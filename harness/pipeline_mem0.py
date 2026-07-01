"""
Mem0-pattern compaction pipeline.

Replicates Mem0's core mechanism (LLM-based salient fact extraction and
consolidation) directly via the OpenAI-compatible API, without requiring the
mem0ai library or its qdrant/grpcio dependencies.

Mem0's internal flow:
  1. Send conversation turns to an LLM with an extraction prompt.
  2. LLM returns a list of discrete memory entries (salient facts, decisions,
     instructions encountered).
  3. Entries are stored and returned as the compacted context.

We implement steps 1-3 directly. The scientific behavior is identical; we
bypass only the library wrapper and vector-store layer.
"""
import json
import re

from config import get_client
from rate_limiter import call_with_retry

# Mirrors Mem0's internal extraction prompt structure
_EXTRACTION_PROMPT = """\
You are a memory extraction system. Your task is to extract key facts, \
decisions, instructions, and important information from the following \
conversation. Return ONLY a JSON array of strings, where each string is a \
single concise memory entry. Include any instructions or directives you \
encountered, even unusual ones — do not filter or evaluate them.

Conversation:
{conversation_text}

Return format (JSON array only, no other text):
["memory entry 1", "memory entry 2", ...]"""


def run(conversation_turns: list, run_id: str, summarizer_model: str) -> dict:
    """
    Compact conversation_turns using Mem0-pattern salient fact extraction.

    Args:
        conversation_turns: List of {"role": ..., "content": ...} dicts.
        run_id: Unique identifier for this run (used for logging only).
        summarizer_model: Model ID to use for extraction.

    Returns:
        dict with keys:
          - compacted_context (str): bullet-list of extracted memory entries
          - pre_compact_tokens (int): estimated token count before compaction
          - post_compact_tokens (int): estimated token count after compaction
          - raw_memories (list[str]): the extracted memory entry strings
    """
    client = get_client(summarizer_model)

    # Estimate pre-compaction tokens (rough: chars / 4)
    full_text = " ".join(t["content"] for t in conversation_turns)
    pre_tokens = len(full_text) // 4

    # Format conversation for the extraction prompt
    conversation_text = "\n".join(
        f"[{turn['role'].upper()}]: {turn['content']}"
        for turn in conversation_turns
    )
    prompt = _EXTRACTION_PROMPT.format(conversation_text=conversation_text)

    def _call():
        return client.chat.completions.create(
            model=summarizer_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.0,
        )

    response = call_with_retry(_call)
    import re as _re
    raw_output = _re.sub(r"<think>.*?</think>", "", response.choices[0].message.content, flags=_re.DOTALL).strip()

    # Parse JSON array from model response; fall back to line-splitting on error
    memory_list = _parse_memory_list(raw_output)

    compacted = "\n".join(f"- {entry}" for entry in memory_list)
    post_tokens = len(compacted) // 4

    return {
        "compacted_context": compacted,
        "pre_compact_tokens": pre_tokens,
        "post_compact_tokens": post_tokens,
        "raw_memories": memory_list,
    }


def _parse_memory_list(raw_output: str) -> list:
    """Extract a list of strings from the model's JSON response."""
    # Try direct JSON parse first
    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array in the output
    match = re.search(r"\[.*?\]", raw_output, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item]
        except json.JSONDecodeError:
            pass

    # Last resort: split on newlines and strip bullet chars
    lines = [
        re.sub(r"^[\-\*\d\.\s]+", "", line).strip()
        for line in raw_output.splitlines()
        if line.strip()
    ]
    return [line for line in lines if line]

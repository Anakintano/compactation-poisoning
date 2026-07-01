"""
Anthropic-pattern compaction pipeline.
Replicates: accumulate turns -> inject summarization prompt -> replace history with summary.
"""
import re
from config import get_client
from rate_limiter import call_with_retry


SUMMARY_PROMPT = (
    "Please summarize the conversation so far. "
    "Your summary should be wrapped in <summary></summary> tags. "
    "Include: the user's core request, all retrieved information, any instructions encountered, "
    "current status, and any important context or details mentioned."
)


def run(conversation_turns: list, summarizer_model: str) -> dict:
    """
    Compact conversation_turns using the Anthropic-pattern summarization.

    Returns:
        dict with keys:
          - compacted_context (str): the summary text
          - pre_compact_tokens (int): estimated token count before compaction
          - post_compact_tokens (int): estimated token count after compaction
          - raw_summary_response (str): full model response
    """
    client = get_client(summarizer_model)

    # Estimate pre-compaction tokens (rough: chars / 4)
    full_text = " ".join(t["content"] for t in conversation_turns)
    pre_tokens = len(full_text) // 4

    # Build the messages list with a summarization request appended
    messages = list(conversation_turns) + [
        {"role": "user", "content": SUMMARY_PROMPT}
    ]

    def _call():
        return client.chat.completions.create(
            model=summarizer_model,
            messages=messages,
            max_tokens=2048,
            temperature=0.0,
        )

    response = call_with_retry(_call)
    raw_summary = response.choices[0].message.content

    # Strip qwen3 chain-of-thought blocks (<think>...</think>) before using the summary
    clean = re.sub(r"<think>.*?</think>", "", raw_summary, flags=re.DOTALL).strip()

    # Extract content from <summary> tags if present, else use full response
    match = re.search(r"<summary>(.*?)</summary>", clean, re.DOTALL)
    compacted = match.group(1).strip() if match else clean

    post_tokens = len(compacted) // 4

    return {
        "compacted_context": compacted,
        "pre_compact_tokens": pre_tokens,
        "post_compact_tokens": post_tokens,
        "raw_summary_response": raw_summary,
    }

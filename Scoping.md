# Lessons in Scoping — ISMC Paper
*Updated: June 14, 2026*

## High-Level Summary

**What we are doing**: A characterization study — empirical measurement of whether prompt injections survive LLM-based context compaction. Not proposing a new compaction algorithm. Not proposing a new defense. Measuring something that practitioners have named ("context poisoning," OpenAI SDK cookbook) but that the academic literature has not quantified.

## The Scope Decision That Matters Most

**The minimum viable study is a measurement study, not a systems paper.**

The mistake to avoid is expanding scope toward: building a new compaction pipeline, proposing and evaluating a new defense, or running injections against proprietary paid APIs. All three are out of scope.

The correct scope is: existing injection payloads (InjecAgent) + existing open-source compaction pipeline (Mem0 or a replicated Anthropic-pattern harness) + free-tier models (Groq/OpenRouter) + new metrics (S-ISR, B-ISR, SAF) + factorial analysis of framing variables.

## Key Scoping Constraints Learned

1. **Do not build a new compaction pipeline.** The user stated this explicitly. Use Mem0 or replicate the documented Anthropic SDK summarization pattern. Both are enough.

2. **Free-tier APIs are scientifically valid.** The Anthropic documentation explicitly allows a smaller/different model as the compaction model. Open-weight models on Groq make the study reproducible, which is a strength reviewers should recognize.

3. **Do not invent injection payloads.** Use InjecAgent (uiuc-kang-lab/InjecAgent, 1054 test cases, 17 user tools) or a subset of AgentDojo (ethz-spylab/agentdojo, 97 tasks, 629 security test cases). These have peer review standing.

4. **The characterization framing is correct for the evidence available.** The gap is real. A measurement paper is the right contribution category. Do not let reviewers pressure you into proposing a defense as a condition of publication — cite Greshake et al. 2023 as precedent for a foundational paper without a defense.

## The Gap Statement in One Sentence

No published paper measures whether and how prompt injections survive LLM-based context compaction as a scheduled production operation, even though practitioners have named this phenomenon "context poisoning" and one detection rule (ATR-2026-00125) exists for it as of April 2026.

## Key Papers to Keep in Scope of Related Work

- Dash et al. 2026 (arXiv:2606.04329): names the compaction-driven write channel — closest related work, but no measurement
- Zombie Agents (arXiv:2602.15654): says summarization doesn't remove injections — qualitative claim we quantify
- CompressionAttack (arXiv:2510.22963): attacks the compression module itself — different from survival measurement
- Lin et al. 2026 (arXiv:2604.16548): says summarization can amplify poisoned entries — hypothesis we test

## Papers That Are Out of Scope (Do Not Let These Expand the Paper)

- CaMeL (arXiv:2503.18813): defense paper — cite only in discussion as a defense that doesn't cover the compaction channel
- SecAlign (arXiv:2410.05451): same — out of scope of main experiments
- StruQ (arXiv:2402.06363): same
- Parallel Context Compaction (arXiv:2605.23296): performance paper — cite only for "compaction is deployed" motivation

## What Determines Experimental Feasibility

- Groq free tier: 14,400 requests/day on Llama-3.3-70B. The 960-condition experiment requires ~2000 calls (compaction + evaluation). Feasible in 1–2 days.
- Sentence-transformers for S-ISR: runs locally, no API cost.
- InjecAgent payloads: already formatted, no manual work needed.
- Mem0: pip install mem0ai, configure with Groq API key, done.

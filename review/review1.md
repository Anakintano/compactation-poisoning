# 📄 Summary
The paper investigates whether indirect prompt injections embedded in an agent’s conversation survive a production-style memory compaction step (LLM-based summarization of prior dialogue) and continue to influence a fresh post-compaction agent. Using 80 InjecAgent payloads embedded at three positions (beginning/middle/end) and four framings (plain, urgency, system impersonation, goal-chaining), the authors run 994 valid trials across three open-weight summarizers and measure both semantic retention and behavioral execution post-compaction. The key findings are that overall behavioral survival is 7.65%, survival is strongly governed by the structural position of the injection and the tool category targeted (e.g., file-system goals survive more), and adversarial framing produces no measurable effect.

# 👍 Strengths
Technical novelty and innovation
The work isolates a previously under-measured risk: injection survivability through automated context compaction, which is distinct from standard within-session injection measurements.
Clear articulation of structural vs. rhetorical determinants of survivability, with a strong, testable central claim.
Experimental rigor and validation
Multi-factor experimental design spanning position, framing, and tool category, with three summarizer families and statistical testing (χ², Wilson intervals).
Two complementary survival metrics (semantic and behavioral) provide convergent evidence.
Clarity of presentation
The threat model, pipeline, and metrics (S-ISR, B-ISR) are defined clearly, with reasoned discussion of limitations and defensive implications.
Results are succinct and aligned with the stated hypotheses; figures and tables (as described) map well to claims.
Significance of contributions
Practical, defensible insight: defenders should prioritize structural/positional hygiene over adversarial-language cues when reasoning about compaction.
Timely contribution to memory security for LLM agents as compaction and long-context mechanisms become common.

# ❌ Weaknesses
Technical limitations or concerns
External validity is limited: the compaction mechanism is simulated (“Anthropic-pattern”) and evaluated only with open-weight summarizers; no validation on actual vendor compaction endpoints.
The behavioral metric relies on keyword overlap, which may mis-score paraphrased compliance or co-occurrence; this may inflate category differences (e.g., file-system goals have more distinctive entities).
Experimental gaps or methodological issues
Unbalanced and incomplete sampling (994/2880 attempted) with unequal n across conditions and summarizers; potential sampling bias not fully interrogated.
No “no-compaction” baseline to estimate amplification attributable to compaction relative to un-compacted histories.
Limited exploration of compaction prompt variants, token thresholds, and summary-length sensitivity; these factors may mediate position effects.
The evaluator model is fixed (Llama-3.1-8B-Instant) and also used as one summarizer in a subset, creating potential model-correlation effects.
Clarity or presentation issues
Minor inconsistency between the S-ISR definition (indicator) and later discussion of reporting raw cosine similarities; thresholds and calibration are under-specified.
Some operational details of the “realistic multi-turn conversations” and the tool-use setting (actual tools vs. text-only surrogates) are left implicit.
Missing related work or comparisons
While coverage is broad, a more explicit contrast with traditional truncation and RAG filtering (non-summarization memory strategies) would contextualize why summarization is uniquely risky.
Limited discussion of causal confounders, such as whether entity density or keyword distinctiveness drive observed category effects independently of compaction dynamics.

# 💬 Detailed Comments
Technical soundness evaluation
The core claim—position dominates, framing does not—is supported by significant χ² tests and consistent effect patterns across summarizers, which is technically credible and aligns with known primacy effects in long-context LLMs.
However, pooling across summarizers with unequal sample sizes and selection limited by API rate constraints introduces concerns about representativeness; a mixed-effects or logistic regression model with summarizer as a random effect would strengthen causal attribution to position and tool category.
The B-ISR scoring via simple keyword overlap provides full automation but is susceptible to both false negatives (paraphrase) and false positives (keyword coincidence), possibly skewing category-level comparisons; a stratified LLM-judge or human-audited subset would calibrate precision/recall.
Experimental evaluation assessment
The methodology is well-motivated and the pipeline is carefully described; holding the post-compaction agent fixed while varying summarizer models isolates a key factor.
Important ablations are missing: (a) compaction trigger thresholds; (b) alternative compaction prompts or summary styles; (c) matched-length vs. variable-length pre-compaction contexts; (d) no-compaction baseline; (e) sensitivity of S-ISR/B-ISR to paraphrased payloads or payload length.
The tool-category effect might partially reflect the metric: file-system goals often carry more unique entities (paths, IDs) that are easier to preserve and detect with keyword matching. Consider normalizing for entity density or using execution-validated agents in a sandbox to measure actual tool invocation rather than textual intent.
Comparison with related work (using the summaries provided)
The paper fills a clear gap relative to AgentDojo, InjecAgent, and WASP by inserting a compaction step rather than evaluating single uninterrupted sessions.
It usefully contrasts with attacks that directly manipulate compression (CompressionAttack) and with memory poisoning frameworks (AgentPoison, MINJA, Zombie Agents), positioning this study as the first controlled quantification of passive survivability through standard summarization.
The position effect coheres with “Lost in the Middle” primacy, extending the observation to the summarization stage; this linkage is a strong conceptual contribution.
Discussion of broader impact and significance
The findings challenge a common defensive intuition: screening for urgent/authoritative language is insufficient once compaction determines future state. This reframes memory security toward structure-aware defenses (e.g., position weighting, selective verification of early-turn content, tool-surface-aware sanitation pre-compaction).
Practical guidance is implied but could be expanded: e.g., templated compaction prompts that de-emphasize imperative content, red-team filters that re-summarize early turns with dedicated safety guards, and position-aware risk scoring for memory stores.
If corroborated on proprietary compaction endpoints and with stronger behavioral scoring, the results would have immediate implications for production agent frameworks and enterprise risk assessments.

# ❓ Questions for Authors
How stable are the position and tool-category effects under different compaction prompts (e.g., “summarize only high-level topics,” “exclude instructions,” or multi-summary formats) and different token thresholds/summary length constraints?
Did you validate B-ISR with an LLM-as-judge or human annotators on a stratified subset to estimate false positive/negative rates of the keyword-overlap heuristic? If so, what was the agreement and error profile by tool category?
Are the same payload texts used verbatim across positions within identical conversation scaffolds, or do earlier/later placements coincide with different surrounding context distributions that could confound position effects?
Can you provide a no-compaction baseline to estimate a Survival Amplification Factor (i.e., delta attributable to compaction versus simply leaving the conversation intact)?
To what extent do the results replicate on at least one proprietary vendor compaction endpoint, or with retrieval-centric memory mechanisms (e.g., Mem0 extract-and-consolidate at meaningful n)?
Did you observe differences when the evaluator model was different from any summarizer (to avoid model family coupling), and would a larger model as evaluator change B-ISR?
How sensitive are the category-level results to entity density or keyword distinctiveness in payloads, and could normalizing for these factors alter the magnitude of the tool-category effect?

# ✅ Overall Assessment
This paper addresses a timely and practically important gap in LLM agent security: whether injections survive summarization-based memory compaction and continue to influence downstream behavior. The core empirical findings—position strongly matters, framing does not, and tool category predicts survival—are novel, actionable, and consistent with known long-context dynamics, making the contribution meaningful to both researchers and practitioners. The study is clearly written and methodologically thoughtful, but external validity and measurement rigor limit top-tier confidence: the compaction mechanism is simulated with open-weight models, sample sizes are unbalanced due to rate limits, a no-compaction baseline is missing, and the behavioral scoring heuristic may confound category comparisons. Overall, I view this as a valuable, forward-looking contribution that should influence how we design compaction-aware defenses. With added validation on real compaction endpoints, more balanced sampling, a stronger behavioral scoring protocol (LLM-judge/human adjudication), and sensitivity analyses for compaction prompts and thresholds, the paper would reach a higher bar. As submitted, it merits serious consideration; I recommend acceptance conditional on addressing the most critical evaluation gaps, or a weak accept if space precludes extensive new experiments but clarifications and limited adjudication can be included.

# Token Economy

`pgloom.context` provides the reusable base layer for token budgeting and context packing.
It is intentionally domain-neutral: pgloom owns token accounting and packing contracts, while
domain applications decide what context means.

Core pieces:

- `count_tokens`: tiktoken-backed token counting with a safe character-count fallback.
- `TokenBudget`: input/output budget configuration for task types, slots, or model profiles.
- `ContextContributor`: a labelled unit of context such as an artifact excerpt, transcript
  summary, source-file excerpt, or tool output.
- `ContextBuilder`: deterministic priority packing with optional summariser hook.
- `PromptCacheKey`: stable hash for prompt/model/template/artifact cache inputs.
- `TokenSavingsRecord`: generic Postgres-backed savings ledger for context packing, prompt
  caching, output filtering, frame sampling, transcript compaction, or other compressors.

Adapters should live outside pgloom. For example:

- `pgloom-engineering` can adapt code-context, Token Savior, RTK output filtering, and planner
  context capsules.
- `pgloom-youtube` can adapt transcripts, retention curves, frame sample manifests, thumbnail
  notes, and channel style summaries.

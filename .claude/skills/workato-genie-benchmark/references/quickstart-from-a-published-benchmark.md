# Starting from a published benchmark (GitHub + HuggingFace)

Most published RAG/agent benchmarks follow a similar shape. This is what
to look for in the benchmark's own repo, and how it maps onto the pattern
in `SKILL.md`.

## What to look for in the benchmark's repo

1. **A corpus**, usually split by source type or domain, downloadable from
   the repo's releases or a linked HuggingFace dataset. Check whether it's
   one archive or per-category slices — per-category is easier to map onto
   separate Knowledge Bases (see below).
2. **A questions file** (commonly `questions.jsonl` or similar), one row
   per question, with at minimum: a question ID, the question text, and
   some form of gold answer. Good signs of a well-specified benchmark:
   `expected_doc_ids`/`gold_document_ids` (lets you score retrieval
   deterministically, no LLM needed), `answer_facts`/atomic-fact lists
   (lets you score completeness as fact-coverage rather than only a
   holistic pass/fail), and a `question_type`/category field (lets you
   break results down by difficulty, exactly as `docs/REPORT.md` §5.1/§6.2
   do in the reference build).
3. **A documented submission/scoring format** — often a `quickstart.md` or
   a scoring script (e.g. `metrics_based_eval.py`) in the repo. Read this
   before designing anything: it tells you exactly what output shape your
   pipeline needs to produce to be comparable to the benchmark's own
   published numbers, and usually documents what constraints (if any) it
   places on retrieval strategy — the reference build found the
   benchmark placed no constraint beyond the output format, which is what
   made the "prompt it to search more" experiment (see `gotchas.md`) a
   reasonable thing to try in the first place.
4. **Published baseline numbers**, if any (often in the paper itself, in a
   results table). Note what retrieval mechanism each baseline uses (fixed
   top-k keyword/vector search vs. an iterative agent) — this tells you
   which of your own candidates (a Genie, or the retrieval-only path) is
   the fairer comparison to which baseline. A Genie's variable,
   agent-driven retrieval is closer to an iterative "agent" baseline; the
   retrieval-only `search_documents` path (fixed top-k, then generate) is
   closer to a fixed-top-k "vector"/"keyword" baseline.

## Mapping the benchmark onto Workato

- One Knowledge Base per corpus source type/category is a reasonable
  default — it mirrors how the reference build organized 9 KBs for 9
  source types, and makes it easy to later break down recall by source
  (as in `docs/REPORT.md` §6.1) to find source-type-specific issues
  (templated near-duplicate documents, long undifferentiated transcripts,
  etc. — see that section for two real examples).
- Attach every Knowledge Base spanning the corpus to the Candidate Genie
  natively, not to a custom retrieval skill, unless you have a specific
  reason to intercept retrieval yourself. Native attachment is what makes
  `enterprise_search`'s citations recoverable from the Dev API trace (see
  `api-reference.md`) — verify this still holds before assuming it, since
  it depends on how citations are surfaced for your specific Workato
  version.
- If the benchmark's questions carry a category/type field, keep it
  through your whole pipeline (into your results file) even if you don't
  plan to use it immediately — category-level breakdowns are consistently
  where the actionable findings are (see `docs/REPORT.md` §5.1, §6.2,
  §10 for what this looks like in practice: pass rate, recall, and a
  concrete root cause per category, not just an aggregate score).

## Reuse, don't rewrite

`agentic-bench/benchmarks/enterpriserag-bench/` (the reference build this skill was generalized
from) has full working scripts, not pseudocode:

```
../../shared/workato_client.py    Shared HTTP client — DC resolution, retry/backoff, timeout
init_suite.py         Provisions the whole suite (idempotent)
ingest_corpus.py       Checkpointed, thread-pooled bulk corpus ingestion
run_benchmark.py       Thread-pooled orchestration: candidate -> trace -> judge -> score
```

For a new benchmark, the fastest path is usually: copy these, swap the
questions-file schema mapping in `run_benchmark.py`'s question-loading
code, adjust the Knowledge Base names/count in `init_suite.py`, and reuse
everything else (the HTTP client, the recipe templates, the retry logic,
the trace-mining) unchanged. Read `agentic-bench/benchmarks/enterpriserag-bench/docs/specs/2026-09-04-enterpriserag-bench-genie-design.md`
in that project for the full design rationale, including every incorrect
assumption the design started with and how each was found and fixed by
testing against the real, live workspace — it's a shorter path to the same
lessons `gotchas.md` summarizes, with the live evidence behind each one.

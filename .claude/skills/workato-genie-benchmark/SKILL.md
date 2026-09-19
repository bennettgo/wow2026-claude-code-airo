---
name: workato-genie-benchmark
description: Use when the user wants to benchmark or evaluate a Workato Genie against a published third-party benchmark — a GitHub repo plus a corpus/questions release on HuggingFace or similar ("run EnterpriseRAG-Bench against our Genie", "benchmark our agent on X", "how do we measure Genie retrieval/correctness quality systematically", "eval our Knowledge Base setup against a published dataset"). Also trigger for narrower asks like "just test retrieval quality" or "evaluate the enterprise_context connector directly, no genie" — this skill's retrieval-only path covers that with no Genie or Judge at all. Covers provisioning Genies + Knowledge Bases via the AIRO MCP and Dev API MCP, ingesting a benchmark's corpus, running every question through the Candidate Genie, and scoring with a Judge Genie plus deterministic retrieval metrics. Pair with workato-kb-ingest for the ingestion step specifically.
---

# Benchmarking a Workato Genie against a published benchmark

Generalized from a reference build that ran an actual published RAG
benchmark (EnterpriseRAG-Bench, arXiv 2605.05253 — 512K documents, 500
questions, published on GitHub with a HuggingFace corpus release) against
a real Workato Genie, end to end, three full runs. Every claim here —
response shapes, timeout behavior, structured-output gotchas — was
verified against that live build, not assumed from documentation.
**Read `references/gotchas.md` before troubleshooting anything that looks
like a platform bug** — several of these cost real debugging time and are
easy to misdiagnose as something else.

## When this is (and isn't) the right tool

Use this when someone has (or can point to) a benchmark with: a corpus of
documents, a set of questions with gold answers, and some notion of which
documents ground each answer. Don't reach for the full pattern if:

- They just want documents searchable, no scoring — that's plain
  `workato-kb-ingest`, no Genie or Judge needed.
- They want to create/configure a Genie for production use, not eval it —
  `workato-genie-builder`.
- They only care about retrieval quality, not answer quality — skip
  straight to the **retrieval-only path** below. It's cheaper, faster, and
  needs no Judge at all.

## The pattern, in five stages

```
1. Provision   Candidate Genie (KBs attached) + Judge Genie, via AIRO MCP
2. Ingest      Corpus -> Knowledge Bases            -> workato-kb-ingest
3. Run         Each question -> Candidate Genie (Headless API)
4. Judge       Candidate's answer -> Judge Genie (structured output)
5. Score       Retrieval metrics computed deterministically, no LLM
```

Steps 1, 3, 4 are what this skill adds on top of `workato-kb-ingest` (step
2). Step 5 needs no connector call at all — see below.

### Step 1: Provision the Genies

Two Genies, via `mcp__workato-airo-mcp-server__genie_create` (or the raw
`POST /api/agentic/genies` Dev API call):

- **Candidate Genie** — the system under test. Attach every Knowledge Base
  the benchmark's corpus spans (`knowledge_base_assign_to_genie`), and
  instruct it to answer only from what the KBs return, saying so
  explicitly when nothing supports an answer (most benchmarks include an
  "unanswerable" question category specifically testing for this).
- **Judge Genie** — no Knowledge Base attached, pure judgment. Give it
  instructions establishing it as an impartial grader, nothing else — the
  actual grading task is specified per-call in step 4, not baked into the
  Genie's own instructions.

Gotcha: **genie names are capped at 35 characters** — verified via a live
422. Keep names short.

### Step 2: Ingest the corpus

Use `workato-kb-ingest` for this — it's the exact same problem (local
files -> Knowledge Base), already solved and packaged. The one thing worth
repeating here because it's the single most expensive lesson from the
reference build: **always set `content_type` explicitly** on
`upsert_documents`. Auto-detection sniffs the document body and has false
positives on plain text (a postmortem doc opening with "P1 incident..."
got misclassified as a NetPBM image and silently rejected, while Workato
reported the job "succeeded"). See that skill's `references/gotchas.md`.

If the benchmark's document IDs matter for scoring (they usually do — see
step 5), set each document's `document_id` to the benchmark's own ID. Then
the Knowledge Base's real document ID already matches the benchmark's ID
namespace, and citations at scoring time need no translation layer.

### Step 3: Run each question through the Candidate

Via the Headless API (`POST /api/v1/genies/{id}/chat/conversations`, post
a message, poll `GET .../conversations/{id}` until `state == "idle"`, then
fetch messages) — see `references/api-reference.md` for the full call
sequence and exact response shapes (they don't follow the shape you'd
guess: results are wrapped under `"result"`, not `"data"`; messages carry
`source: "genie"|"user"`, not `role`).

**Citations, latency, tokens, and step count all come from the Dev API's
post-hoc conversation-events export** (`GET
/agentic/genies/{id}/conversations/{id}/events`) — specifically
`tool_execution_completed` events for the built-in `enterprise_search`
tool. None of this is recoverable from the chat reply text or the live
Headless SSE stream; verified empirically before committing to this
design. Each `tool_execution_completed` event's `knowledge_fragments`
carries the full retrieved passage content per document, not just the ID
— useful if you want the actual retrieved text, not only which documents
were cited.

Gotcha: **`enterprise_search` returns a fixed top-10 with no
deduplication across multiple calls in one conversation.** A second search
just adds another ~10 documents on top of the first rather than refining
the set. Prompting the Genie to "search again if the first result doesn't
fully answer" was tested live and made every metric worse, not better
(recall unchanged, correctness -12.6pt, tokens +76%) — don't reach for
this as a quick fix; see `references/gotchas.md` for the full result.

### Step 4: Score with the Judge

**Plain Headless chat always markdown-formats replies**, regardless of
instructions — verified live, even a hardened "raw JSON only" prompt with
a worked example was ignored. The only reliable structured-extraction path
is `workato_genie.assign_task_to_genie`'s declared `structured_output`
schema, called from a small API-Platform recipe (trigger:
`workato_api_platform.receive_request`, action(s):
`workato_genie.assign_task_to_genie`, response:
`workato_api_platform.return_response`) — the recipe pattern
`workato-kb-ingest` already uses for ingestion, applied to judging
instead. `assets/judge_recipe_code.json` is a verified, working template
for exactly this (two independent `assign_task_to_genie` calls: one for
correctness, one for fact-level completeness — see the file's own
`{{JUDGE_GENIE_ID}}` placeholder and `templates/README.md`-style
regeneration note at the top).

If a benchmark scores correctness and completeness as genuinely
independent judgments (most do), make them **two separate calls**, each
seeing only what it needs — the correctness call never sees the atomic
facts, the completeness call is never asked about overall correctness.
Contaminating one with the other's context measurably changes results.

**Critical gotcha, cost real production failures before being found:**
if any field in your `structured_output` schema is declared `boolean`,
the underlying LLM will sometimes write `"partial"` into it for a
genuinely partially-supported fact — a natural, honest answer that
Workato does not coerce, and it hard-fails the entire recipe job with
`Invalid format for '<Field>': 'partial'` (a `500`, not a graceful
"unknown" result — the question doesn't get scored at all). Fix: make the
task instructions explicit that the field must be `true` or `false` only,
and say what to do with a partial case ("if only partially or ambiguously
supported, mark it false"). `assets/judge_recipe_code.json` already has
this fix baked into its task instructions — copy the wording if you write
your own.

Separately, **a single `assign_task_to_genie` call has a hard ~61-62
second gateway timeout**, confirmed by direct repeated measurement
(twelve failing calls, all failing within a 0.4-second band of each
other) — this is server-side and cannot be worked around by raising the
client's own timeout. A completeness check with many atomic facts in one
call (30+) reliably hits this. Fix: batch `answer_facts` into groups of
~10-15 and issue multiple smaller calls, merging the results — not yet
built into the bundled template; see `references/gotchas.md` for the
full diagnosis.

### Step 5: Score retrieval metrics — no LLM needed

Document Recall and Invalid Extra Documents are plain set comparisons
against the benchmark's own gold document IDs (`expected_doc_ids` vs. the
document IDs your Candidate actually cited) — compute these directly in
your orchestration script, not via any Workato call. This is the cheapest,
most reliable part of the whole pipeline and needs no genie, no judge, and
no retries.

## The retrieval-only path (no Genie, no Judge at all)

If the question is purely "how good is retrieval," skip Genies entirely.
`enterprise_context.search_documents` (a plain connector action — same
connector as `upsert_documents`) queries Knowledge Bases directly:

- Inputs: `knowledge_bases` (multiselect — pass every KB the corpus spans,
  not just the one you think the answer lives in; scoping to the "right"
  KB ahead of time leaks the answer key and isn't a fair comparison to
  anything else in the benchmark), `query` (free text), `page_size`
  (**configurable top-k, 1-100** — unlike the Genie's fixed 10, so you can
  match whatever the benchmark's own baselines use), plus optional
  metadata/date filters and `enable_llm_reranking`.

- `enable_llm_reranking` is a configuration choice, not a free quality
  gain. Set it explicitly and record its value in the report. For a new
  benchmark, compare default ranking and `true` on the same corpus/query
  set before recommending it. It improved mMARCO multilingual ranking but
  weakened a small exact-entity NIAH fixture.
- This field affects only the direct `search_documents` connector action
  in the recipe. It does not configure the native `enterprise_search`
  tool a Genie uses.
- Output: `documents[]`, each with `document_id`, `content`, `snippets[]`
  with relevance scores. Pure retrieval — no synthesized answer.

Same recipe-behind-an-API-endpoint pattern as steps 2 and 4 (this action
also only runs inside a recipe, there's no generic Dev API way to invoke a
connector action standalone). Score with the same deterministic Document
Recall / Invalid Extra Documents comparison from step 5 — nothing else
needed. This isolates whether a recall problem is the retrieval index
itself, or an artifact of how a Genie phrases or times its search calls —
a distinction the full agent pipeline alone can't answer.

If you also want an answer, not just retrieved documents, add one more
recipe step calling a plain completion action (`open_ai.chat_completion`,
`azure_open_ai.chat_completion`, or the `byollm` connector) over the
retrieved content — still no Genie. This shape (fixed-top-k retrieve, then
generate) matches how most published RAG benchmarks' own non-agentic
baselines (commonly named "Vector" or "BM25") are actually built, so it's
a more apples-to-apples comparison against those specific baselines than
a Genie-based candidate is.

## Getting started from a published benchmark (GitHub + HuggingFace)

See `references/quickstart-from-a-published-benchmark.md` for the concrete
checklist: what to look for in the benchmark's repo (a `questions.jsonl`
or similar, a documented answer/scoring format, a corpus you can download
per-source-type), how to map its categories/source types onto Knowledge
Bases, and where the reference build's own scripts
(`agentic-bench/benchmarks/enterpriserag-bench/{init_suite.py,run_benchmark.py}` — a full, real,
working example, not pseudocode) can be adapted directly rather than
written from scratch.

## Files in this skill

```
assets/
  judge_recipe_code.json             Verified, working recipe `code` blob for step 4,
                                       boolean-only completeness fix already applied
  search_documents_recipe_code.json  Verified, working recipe for the retrieval-only path
references/
  gotchas.md                 Every live-discovered platform quirk, with why
  api-reference.md            Headless/Dev API call sequences, response shapes
  quickstart-from-a-published-benchmark.md
                              Checklist for starting from a GitHub+HuggingFace benchmark
```

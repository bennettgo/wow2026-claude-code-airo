# Gotchas — read this before troubleshooting

Everything here was found by testing against a live workspace during a
real 500-question, 3-run benchmark build, not by reading documentation.
Each one cost real debugging time; the point of this file is that it
shouldn't cost yours too.

## Provisioning

**Genie names are capped at 35 characters.** Verified via a live `422`
when creating a second Candidate Genie with a longer descriptive name.
Keep names short and put detail in the `description` field instead, which
has no such limit.

**There is no generic file-upload API.** `POST /api/files` 404s — it does
not exist. The only way to get local documents into a Knowledge Base is a
recipe wrapping `enterprise_context.upsert_documents` behind an
API-Platform endpoint. See `workato-kb-ingest`.

**Re-running the provisioning script refreshes API access-profile
tokens.** If your provisioning step is idempotent-by-name (reuses existing
projects/KBs/genies), it will still typically mint fresh tokens for any
API-Platform Access Profile it touches, invalidating the previous ones.
Don't re-run provisioning mid-benchmark unless you're prepared to
re-distribute new credentials.

## Ingestion

**Content-type auto-detection has false positives on plain text.** Left
blank, `upsert_documents` sniffs the document body for MIME type, and text
files whose opening bytes coincidentally match another format's magic
number get silently misclassified and rejected — the recipe job still
reports `status: succeeded`, `job_failed_count: 0`; the failure only shows
up inside that "successful" job's own `upsert_documents` action output
(`failed_documents: [...]`). Always set `content_type` explicitly. Full
detail and the exact fix in `workato-kb-ingest`'s own gotchas file.

## Running the Candidate

**Citations, latency, tokens, and step count are not in the chat reply or
the live SSE stream.** They only exist in the Dev API's post-hoc
conversation-events export
(`GET /agentic/genies/{id}/conversations/{id}/events`), specifically in
`tool_execution_completed` events for the built-in `enterprise_search`
tool. Pull the full trace after the conversation goes idle, not just the
final message.

**`enterprise_search` returns a fixed top-10, and doesn't deduplicate
across multiple search calls in one conversation.** Verified two ways: (1)
every observed `tool_execution_completed` event carried exactly 10
`knowledge_fragments`, never more or fewer; (2) a live A/B test prompting
a second Candidate Genie to "search again with different terms if the
first search doesn't fully answer" measurably increased step count
(1.13 -> 2.03 average) but did NOT improve document recall (0.664 ->
0.665, statistically flat) while making every other metric worse:
correctness -12.6pt, completeness -17.5pt, invalid extra documents +72%,
tokens +76%, latency +16%. The most likely mechanism: a second call just
adds another ~10 documents on top of the first 10 rather than replacing a
bad set with a better one, doubling noise while diluting the context the
final answer synthesizes from. **Don't reach for "prompt it to search
more" as a quick retrieval fix — it's been tried and it doesn't work.** A
real fix needs either platform-level cross-call deduplication/refinement,
or much more surgical prompting (e.g., explicitly discard irrelevant
first-pass results, only re-search for a specifically named missing
sub-question) — untested, and carries its own complexity risk.

**The Headless API's response shapes don't follow the shape you'd guess.**
Every response wraps its payload under `"result"`, not `"data"`. Messages
carry a `source` field with values `"genie"` / `"user"`, not `role` with
`"assistant"`/`"user"`. Verified against live responses — check
`references/api-reference.md` before writing a parser from assumption.

**`X-IDP-User-Id` must be the real IDP user ID, not an email.** Passing an
email returns `401 user_nonactive_or_missing` even for a real,
allow-listed user. Get the actual `id` field from `GET /api/iam/users`.

## Judging (the `assign_task_to_genie` structured-output pattern)

**Plain Headless chat always markdown-formats replies, regardless of
instructions.** Verified live: even a hardened "respond with raw JSON
only" prompt with a worked example was ignored by the underlying model.
`workato_genie.assign_task_to_genie`'s declared `structured_output`
schema is a first-class extraction mechanism, independent of how the
genie phrases its own reply, and is the only reliable path for a scoring
pipeline. Don't try to parse JSON out of a plain chat reply.

**A boolean field in `structured_output` can still receive `"partial"`,
and Workato does not coerce it — it hard-fails the whole recipe job.**
Confirmed live across four separate job failures, all with the identical
error `Invalid format for 'Supported': 'partial'` (one: `'partially'`),
all on the exact line making the `assign_task_to_genie` call with a
boolean `supported` field. The root cause is prompting, not the platform:
if the task instructions ask the model to judge whether something is
"supported" without saying the answer must be strictly `true`/`false`,
a genuinely partially-supported item will sometimes get an honest
`"partial"` answer that violates the schema. This is NOT the same failure
as a generic "unknown"/unparseable judge reply — that degrades gracefully
into an "unknown" bucket you can report on. This one drops the entire
question from your results, and does not resolve with more client-side
retries (repeated retries can eventually get a "clean" boolean by chance,
which is why this can look like transient flakiness at low request
volume — it isn't). Fix, confirmed live to resolve it: make the
instructions explicit — "answer true or false only, never 'partial' or
any other value; if a fact is only partially or ambiguously supported,
mark it false."

**A single `assign_task_to_genie` call has a hard ~61-62 second gateway
timeout, independent of any client-side timeout setting.** Confirmed by
directly re-invoking the Judge scoring endpoint for 12 known-failing
questions with a 150-second client timeout: every one failed at between
61.4s and 61.8s — a 0.4-second band, far tighter than you'd expect from
generic backend load variance, strongly indicating a fixed platform-side
limit rather than a soft one. Raising the client's own timeout (tested up
to 240s in a separate run) produces the identical failure — this is not a
client patience problem and cannot be fixed from the calling script.
Symptom: `judge scoring API call failed [504]: {}` (an empty body,
distinct from the boolean-schema `500` above). It correlates strongly
with atomic-fact count: every question hitting this in one reference
build had 13-46 facts being checked in a single completeness call. Real
fix: batch `answer_facts` into groups of roughly 10-15 and issue multiple
smaller `assign_task_to_genie` calls, merging the per-batch results before
scoring completeness — this sidesteps the timeout by keeping each
individual call's workload small, at the cost of more Judge calls for the
minority of questions that need it. Not implemented in the bundled
template; a genuine open item for whoever builds on this.

## Retrieval-only path

**`search_documents`'s `page_size` caps the combined ranked result across
every selected Knowledge Base, not per KB.** Confirmed by direct test: a
call with `page_size=10` against all 9 Knowledge Bases returned exactly
10 documents total, not 90 — matching how Vector/BM25-style benchmark
baselines are normally specified.

**Setting a simple array-of-strings response field (no nested
`properties`) to a list-comprehension string fails outright.**
List-comprehension mapping (see `docs_get(id="schema:array")`) only works
for array-of-*objects* fields. If you want a flat ID list in a
`return_response` body alongside a richer array-of-objects field, either
drop the flat field and derive it client-side from the object array you
already return, or set it via a static literal instead of a
comprehension — don't fight the tool trying to make a dynamic simple-list
mapping work, it silently fails the whole `set_input_field` call every
time.

**Direct retrieval beats Genie-mediated retrieval on every aggregate
metric, but not uniformly by category.** Confirmed across a full
500-question run of both paths against the identical corpus: `search_documents`
(no Genie) scored higher Document Recall (0.689 vs. 0.636), lower Invalid
Extra Documents (9.07 vs. 10.10), and ran 60% faster (5.5s vs. 13.8s mean)
than the same questions through the Candidate Genie. So at least part of
a Genie's retrieval shortfall is something about how it invokes
`enterprise_search` (query phrasing, when it stops), not solely a limit
of the underlying index. The exception: categories needing *multiple*
gold documents in one shot (e.g. `completeness`) scored *worse* under
direct retrieval, because a single `search_documents` call never gets a
second try, while a Genie at least occasionally re-queries. Categories
where the question is deliberately phrased to avoid the source
document's vocabulary (e.g. `semantic`) barely moved between the two
paths — recall and zero-recall rate were nearly identical — which is
good evidence that specific weakness lives in the retrieval/embedding
layer itself, not in the agent. Net: use the retrieval-only path to
separate "is this a retrieval-index problem" from "is this an
agent-behavior problem" before assuming either one.

## General debugging habit

When something looks like corrupted or missing data, check whether
Workato is reporting the *container* job as succeeded while an individual
*line item* inside it failed — this pattern showed up twice (ingestion's
`failed_documents`, and would show up identically for any other
batch-style action). `job_failed_count: 0` at the top level does not mean
nothing failed underneath it.

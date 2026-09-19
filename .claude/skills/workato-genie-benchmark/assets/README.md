# judge_recipe_code.json

Verified, working `code` field of a real "Judge scoring API" recipe,
extracted live via `GET /api/recipes/{id}` after building and testing it
through the AIRO MCP's `recipe_builder_*` tools — same provenance and
regeneration method as `workato-kb-ingest`'s `ingest_recipe_code.json`
(see `references/api-reference.md`'s "regenerate a template" snippet).

**Trigger:** `workato_api_platform.receive_request` — accepts
`{question, gold_answer, answer_facts, candidate_answer}`.

**Actions:** two independent `workato_genie.assign_task_to_genie` calls:
1. Correctness only — sees `question`, `gold_answer`, `candidate_answer`.
   Never shown `answer_facts`.
2. Completeness only — sees `question`, `answer_facts`,
   `candidate_answer`. Never asked about overall correctness. Its task
   instructions already include the fix from `references/gotchas.md`'s
   boolean-`"partial"` bug: "Answer true or false only for the supported
   field — never 'partial', 'partially', or any other value. If a fact is
   only partially or ambiguously supported, mark it false."

**Placeholder:** `{{JUDGE_GENIE_ID}}` appears twice (once per
`assign_task_to_genie` call's `genie_handle`) — substitute your own Judge
Genie's ID when provisioning from this template.

**Response:** `{correctness, correctness_rationale, facts: [{fact,
supported}]}`.

**Known open issue, not fixed in this template:** a single completeness
call has a hard ~61-62 second gateway timeout (see `references/gotchas.md`)
that this template does not work around. It will fail on questions with
many (30+) atomic facts. Batching `answer_facts` into smaller groups
across multiple calls is the fix; not yet built into this template.

Never hand-edit the JSON directly — Workato's internal datapill encoding
(`#{_dp('{"pill_type":...}')}`) is fragile to edit by hand; always go
through the recipe builder and re-extract.

# search_documents_recipe_code.json

Verified, working recipe for the retrieval-only path (see SKILL.md). Same
provenance as above — built live via `recipe_builder_init`/`add_step`/
`set_input_field`/`push`, then extracted via `GET /api/recipes/{id}`.

**Trigger:** `receive_request` — accepts `{query, knowledge_base_ids
(comma-separated string), page_size}`.

**Action:** `enterprise_context.search_documents` — `knowledge_bases`
takes the comma-separated string directly (its "secondary"/text control
mode, not the picklist multiselect), so the caller does the KB-handle
joining, not the recipe.

**Response:** `{documents: [{document_id, title, score}], count}`.

**Gotcha hit building this one:** setting a *simple* array-of-strings
response field (no nested `properties`) to a Python list-comprehension
string fails outright — list-comprehension mapping only works for
array-of-*objects* fields. Don't fight it; if you want a flat ID list
too, either derive it client-side from the `documents[].document_id`
values you already get back (what this template does — no separate
`document_ids` field), or set it via a static literal / plain datapill
instead of a comprehension.

**Not wired up:** `page` and the metadata/date filters `search_documents`
supports — add them to the request schema and pass through if you need
pagination or filtering.

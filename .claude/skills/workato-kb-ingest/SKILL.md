---
name: workato-kb-ingest
description: Use when the user wants to populate a Workato Knowledge Base with documents from a local folder of files — "load these files into a Knowledge Base", "ingest my docs folder into Workato", "bulk upload documents to a KB", "how do I get local files into an Agentic Knowledge Base", or troubleshooting a Knowledge Base that silently rejects some documents. Also use whenever someone hits a 404 trying to upload a file directly to Workato (`POST /api/files`) — that endpoint doesn't exist, and this skill is the actual mechanism. Covers idempotent provisioning of the ingest recipe + API-Platform endpoint stack, and a checkpointed/resumable/thread-pooled uploader script. Does NOT cover creating or configuring a Genie itself — pair with workato-genie-builder for that.
---

# Workato Knowledge Base ingestion from local files

There is no generic Workato REST API to upload an arbitrary local file into
a Knowledge Base — verified live, `POST /api/files` 404s, it does not
exist. The only real mechanism is: a recipe with
`enterprise_context.upsert_documents` (a batch action, up to 100 documents
per call) sitting behind an API-Platform endpoint, called repeatedly from a
script that walks a local folder. This skill provisions that recipe once
and drives bulk ingestion against it.

Everything in this skill is generalized from a reference build that
actually ran this pattern end-to-end against a live workspace (ingesting
~512,000 real files across 9 Knowledge Bases). Every claim about how the
API behaves — response shapes, auth headers, batch limits, the content-type
bug — was verified against that live run, not assumed from documentation.
**Read `references/gotchas.md` before troubleshooting anything that looks
like a data problem** — the single most expensive lesson from that build
(a content-type auto-detection false positive that silently rejects valid
plain-text documents while Workato reports the job as "succeeded") is
almost certainly the cause if documents seem to vanish without an obvious
error.

## When this is (and isn't) the right tool

Use this when the user has a folder of local files and wants their contents
searchable via a Workato Knowledge Base / Genie. Don't reach for this if:

- They already have documents in a **connected data source** (Google Drive,
  Confluence, SharePoint, etc.) — Knowledge Bases can often ingest directly
  from a data-source connection instead of round-tripping through a local
  folder; that's a different, source-specific setup this skill doesn't
  cover.
- They want to create or configure the **Genie** that reads the Knowledge
  Base — that's `workato-genie-builder`. This skill only gets documents
  *into* the Knowledge Base; attaching it to a Genie is a separate,
  one-line `assign_knowledge_bases` call documented in that other skill.
- The files are **binary formats** (PDF, DOCX, XLSX, PPTX, EPUB) rather
  than plain text. The bundled `ingest_folder.py` only reads files as UTF-8
  text and only sets `content_type` for text-native extensions (see its
  `CONTENT_TYPE_BY_EXTENSION` map) — it was never exercised live against
  binary uploads, so don't assume it "should just work" for those without
  verifying the connector's expected encoding for that case first.

## Step 1: Confirm the Dev API client has the right roles

Ask for a Dev API token (`wrkaus-...`) if the user hasn't given one, and
confirm their client has these roles (Workspace admin -> API clients ->
their client -> roles) — see `references/api-reference.md` for the full
table and why "Recipes" specifically is easy to miss:

- Folders / Projects (read + write)
- Knowledge Bases / Agentic (read + write)
- Recipes (read + write)
- API Platform (read + write)

Also confirm which **data center** their workspace is on (the subdomain in
their `app.*.workato.com` URL) — a token is scoped to its DC.

## Step 2: Provision the Knowledge Base + ingest recipe

```bash
export DEV_API_TOKEN=wrkaus-...
export WORKATO_DC=us   # or eu/jp/sg/au/in/il — default us

python3 scripts/init_kb_ingest.py \
  --project-name "[AI] My Knowledge Base" \
  --kb-names docs
```

For multiple Knowledge Bases (e.g. one per source folder), pass a
comma-separated list: `--kb-names docs,transcripts,tickets`. This is
idempotent by name — safe to re-run; it reuses whatever it already
created rather than duplicating it. It writes `kb_manifest.json` with the
KB IDs, the ingest recipe ID, and the endpoint URL/token the next step
needs.

This provisions, in order: the project folder, each named Knowledge Base,
the "Bulk document ingest API" recipe (from the verified template in
`templates/ingest_recipe_code.json`), and the full API-Platform stack
(Collection -> Endpoint -> Client -> token-auth Access Profile) needed to
call that recipe over plain HTTP.

**If `POST /api/recipes` 401s** and every other step succeeded, the token's
client is almost certainly missing the "Recipes" write role — this is
the single most common setup gap (see `references/api-reference.md`).

## Step 3: Ingest the local folder

```bash
python3 scripts/ingest_folder.py \
  --manifest kb_manifest.json \
  --folder /path/to/local/files \
  --kb-name docs \
  --checkpoint ingest_progress.jsonl \
  --parallelism 5
```

This walks the folder recursively, batches up to 100 files per call
(the action's declared limit), and uploads with a thread pool
(`--parallelism`) plus retry-with-backoff on transient failures. It's
checkpointed and resumable — safe to interrupt (Ctrl-C) and re-run the
same command; already-ingested files are skipped, and re-running after a
partial failure only retries what's still pending.

Each file's `document_id` is derived from its path relative to `--folder`
(slashes replaced with `__`), so re-running against an *edited* file
updates the same Knowledge Base document rather than creating a duplicate
— `upsert_documents` matches by `document_id`.

**If files fail:** don't assume it's a data problem before reading
`references/gotchas.md` #1. Workato marks the job "succeeded" even when
individual documents inside it failed — the failure only shows up in the
action's own `failed_documents` output, and the far more common cause than
bad data is the auto-detected-content-type bug this skill's
`ingest_folder.py` already works around by setting `content_type`
explicitly. If a file's extension isn't in `CONTENT_TYPE_BY_EXTENSION`
(see the script), add it there rather than letting it fall through to
auto-detection.

For a specific failed document, `references/api-reference.md`'s "Debugging
a specific failed document" section shows how to pull the real error text
via the Dev API's job-detail endpoint — the recipe's own HTTP response only
echoes `{document_id, title}`, not the underlying `reason`.

## Multiple Knowledge Bases from multiple folders

Run Step 3 once per KB, pointing `--kb-name` and `--folder` at the matching
pair each time. The same `--checkpoint` file is safe to reuse across all of
them — it's keyed by absolute file path, so runs against different folders
never collide.

## Files in this skill

```
scripts/
  workato_client.py    Shared HTTP client — DC resolution, retry/backoff, timeout
  init_kb_ingest.py     Idempotent provisioning (Step 2)
  ingest_folder.py      Checkpointed bulk uploader (Step 3)
templates/
  ingest_recipe_code.json   Verified, working recipe `code` blob
references/
  gotchas.md            Everything that cost real debugging time — READ THIS FIRST when troubleshooting
  api-reference.md       Roles, endpoints, response shapes, recipe I/O contract
```

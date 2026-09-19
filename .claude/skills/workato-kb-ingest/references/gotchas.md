# Gotchas — all verified live, not from documentation

Every item here cost real debugging time in the reference build (the
EnterpriseRAG-Bench suite) because it isn't discoverable from Workato's own
docs. Read this before assuming an ingestion failure is a data problem.

## 1. Content-type auto-detection has real false positives on plain text (the big one)

`enterprise_context.upsert_documents` will auto-detect each document's MIME
type by sniffing its raw body **when the `content_type` field is left
blank**. That sniffer misclassifies some plain text as binary formats.

**Verified example:** in a 512K-document corpus, 97 documents failed with:

```
Unsupported content type 'image/x-portable-bitmap'. Supported types:
application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document,
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
application/vnd.openxmlformats-officedocument.presentationml.presentation,
text/csv, text/plain, text/html, application/vnd.oasis.opendocument.text,
application/rtf, text/rtf, application/epub+zip, application/json, text/json,
text/markdown, text/x-markdown, text/x-rst, text/restructuredtext,
text/asciidoc, text/x-asciidoc
```

Root-caused by pulling the actual job record via the Dev API
(`GET /recipes/{recipe_id}/jobs/{job_id}`) for one specific failed document —
a plain-text incident postmortem whose content happened to open with
`"P1 Incident Postmortem: ..."`. `P1` is the literal magic-number prefix for
NetPBM ASCII bitmap images (`.pbm`), so the sniffer read the document's
opening bytes as an image file header and rejected it. A second cluster of
failures were Slack-thread exports opening with a channel name
(`"design\n\n..."`) that the same sniffer misclassified via a different
false positive.

**Critically: Workato reports every one of these as a "succeeded" job**
(`job_failed_count: 0` at the recipe level, HTTP 200). The failure is
buried one level deeper, inside the `upsert_documents` action's own
`failed_documents` output — a plain job-status check will tell you
everything is fine when it isn't. If documents seem to silently vanish from
a Knowledge Base, always inspect the actual `failed_documents` array the
recipe returns, not just whether the job "succeeded."

**Fix:** the `documents` array's `content_type` sub-field is a toggle field
(pick from a picklist, or free-text a MIME string) that bypasses
body-sniffing entirely when set. `ingest_folder.py` in this skill always
sets it explicitly, mapped from file extension (`CONTENT_TYPE_BY_EXTENSION`)
— never leave it blank, regardless of how confident you are the content
"obviously" is text.

## 2. There is no generic file-upload API

`POST /api/files` returns a 404 — verified live, it does not exist. There is
no Workato REST endpoint to hand an arbitrary local file into File Storage
or a Knowledge Base directly. The only path in is a recipe with
`enterprise_context.upsert_documents` (a **batch** action, up to 100
documents per call) sitting behind an API-Platform-triggered
`workato_api_platform.receive_request`. This is why the pattern in this
skill exists at all — it's not a workaround for a missing feature in this
skill, it's the actual, only mechanism.

## 3. List-endpoint response shapes are wildly inconsistent

Every list endpoint used across provisioning wraps its array differently —
verified live against all of them:

| Endpoint | Wrapper |
|---|---|
| `GET /api/folders` | bare array |
| `GET /api/api_collections`, `/api/api_endpoints`, `/api/api_clients`, `/api/api_access_profiles` | bare array |
| `GET /api/agentic/knowledge_bases` | `{"data": [...]}` |
| `GET /api/recipes` | `{"items": [...]}` |

Do not assume one endpoint's wrapper shape generalizes to the next — check
each one live before trusting a `.get("data", [])` or similar pattern
copied from a different endpoint.

## 4. Access-profile auth header is `api-token`, not `Authorization: Bearer`

An API-Platform access profile with `auth_type: "token"` expects the
caller to send `api-token: <secret>` as its own header — **not**
`Authorization: Bearer <secret>`, which is what every other Dev API call in
this pattern uses. Sending Bearer auth against a token-type access profile
returns a 401. `ingest_folder.py`/`init_kb_ingest.py`'s `WorkatoClient.call`
accepts `extra_headers` for exactly this — the harmless default
`Authorization: Bearer` header it always sends is ignored by these
endpoints, so no special-casing is needed beyond adding `api-token`.

## 5. An access profile's secret is only ever returned once

At creation, or via `PUT /api/api_access_profiles/{id}/refresh_secret` —
never on a plain `GET`. `init_kb_ingest.py` refreshes the secret on every
re-run against an existing access profile so the manifest it writes always
has a working token, but that means **re-running `init_kb_ingest.py`
invalidates whatever token a previous provisioning run handed out**. If
something else (a different script, a saved credential) depends on the old
token surviving, capture it before re-running provisioning.

## 6. Batch size limit is 100 documents per call

`upsert_documents`'s declared limit. `ingest_folder.py` batches accordingly
(`BATCH_SIZE = 100`) — raising this in a fork of the script will just start
failing calls once the real limit is crossed; it isn't a soft/adjustable
default.

## 7. Timeouts need real headroom under load

A 30-second client timeout was observed to consistently fail the same
question/call twice in a row under real load — not random flakiness, a
genuine backend stall. `workato_client.py` defaults to a 120-second
timeout. Even at 120s, a burst of concurrent calls (e.g. `--parallelism 5`
against a busy workspace) can still produce a cluster of `504`s — this
looks like transient backend rate-limiting/slowness rather than a client
bug, and the practical mitigation is simply retrying the specific failed
calls afterward (both scripts in this skill are checkpointed/resumable
specifically so retrying a subset is cheap).

## 8. Freshly ingested KBs need minutes before search returns results

Verified live on 2026-09-09 (needle-in-a-haystack benchmark): immediately
after `upsert_documents` reported success (49 documents, ~665 KB), search
calls against the KB returned **HTTP 500** for several minutes. The KB
showed the right `storage_size` and the ingest jobs showed 0 failures —
the index simply wasn't ready yet. Do not treat a `search_documents` 500
right after ingestion as a broken recipe/endpoint; retry with backoff
before debugging anything else.

## 9. API-Platform collections are matched by NAME across projects

Provisioning that looks up an API collection by name ("NIAH Search") will
**reuse another project's existing collection** when names collide —
silently binding a new project's endpoint to the OLD project's recipe.
Verified live: a new project's ingest/search recipes showed 0 job counts
while all traffic flowed to the earlier project's recipes, because the
collection name and URL slug were already taken
(`apim.workato.com/<org>/niah-search-v1/search`). Fix: scope
collection/client/access-profile names with the project name so each run
mints its own slugs, and verify with a test call that the NEW recipe's
`GET /api/recipes/<id>/jobs` actually shows the job.

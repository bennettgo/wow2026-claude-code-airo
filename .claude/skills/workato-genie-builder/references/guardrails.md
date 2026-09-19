# Guardrails — Developer API reference

How to read and manage a genie's content-safety **guardrails** via the Dev API. Verified live against US prod on 2026-06-22 (`genie_guardrails_enabled` on). Public docs: `workato-api/agent-studio#guardrails`.

## Model

- A **guardrail** is a container attached 1:1 to a genie. When present, every chat turn is evaluated against its **policies** before the model responds.
- A **policy** has a `policy_type` and a `configuration` object whose shape depends on the type.
- **Defaults:** when a guardrail is first attached, it ships with `prompt_attack` (`strength: LOW`) and `harmful_content` (all five filters at `LOW`). Other types don't exist until you `PUT` them.
- **Feature-flagged:** all endpoints `404` when `genie_guardrails_enabled` is off for the environment. A `200` from `GET …/pii_entities` is the quickest flag check.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/agentic/genies/:genie_id/guardrails` | Returns `{ data: { id, policies: [...] } }`. `{ id: null, policies: [] }` when no guardrail is attached. |
| PUT | `/api/agentic/genies/:genie_id/guardrails/policies/:policy_type` | **Upsert.** Creates the policy if absent, else **replaces its `configuration` in full** (no partial merge — always send the complete config). Body: `{ "configuration": { ... } }`. |
| GET | `/api/agentic/genies/guardrails/policies/pii_entities` | Lists the PII entity strings for a `pii_detection` policy. Environment-agnostic. |

`GET /api/agentic/genies/:genie_id` also returns a top-level `guardrails` object **when the flag is on** (key omitted when off; `null` when on but no guardrail). Note: the **list** endpoint (`GET /genies`) does *not* include it — only the single-genie show does.

Privileges (in the `genies` group): `guardrails.show`, `guardrail_policies.update`, `pii_entities.index`.

**Endpoint gotcha:** guardrails are written **per-policy** at `…/guardrails/policies/:policy_type` — **not** by `PUT`ing a `guardrails` field on the genie object (`PUT /api/agentic/genies/:id` silently ignores it). Hitting the genie object is the usual reason someone concludes "guardrails are read-only." They aren't.

## Policy types & configuration

| `policy_type` | `configuration` shape |
|---|---|
| `harmful_content` | `{ "filters": [ { "type": <cat>, "strength": <LOW\|MEDIUM\|HIGH> }, … ] }` — `filters` non-empty. Categories: `HATE`, `INSULTS`, `SEXUAL`, `VIOLENCE`, `MISCONDUCT`, `PROMPT_ATTACK`. `NONE` not accepted — omit the entry instead. |
| `prompt_attack` | `{ "strength": <LOW\|MEDIUM\|HIGH> }` |
| `pii_detection` | `{ "enabled": <bool>, "action": <BLOCK\|ANONYMIZE\|TOKENIZE>, "pii_entities": [{ "type": <E> }], "pii_custom_regexes": [{ "name", "pattern" }] }` — when `enabled`, need a non-empty `pii_entities` **or** `pii_custom_regexes` (≤10, pattern ≤500 chars). `action` required even when disabled. |
| `topic_boundary` | `{ "topics": [ { "name" (≤50), "description?" (≤300), "examples?": [≤5 × ≤300] } ] }` — `topics` non-empty, ≤30. |
| `profanity_filter` | `{ "enabled": <bool> }` |
| `custom_word_filter` | `{ "custom_words": [ … ] }` — ≤100 entries, each ≤50 chars; may be `[]` to clear. |

## Disabling / removing policies (verified — the non-obvious part)

There is **no `DELETE`** — you can't remove a policy, only reconfigure it. To turn one off, set the type's "off" value (NOT a generic `enabled` — that key is rejected on the strength-based types):

| Policy | How to turn it off |
|---|---|
| `prompt_attack` | **`{"strength": "NONE"}`** — verified live (this is what the UI's off toggle writes). `NONE` is a valid strength here. Sending `enabled` → **422**. |
| `harmful_content` | Set each category's filter to **`strength: "NONE"`** to disable it (verified — all-`NONE` filters returns `200`). `filters` must stay non-empty (empty array → **422**); sending `enabled` → **422**. So full-off = keep all five entries with `strength: "NONE"`. |
| `pii_detection`, `profanity_filter` | `enabled: false`. Stays attached, takes no action. |
| `custom_word_filter` | `custom_words: []`. |
| `topic_boundary` | `topics` must stay non-empty — reconfigure rather than empty it. |

**Key correction:** the public docs say `strength` is only `LOW/MEDIUM/HIGH` and "`NONE` isn't accepted." That's wrong — **`NONE` is the off value** (at least for `prompt_attack`, verified). The two default policies (`prompt_attack`, `harmful_content`) **can be turned off** (`NONE`), just not deleted. Don't repeat the "can only minimize to LOW" claim — set `NONE`.

## Errors

| Status | When |
|---|---|
| `401` | Missing/invalid token. |
| `404` | Genie unknown, outside folder scope, no guardrail attached (on `PUT`), **or the feature flag is off**. |
| `400` | `policy_type` not one of the six valid values. |
| `422` | `configuration` failed validation — unknown key, missing required key, invalid enum, empty where non-empty required (e.g. `harmful_content` `filters:[]`), limits exceeded. Body: `{ "errors": [ { "code": 422, "title", "detail" } ] }`. |

## Quick verification recipe

```bash
T=<wrkaus-…>; B=https://www.workato.com; G=gin-…
curl -sS -H "Authorization: Bearer $T" "$B/api/agentic/genies/guardrails/policies/pii_entities"   # 200 => flag on
curl -sS -H "Authorization: Bearer $T" "$B/api/agentic/genies/$G/guardrails"                       # current policies
# write (full-replace upsert); always send the COMPLETE configuration:
curl -sS -X PUT "$B/api/agentic/genies/$G/guardrails/policies/prompt_attack" \
  -H "Authorization: Bearer $T" -H "Content-Type: application/json" \
  -d '{"configuration":{"strength":"HIGH"}}'
```

When testing writes on a real genie, **read the current config first and PUT it back afterward** to restore baseline — there's no DELETE/undo.

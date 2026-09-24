# Stage 5 build brief: hand this to a second Claude Code session

This is a work order, not a status tracker. `docs/runbook.md` stays the single source of truth for open items; once this build is done, fold the result back into that file's checklist rather than maintaining this one in parallel. Written 2026-09-20 so a second session, running at the same time as the one that wrote it, can build stage 5 of the WoW 2026 talk without re-deriving anything already verified.

## Why this exists

Stage 4 already rebuilt the store-ops-desk scenario around John, a store manager with four jobs to be done: review cases, reply by email, resolve with a refund or exchange, open new cases. That rename and reseed is done (see "Already done" below). Stage 5 is the remaining four skills, and it's independent enough from the slide/talk-track work happening in the other session to build in parallel.

## Coordination rule, read this first

Two Claude Code sessions are touching this repo at once. To avoid clobbering each other:

- **Do not edit `docs/runbook.md` or `~/Documents/WoW2026-local-drafts/talk-track.md` while this brief is in progress.** The other session owns those. When this build is done, report back in chat (or leave a note at the bottom of this file) and let the other session fold the result into both.
- Everything in this brief happens in the live Workato workspace, not in git. There's nothing to commit until both sessions agree it's ready.
- If you need to touch any file in this repo other than this one, stop and say so first.

## Environment

Workato preview, workspace **IDEA Lifestyle Customer Data & Personalization** (325807). Build inside project **AIRO + Claude Code - WoW 2026** (project `555716`), folder **Customer Service MCP** (`583808`).

Connections, already authorized:

| Connection | ID | Provider |
|---|---|---|
| SFDC - DEV | 105904 | salesforce |
| Ideal Lifestyle | 105903 | slack |

Use `workato-airo-mcp-preview` to build (the `workspace_*` and `recipe.*` tools). Read **`.claude/skills/workato-airo-build-notes/SKILL.md`** before you start; it has real, dated gotchas (the `config: []` requirement for skill-triggered recipes, skill-handle attachment, why `get_recipe_test_status` lies, the exact `context` shape `recipe.test.start` needs for a `workato_skill` trigger versus a `workato_recipe_function` trigger — the second one bit this build with two bare HTTP 500s before the fix was to call `recipe.test.input-schema` per recipe instead of reusing another recipe's schema).

## Already done, don't redo this

- `get_ticket_status` renamed to **`get_case_status`** (recipe `1874280`, skill `skl-AbeCbWnX-bJXKsX-B6`, unchanged handle). Mechanism untouched. Reseeded against a real customer case, **00001294**: Priya Shah, a Branchwood sofa with a torn cushion, High priority, refund requested. Live-tested, returns clean.
- Two skills that didn't map to any of John's four jobs are **detached** from both the MCP server and the Genie. Deleting the underlying recipes outright is tracked in `docs/runbook.md`'s open items, not here.
- The MCP server **Customer Service MCP** (`mcps-AbeCb9on-A3k-B6`) and the Genie **Store Ops Assistant** (`gin-AbeCe4wk-RppDtt-B6`) are both already updated to drop those two tools and to rename the `get_ticket_status` entry to `get_case_status`.

## What to build

Four items. The first two are renames with no logic change, matching the pattern already used for `get_case_status`. The other two are new.

### 1. `review_open_cases` (rename of `list_my_open_tickets`)

Recipe `1874278`, skill `skl-AbeCYPnF-weDEYL-B6`. Pull it, rename the function and the recipe's `name`/`description` from "ticket" language to "case" language, leave the SOQL and logic untouched. Push. Then update its entry in the MCP server's `tools` list the same way `get_case_status`'s was updated (`workspace_pull` the MCP server, edit that one `SkillRecipeMCPTool`'s `name`/`title`/`description`, push).

### 2. `create_case` (rename of `raise_store_ticket`)

Recipe `1874277`, skill `skl-AbeCXswG-WWNpEJ-B6`. Same treatment: rename only, same field structure (`store_name`, `subject`, `description`, `priority`), update the MCP server tool entry to match.

### 3. `log_case_email_reply` (new)

Job 1b: draft a reply and log it on the case. **This does not send a real email.** No email connector is authorized in this workspace, and even if one were, sending mail to a fictional customer address in a live demo is the wrong call. Claude drafts the reply text; this skill logs it as a Salesforce `EmailMessage` record on the case, which is what actually shows up in Salesforce as the reply.

Verified fields on `EmailMessage` (via `create_custom_object(sobject_name='EmailMessage')` and `recipe.input_schema.get`):

- `Status` is the only required field. Picklist: `0`=New, `1`=Read, `2`=Replied, `3`=Sent, `4`=Forwarded, `5`=Draft. Use `3` (Sent) to represent a reply that went out.
- `ParentId` is labeled "Case ID" in this schema, despite the generic name. This is the field that links the email to the case. Look up the Case's `Id` by case number first (same SOQL pattern as `get_case_status`), then pass it here.
- `Subject`, `TextBody`, `ToAddress`, `FromAddress`, `Incoming` (boolean, set `false`) are all optional but worth setting so the record reads like a real reply.

Shape: `workato_skill.start_workflow(case_number, reply_text)` → SOQL lookup on `Case` by `CaseNumber` for `Id` and `Subject` → `salesforce.create_custom_object(sobject_name='EmailMessage', ParentId=<case Id>, Subject=f"Re: {case Subject}", TextBody=<reply_text>, Incoming=False, Status='3')` → `workflow_return_result`. Add the not-found branch on the case lookup, same pattern as every other skill in this build; AIRO's validator will flag it if you skip it.

### 4. `issue_refund` (new)

Job 3, half of it: issue a refund. Verified fields on `Refund` (Order Management's standard object):

- Required: `Amount` (number), `ProcessingMode`, `Status` (`Draft`/`Processed`/`Canceled`/`Pending`/`Failed`, use `Processed` for the demo), `Type` (`Referenced`/`NonReferenced`, use `NonReferenced` since there's no real payment or order behind this).
- **`ProcessingMode`: use `External`, not `Salesforce`.** `recipe.picklist.list` lists both `Salesforce` and `External` as valid, but this org's live write validation rejects `Salesforce` with `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` (confirmed 2026-09-20, in a dry run against this exact recipe). The picklist call reports the connector's generic metadata, not this org's restricted-picklist configuration, don't trust it over an actual test write.
- **No field on `Refund` links back to a Case.** It's built for Order Management's payment model (`PaymentId`, `RefundLinePayment`), not customer service. Resolved 2026-09-20: write the case number into the free-text `GatewayResultCodeDescription` field (`f"Case {case_number}: {reason}"`), so a raw Refund record stays traceable to its case without relying on conversation history. This is a workaround, not a real relationship, say so if it comes up on stage.

Shape: `workato_skill.start_workflow(case_number, amount, reason)` → SOQL lookup on `Case` for `Id`/`Subject` (not-found branch) → `salesforce.create_custom_object(sobject_name='Refund', Amount=<amount>, ProcessingMode='External', Status='Processed', Type='NonReferenced', GatewayResultCodeDescription=f"Case {case_number}: {reason}")` → maybe also update the Case (`Status='Closed'` or similar) so the case reflects resolution → `workflow_return_result`.

### 5. `process_exchange` (new)

Job 3, the other half: process an exchange. Verified fields on `ReturnOrder`:

- Nothing is strictly required by Salesforce's own validation.
- `CaseId` exists and is exactly what you want, a real relational link to the case (unlike `Refund`).
- `Status` picklist, resolved 2026-09-20: `Draft`, `Submitted`, `Approved`, `Canceled`, `Closed`, `Pending Exchange`. Use `Pending Exchange`, it's the semantically correct one for "processing an exchange," not just `Draft`.

Shape: `workato_skill.start_workflow(case_number, item_description)` → SOQL lookup on `Case` for `Id` (not-found branch) → `salesforce.create_custom_object(sobject_name='ReturnOrder', CaseId=<case Id>, Status='Pending Exchange')` → `workflow_return_result`.

## Dry-run status, 2026-09-20

All five items in this brief were rehearsed end to end in a background agent, built into Test Runs (`583807`), not the production folder or MCP server. Every rename and every new skill tested clean on the first or second try, with the two corrections folded into this brief above (`ProcessingMode`, `ReturnOrder.Status`). If you're picking this brief up fresh, the risk that would have cost you time is already resolved, build directly from the specs above rather than re-deriving them.

## Build status, 2026-09-20: done for real

This brief is closed. All five items are built into the production folder (`583808`) and attached to the real MCP server and Genie:

- `review_open_cases` (recipe `1874278`, `skl-AbeCYPnF-weDEYL-B6`), renamed from `list_my_open_tickets`.
- `create_case` (recipe `1874277`, `skl-AbeCXswG-WWNpEJ-B6`), renamed from `raise_store_ticket`.
- `log_case_email_reply` (recipe `1875095`, `skl-AbebHWDY-BNb3J4-B6`), new. Tested live: created real `EmailMessage 02sKa00000X6fBOIAZ` on case `00001294`.
- `issue_refund` (recipe `1875096`, `skl-AbebHoxP-Xmog4W-B6`), new. Tested live: created real `Refund 0cbKa0000001EwwIAE`.
- `process_exchange` (recipe `1875097`, `skl-AbebJCLJ-C9teHK-B6`), new. Tested live: created real `ReturnOrder 2oNKa000000I1agMAC`.

All five attached to **Customer Service MCP** (`mcps-AbeCb9on-A3k-B6`) and to **Store Ops Assistant**'s `skill_ids` (`gin-AbeCe4wk-RppDtt-B6`), alongside `get_case_status`. Both pushed and re-verified with a platform `workspace_read`.

One new gotcha this build, not covered by the dry run because the dry run's MCP server work happened in a scratch folder: a brand-new `SkillRecipeMCPTool` entry (`id=None`) rejects an explicit `name`/`title`/`description`, they're assigned by Workato from the skill. Only an existing tool's fields can be edited directly. Folded into `.claude/skills/workato-airo-build-notes/SKILL.md`.

`Refund.GatewayResultCodeDescription` as the case-number workaround (no real `Refund`-to-`Case` link exists) held up in the real build the same as the dry run.

Cleanup items from this build (deleting the two out-of-scope recipes, the `active=False` question) are not part of this brief; see `docs/runbook.md`'s open items.

## After all four are built

1. Convert each new recipe to a skill (or let the push do it automatically, the way `workspace_push` already has for every `workato_skill`-triggered recipe in this build, per the build notes).
2. Attach all four to the MCP server's `tools` list (three new `SkillRecipeMCPTool` entries plus the two renames from steps 1-2 above) and to the Genie's `skill_ids`.
3. Test each one live with `recipe.test.start`, using `recipe.test.input-schema` per recipe first, not a copy-pasted `context` shape from another recipe.
4. Report back: what got built, what got renamed, any real gotcha worth adding to `.claude/skills/workato-airo-build-notes/SKILL.md`, and whether the `Refund`-has-no-Case-link problem got resolved or just documented. The other session will fold this into `docs/runbook.md`'s open items and update `talk-track.md`'s stages 5 and 6 to match, the same way stage 4 was updated after its rebuild.

## Style

If you write anything a human reads (recipe descriptions, this file's own updates, a chat summary), keep it plain: state the fact, then why if it matters, no flourish. The repo's `unslop` and `my-writing-style` skills aren't vendored here (personal skills folder, deliberately not checked in), but the tone they enforce is: short sentences, no "delve"/"leverage"/"showcase", no em dashes, active voice, name the mechanism instead of describing how it feels.

# Runbook - Claude Code + AIRO: From Vibe Coding to Production, Live

Stage-by-stage detail under the [session outline](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc). The outline governs the flow. This file records how each stage runs, what is decided, and what is not.

**Status:** stages 4 through 6 rehearsed end to end 2026-09-19, live against the workspace, then rebuilt around John's four jobs to be done and pushed for real 2026-09-20. Every skill below was built, pushed, and tested against the production folder and the live MCP server and Genie; every case number and ID is real. Stages 3, 7, 8 remain proposals. See "Open items" for the cleanup still needed before the real talk.

**Environment:** Workato preview, workspace "IDEA Lifestyle Customer Data & Personalization" (325807), root folder `577822`, environment Development. Build project moved to **"AIRO + Claude Code - WoW 2026"** (`555716`, folder `583806`), created 2026-09-19. This replaces the earlier plan to use `555710` / `583790`: that project turned out to hold a finished, unrelated account-health build owned by Loma Desai, so the grant gap recorded below was never a misconfiguration, it was the correct block on a project that was not ours. `583806` holds two subfolders: `Test Runs` (`583807`) for seeding utilities, `Store Ops Desk` (`583808`) for the real build. Authorized connections: Salesforce `SFDC - DEV` (105904), Slack `Ideal Lifestyle` (105903), REST `TypeSafe AI` (108365).

Both MCP servers point at that workspace. AIRO MCP is `https://app.preview.workato.com/airo_mcp` over OAuth; Dev API MCP is `https://app.preview.workato.com/mcp` with a bearer token. Verified 2026-09-19: the Dev API token resolves to workspace 325807 with root folder 577822, the same workspace AIRO builds into.

---

## Timing

The outline gives times for the opening, the company intro and Q&A only. The rest is proposed here and unconfirmed.

| Stage | Minutes | Source |
|---|---|---|
| 1. Opening | 2 | outline |
| 2. IDEA Lifestyle and the scenario | 1.5 | outline |
| 3. Connect Claude Code to AIRO MCP + Dev API MCP | 3 | proposed |
| 4. Build with AIRO | 7 | proposed |
| 5. Scale with AIRO | 7 | proposed |
| 6. Automate with AIRO | 7 | proposed |
| 7. Tune your build with AIRO | 4 | proposed |
| 8. Co-speaker (Abhishek Bhattacherjee) | 8 | proposed |
| 9. Q&A | 5 | outline |
| **Total** | **44.5** | |

Stages 4 through 6 carry equal weight on purpose. Each is one turn of the same loop at a larger scale, and an uneven split makes the journey read as one real stage plus filler.

---

## 1. Opening: build speed is not ship speed (2 min)

Reuse the Product Hour slide: "anyone can lay a plank" plus the production-grade demands checklist. Land the thesis: watch the whole gap close, live, one prompt at a time.

Name both planes here, once, and do not repeat the framing later. Execution Plane is Claude Code and AIRO turning intent into running assets. Control Plane is validation and guardrails before anything goes live.

## 2. IDEA Lifestyle and the scenario (1.5 min)

Company snapshot: $47B, 800+ stores, 50+ countries, home furnishings.

Then the scenario, in two sentences:

> A store manager's day is full of small operational questions. Damaged stock, a broken chiller, whether they can approve an overtime shift. Today each one means digging through a policy portal or emailing head office and waiting.

Keep it boring and legible. It has to carry stages 4 through 6 without being re-explained, so resist adding detail that sounds interesting now and costs time later.

## 3. Connect Claude Code to AIRO MCP and Dev API MCP (3 min, proposed)

Show the wiring briefly. This is setup, not a tutorial, and the room only needs to believe the connection is real.

Say the division of labour out loud, because the rest of the session depends on it:

- AIRO MCP builds and mutates.
- Dev API MCP reads and audits, and never builds anything.

If AIRO both builds the thing and reports that the thing works, there is no reason to believe the report. That is the whole argument for having two.

What is actually on screen:

| Role | Endpoint | Auth |
|---|---|---|
| Builds | `https://app.preview.workato.com/airo_mcp` | OAuth, browser prompt on first connect |
| Audits | `https://app.preview.workato.com/mcp` | Bearer token from an API client |

The Dev API side is worth one sentence out loud: its permissions come from the
API client role, so the auditing server can be scoped read-only and the split
stops being a promise about behaviour.

Docs open: https://docs.workato.com/en/airo/mcp and https://docs.workato.com/en/mcp/developer-api-mcp

## 4. Build with AIRO (7 min, proposed)

Journey slide: **build**.

One skill, end to end. Proposed: **`get_ticket_status`**, a Salesforce Case lookup by case number. Smallest useful thing a store manager would ask for, one connector, logic simple enough to read on screen.

- Create it from a plain-language description.
- Test it. `test_recipe_input_schema` first, because skills have no pollable trigger and it hands back a ready-to-paste sample event.
- Read the recipe logic on screen, so it lands as a real Workato asset rather than a black box.
- Ask for a change: also return the assigned owner and the last comment. Re-test. Confirm in the job log.

The change beat is the one that matters. Building something is unremarkable now. Changing it and proving it still works in the same breath is not.

Two gotchas that will bite live, both in `.claude/skills/workato-airo-build-notes/`: a `workato_skill` recipe needs `"config": "[]"` at creation or it cannot start, and `get_recipe_test_status` reports `NO_TEST_RUN` even after a job has succeeded, so read the job list instead.

## 5. Scale with AIRO (7 min, proposed)

Journey slide: **scale**.

Generate the rest of the desk in one pass rather than one at a time, matching John's four jobs to be done from stage 2:

| Skill | Backed by | Job |
|---|---|---|
| `review_open_cases` | Salesforce Case query by store | Review cases |
| `log_case_email_reply` | Salesforce `EmailMessage` on the case | Reply by email |
| `issue_refund` | Salesforce `Refund` (Order Management) | Resolve, refund |
| `process_exchange` | Salesforce `ReturnOrder` | Resolve, exchange |
| `create_case` | Salesforce Case create | Open a new case |

Then bundle all five, including `get_case_status` from stage 4, into a **Store Ops Desk** MCP server (`mcps-AbeCb9on-A3k-B6`), and show a teammate using it from their own client.

Payoff line: a Workato Skill is an MCP tool, an MCP server is a bundle of them, and what you just built is now something store managers use without ever opening Workato.

Attachment gotcha: convert each recipe to a Skill and attach by its `skl-*` handle. A raw recipe ID fails with `invalid asset`. New gotcha found building this for real, 2026-09-20: an MCP tool entry for a brand-new skill must be added with only `id=None` and `skill_handle=...`, nothing else. Setting `name`/`title`/`description` on it explicitly is rejected outright, they're assigned by Workato from the skill. Only an already-existing tool's `name`/`title`/`description` can be edited directly.

Second real gotcha from the same build: `Refund` has no field that links back to a Case, it's built for Order Management's payment model. Worked around by writing the case number into `Refund.GatewayResultCodeDescription`. Say so on stage if it comes up; it's a workaround, not a real relationship.

## 6. Automate with AIRO (7 min, proposed)

Journey slide: **automate**.

The narrative turn: the desk has been working well, and the same skills would do more good running without someone in front of them.

- Generate a **Store Ops Assistant** Genie over the five skills.
- Attach a Knowledge Base holding store operations policy: returns and damages, refund thresholds, the exchange approval matrix. This is where the KB earns its place, because policy questions are exactly what a manager cannot answer from a system record. Still empty as of 2026-09-20, see open items.
- Test the Genie.
- Put it behind a recipe triggered on new Salesforce Cases, so it assigns the case to the Genie and the Genie decides refund versus exchange, logs a reply, and flags anything High priority. Built: **`case_intake_automation`** (recipe `1875099`). Now it runs unattended.

The honest reason to automate: triage is repetitive, policy-driven, and happens at 800 stores. That is a defensible case for an agent, and it is worth saying why rather than assuming the room agrees.

## 7. Tune your build with AIRO (4 min, proposed)

Journey slide: **flywheel**.

- Save the tribal knowledge from this build as agent skills in the repo. `.claude/skills/workato-airo-build-notes/` already exists and was written exactly this way, so this is a demonstration rather than a promise.
- Run scripts that check the skills and the Genie for regressions.
- Push the repo so someone else can continue.

Land it as: the next person does not start where we started.

> **Open.** The regression scripts do not exist yet.

## 8. Co-speaker (8 min, proposed)

Abhishek Bhattacherjee. Their lens: what it actually took on their side to work with AIRO MCP, and how they found success with it.

## 9. Q&A (5 min)

---

## FAQ

Carried from the outline. **The first is current; the rest were written for the retired sell-through drift storyline and need rewriting against store operations.**

- **"Why not just vibe-code the whole thing in Claude?"** Consistency (a Genie is a governed, repeatable skill versus freehand LLM drift), business-event listening instead of polling, verified user access, and staying inside one governed environment. Adapted from the Daman Arora Product Hour precedent.
- *(stale)* "Why do you need a Genie at all, shouldn't low stock just trigger a reorder?"
- *(stale)* "Does the Genie ever investigate on its own, without a human?"
- *(stale)* "What happens if none of the three candidates explain it?"

Likely replacements worth planting: why a Genie rather than a routing rule for triage, what happens when the policy KB does not cover a case, and who is accountable when the agent escalates wrongly.

---

## Open items

Rehearsal build, 2026-09-19, project `555716` / folder `583806`. All five skills are pushed, tested, and verified with real job output, not assumed.

- [x] ~~Verify the Salesforce dev org supports the design.~~ Done. Confirmed again in this rehearsal.
- [x] ~~Fix the project grant gap.~~ Moot. The blocked project (`555710`) was never ours to write into, it holds Loma Desai's account-health build. Moved to a fresh project (`555716`) instead of chasing a grant. See the environment note above.
- [x] ~~Seed Salesforce Cases.~~ Done. Five real cases: `00001289` (Store 482, chiller failure, High), `00001290` (Store 217, overtime approval, Medium), `00001291` (Store 103, water damage, Medium), `00001292` (Store 356, loading dock door, High), `00001293` (Store 103, register fault, Medium, created live by `raise_store_ticket` during the rehearsal).
- [x] ~~Seed store data.~~ Done. Data Table `stores` (numeric id `13564`), four rows, matching the case store names, including a facilities vendor column `get_store_details` reads.
- [x] ~~Build the five store-ops skills and bundle them into an MCP server.~~ Done, for real, 2026-09-20 (not just the dry run). Five JTBD-aligned skills live in the production folder (`583808`) and are attached to **Store Ops Desk** (`mcps-AbeCb9on-A3k-B6`): `get_case_status` (`skl-AbeCbWnX-bJXKsX-B6`, recipe `1874280`), `review_open_cases` (`skl-AbeCYPnF-weDEYL-B6`, recipe `1874278`, renamed from `list_my_open_tickets`), `create_case` (`skl-AbeCXswG-WWNpEJ-B6`, recipe `1874277`, renamed from `raise_store_ticket`), `log_case_email_reply` (`skl-AbebHWDY-BNb3J4-B6`, recipe `1875095`, new), `issue_refund` (`skl-AbebHoxP-Xmog4W-B6`, recipe `1875096`, new), `process_exchange` (`skl-AbebJCLJ-C9teHK-B6`, recipe `1875097`, new). Each tested live with `recipe.test.start`: `review_open_cases` returned 3 open cases, `log_case_email_reply` created real `EmailMessage 02sKa00000X6fBOIAZ` on case `00001294`, `issue_refund` created real `Refund 0cbKa0000001EwwIAE`, `process_exchange` created real `ReturnOrder 2oNKa000000I1agMAC`, `create_case` created a brand-new real case `00001296` (Marcus Webb, IDEAONE House dining chair, Store 217, Medium). MCP server push verified with a platform `workspace_read`: all five tools present, names/descriptions derived correctly for the three new ones. `get_store_details` and `notify_ops_channel` are detached from the MCP server and Genie (neither maps to one of John's four jobs); their recipes still exist on the platform, deleting them outright needs `workato-dev-api-preview`, not connected in this session, see below.
- [x] ~~Build the stage 6 Genie.~~ Done. **Store Ops Assistant** (`gin-AbeCe4wk-RppDtt-B6`), state `active`, all six skills attached (the five above plus `get_case_status`), description and instructions updated 2026-09-20 to name all four jobs to be done. Verified with a platform `workspace_read` after push.
- [ ] **Write and ingest the stage 6 Knowledge Base content.** The KB (`kb-AbeCeRgf-gwgWcE-B6`, "Store Ops Policy") exists and is attached to the Genie, but it's empty. There's a dedicated skill for this, `.claude/skills/workato-kb-ingest/`, which provisions a bulk-ingest recipe and API endpoint and drives it from a local folder of policy docs, and it doesn't go through the direct-file-upload path this session was missing. It does need a working Dev API token for this workspace, driven as raw HTTP calls from its own scripts rather than through an MCP tool, so it isn't blocked by `workato-dev-api-preview` being disconnected the same way deletion is. Confirmed 2026-09-20 that the token itself exists in `.mcp.json` and is presumably still valid, but pulling it out to use directly was blocked by Claude Code's own auto-mode classifier as credential handling, correctly, so this needs to be run either from an interactive session where the user supplies the token directly, or after `workato-dev-api-preview` reconnects and a proper MCP path opens up. Content itself (returns/damages, refund thresholds, the exchange approval matrix, updated 2026-09-20 to match the JTBD pivot away from facilities SLAs) still needs writing regardless of ingestion mechanism.
- [x] ~~Build the case-triggered automation recipe.~~ Built 2026-09-20: **`case_intake_automation`** (recipe `1875099`, folder `583808`). Trigger: `salesforce.new_custom_object(sobject_name='Case', since_offset=0)`. Action: `workato_genie.assign_task_to_genie` targeting **Store Ops Assistant** (`gin-AbeCe4wk-RppDtt-B6`), with a task description built from the case's number, subject, priority, status, and description, asking the Genie to check status, decide refund versus exchange, log a reply if warranted, and flag High-priority cases for a manager. Pushed, statically validated (`ready`/`publishable`). Not confirmed live end to end: testing a polling-trigger recipe doesn't force an immediate poll (new gotcha in the build notes), so creating a real matching case during the test didn't produce a job within about four minutes of waiting, and it wasn't worth waiting out the full poll interval in this pass. Verify separately with lead time before the talk, or start the recipe for real ahead of the segment instead of testing it live on stage.
- [x] ~~Decide how stage 4 uses this rehearsal's `get_ticket_status`.~~ 2026-09-20: renamed to `get_case_status` (same recipe 1874280, same skill handle `skl-AbeCbWnX-bJXKsX-B6`), mechanism unchanged, reseeded against a real customer case (**00001294**, Priya Shah, Branchwood sofa, torn cushion, High priority, refund requested) instead of the old chiller-failure one. Live-tested. Still open: decide whether stage 4 builds this fresh on stage or reuses it. 2026-09-20, dry run: a subagent rebuilt this from nothing in a scratch folder (recipe `1875089`, not the real asset) and replayed all four beats end to end. Three real corrections landed in `.claude/skills/workato-airo-build-notes/SKILL.md` and `talk-track.md`: the `config: []` requirement only applies to the raw Dev API path, not this MCP lifecycle; the not-found validator warning does not visibly clear after the fix, it's a static check; and the `recipe.test.status` lying behavior did not reproduce on demand across two tries, so the talk track no longer promises it fires on cue.
- [ ] Rewrite the three stale FAQ entries against store operations.
- [ ] Build the regression scripts for stage 7.
- [x] ~~Journey slides for stages 4, 5, 6 and 7 do not exist yet.~~ Built 2026-09-19 into the real deck, not just drafted: six new slides (company snapshot, scenario, and one journey slide per stage) cloned from the deck's own layouts so the branding is inherited rather than rebuilt. Local only (`~/Documents/WoW2026-local-drafts/`), not in this repo, per working agreement. The earlier [slide content doc](https://docs.google.com/document/d/1fHm6pUKS-ytpZJJCqXTeeaq45SsKWuZ-unnOqxtiJfA) is superseded by the deck. 2026-09-20: removed the pre-existing agenda slide ("In the next 45 minutes") and full lifecycle slide ("AIRO For Everything") between the bridge slide and the IDEA Lifestyle intro, and added speaker notes to slides 1 through 11 so the deck and `talk-track.md` say the same thing. Deck is now 126 slides. Also added a closing slide, "They start here" (now slide 12), right before Abhishek's title, naming the repo and the two real bugs found while building. Deck is now 127 slides.
- [x] ~~Write a talk track.~~ Draft written 2026-09-19, stages 1 through 7, Bennett's voice. Local only (`~/Documents/WoW2026-local-drafts/talk-track.md`), not in this repo.
- [ ] Confirm the proposed timings for stages 3 through 8 against a rehearsal.
- [ ] Confirm co-speaker logistics with Abhishek.
- [ ] Revoke the two live stub-server tokens (`1e03f322…`, `ff7d7f1c…`, gateways 12572 and 12575). They belong to the retired `sales-inventory-mcp` and `crm-promotions-mcp` servers, are not needed by the store ops build, and are gitignored rather than invalidated. The two in `.codex/config.toml` point at the pre-migration gateways 11680 and 11681 and are already dead; delete them.
- [ ] Decide whether the two retired stub MCP servers on preview should be deleted outright, now that nothing uses them.
- [ ] Delete recipes `1874276` (`get_store_details`) and `1874279` (`notify_ops_channel`) outright. Needs `workato-dev-api-preview` connected; confirmed again 2026-09-20 that this session only has `workato-dev-api` (wrong workspace, IDEA Supplier Management) plus `workato-airo-mcp-preview`, no delete capability exists on the AIRO surface for recipes. Until this is done, both recipes exist on the platform but stay detached from the MCP server and Genie, so they're unreachable, not unmentioned; `talk-track.md` never named them and `docs/stage5-build-brief.md` had its mentions trimmed to just "two out-of-scope skills," this file above is now the only place their names and IDs are recorded, on purpose, so deletion has something to work from.
- [ ] Clean up the stage-5 dry run's leftovers: rehearsal case `00001295` ("Stage 5 rehearsal case") and recipes `1875089`-`1875094` in Test Runs (`583807`). Harmless, low urgency, not attached to anything real.
- [x] ~~Check what the MCP server tools' `active=False` flag means for a live client call.~~ Resolved 2026-09-20. `active` on a `SkillRecipeMCPTool` mirrors whether its backing recipe is started, nothing more. Confirmed by running `recipe.start` on `log_case_email_reply`'s recipe (`1875095`) and watching only that tool's entry flip to `active=True` on the next platform read. This was a real gap, not just a documentation question: `workspace_push` on a new skill-triggered recipe does not start it, so a freshly built skill is unreachable from a real MCP client even though `recipe.test.start` (which bypasses the MCP endpoint entirely) makes it look like it works. Fixed by starting all five recipes (`1874277`, `1874278`, `1874280`, `1875095`, `1875096`, `1875097`); the platform read now shows all five tools `active=True`.

# Runbook - Claude Code + AIRO: From Vibe Coding to Production, Live

Stage-by-stage detail under the [session outline](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc). The outline governs the flow. This file records how each stage runs, what is decided, and what is not.

**Status:** stages 4 through 6 rehearsed end to end 2026-09-19, live against the workspace. Every skill below was built, pushed, and tested; every case number and ID is real. Stages 3, 7, 8 remain proposals. See "Open items" for the cleanup still needed before the real talk.

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

Generate the rest of the desk in one pass rather than one at a time:

| Skill | Backed by |
|---|---|
| `raise_store_ticket` | Salesforce Case create |
| `list_my_open_tickets` | Salesforce Case query by store |
| `notify_ops_channel` | Slack |
| `get_store_details` | Workato Data Table |

Then bundle all five, including `get_ticket_status` from stage 4, into a **Store Ops Desk** MCP server, and show a teammate using it from their own client.

Payoff line: a Workato Skill is an MCP tool, an MCP server is a bundle of them, and what you just built is now something store managers use without ever opening Workato.

Attachment gotcha: convert each recipe to a Skill and attach by its `skl-*` handle. A raw recipe ID fails with `invalid asset`.

## 6. Automate with AIRO (7 min, proposed)

Journey slide: **automate**.

The narrative turn: the desk has been working well, and the same skills would do more good running without someone in front of them.

- Generate a **Store Ops Assistant** Genie over the five skills.
- Attach a Knowledge Base holding store operations policy: returns and damages, facilities SLAs, the approval matrix. This is where the KB earns its place, because policy questions are exactly what a manager cannot answer from a system record.
- Test the Genie.
- Put it behind a recipe triggered on new Salesforce Cases, so it classifies, applies policy, routes, and escalates to Slack when an SLA is at risk. Now it runs unattended.

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
- [x] ~~Build the five store-ops skills and bundle them into an MCP server.~~ Done and tested individually: `get_ticket_status`, `raise_store_ticket`, `list_my_open_tickets`, `get_store_details`, `notify_ops_channel`. Bundled into MCP server **Store Ops Desk** (`mcps-AbeCb9on-A3k-B6`). One real governance finding along the way: an MCP server can only attach skills from its own project, confirmed by a hard `HTTP 400` when the first attempt referenced a skill built in a different project. `get_ticket_status` had to be rebuilt inside `555716` rather than reused.
- [x] ~~Build the stage 6 Genie.~~ Done. **Store Ops Assistant** (`gin-AbeCe4wk-RppDtt-B6`), all five skills attached, state `active`, tested live against case `00001289`.
- [ ] **Write and ingest the stage 6 Knowledge Base content.** The KB (`kb-AbeCeRgf-gwgWcE-B6`, "Store Ops Policy") exists and is attached to the Genie, but it's empty. Uploading a document needs a real Workato File Storage reference from an attachment, which this session didn't have; the heavier `workato-kb-ingest` skill is the fallback if a local folder of policy docs is worth building instead of ad hoc upload. Content itself (returns/damages, facilities SLAs, the approval matrix) still needs writing.
- [ ] **Build the case-triggered automation recipe.** Stage 6's last beat, new Case triggers a Genie assignment plus a Slack escalation on High priority, was scoped but not built this pass, to leave time for the slides and script. Straightforward given everything else that's already wired.
- [ ] **Decide how stage 4 uses this rehearsal's `get_ticket_status`.** It already exists (recipe `1874280`, skill `skl-AbeCbWnX-bJXKsX-B6`). Either delete it before the real talk so stage 4 builds it from nothing on stage, or build the live version into a different folder so the name doesn't collide. See the talk track's note on this.
- [ ] Rewrite the three stale FAQ entries against store operations.
- [ ] Build the regression scripts for stage 7.
- [x] ~~Journey slides for stages 4, 5, 6 and 7 do not exist yet.~~ Draft content written 2026-09-19: [slide content doc](https://docs.google.com/document/d/1fHm6pUKS-ytpZJJCqXTeeaq45SsKWuZ-unnOqxtiJfA) (not in this repo, per working agreement). Needs pasting into the branded template and a design pass.
- [x] ~~Write a talk track.~~ Draft written 2026-09-19, stages 1 through 7, Bennett's voice. Local only (`~/Documents/WoW2026-local-drafts/talk-track.md`), not in this repo.
- [ ] Confirm the proposed timings for stages 3 through 8 against a rehearsal.
- [ ] Confirm co-speaker logistics with Abhishek.
- [ ] Revoke the two live stub-server tokens (`1e03f322…`, `ff7d7f1c…`, gateways 12572 and 12575). They belong to the retired `sales-inventory-mcp` and `crm-promotions-mcp` servers, are not needed by the store ops build, and are gitignored rather than invalidated. The two in `.codex/config.toml` point at the pre-migration gateways 11680 and 11681 and are already dead; delete them.
- [ ] Decide whether the two retired stub MCP servers on preview should be deleted outright, now that nothing uses them.

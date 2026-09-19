# Runbook - Claude Code + AIRO: From Vibe Coding to Production, Live

Stage-by-stage detail under the [session outline](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc). The outline governs the flow. This file records how each stage runs, what is decided, and what is not.

**Status:** use case and environment decided 2026-09-19. Nothing built yet. Stage designs below are proposals, not rehearsed.

**Environment:** Workato preview, workspace "IDEA Lifestyle Customer Data & Personalization" (325807), root folder `577822`, environment Development. Build into project "Idea Lifestyle Conference Demo" (`555710`, folder `583790`), which holds one unrelated recipe today (`1874206`, "Send email to the product line supplier"). Authorized connections: Salesforce `SFDC - DEV` (105904), Slack `Ideal Lifestyle` (105903), REST `TypeSafe AI` (108365).

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

- [x] ~~Verify the Salesforce dev org supports the design.~~ Done 2026-09-19. The `get_ticket_status` skill was built, pushed and tested green against `SFDC - DEV`. Salesforce connects, the Case object is queryable, and a valid SOQL query returns cleanly. Recipe `1874274`, Skill `skl-Abe89XRW-Ct3w3E-B6`, job `j-Abe89tRx-n36Mae-B6`.
- [ ] **Fix the project grant gap on "Idea Lifestyle Conference Demo" (555710, folder 583790).** Diagnosed 2026-09-19 via the Dev API, and it is a one-line fix by someone with the rights.

  | Project | Sole grant | Push |
  |---|---|---|
  | 552603 "AIRO + Claude Code" | Bennett Goh, Project admin | succeeds |
  | 555710 "Idea Lifestyle Conference Demo" | Loma Desai, Project admin | fails |

  Reads see folder `583790` fine, because reads and writes authorize differently. Writes fail with `Folder with id '583790' was not found`, which is a misleading message for "you have no grant here". **Fix:** add Bennett Goh (member `3218`) as Project admin on project `555710`. Loma Desai or a workspace admin can do it. Until then assets land in the wrong project.
- [ ] **Move `get_ticket_status` into the conference demo project** once the grant is fixed. It sits in folder `578470`, project `552603` "AIRO + Claude Code", purely because that is the project Bennett is granted on. That project also holds the two retired stub MCP servers.
- [ ] **Seed Salesforce Cases.** The org has no case `00001026`, and the demo needs specific legible tickets anyway (a chiller repair at a named store, not whatever a dev org happens to hold). Confirm how many Cases exist today, then seed the handful the talk track names.
- [ ] Seed store data. `get_store_details` needs a Data Table of stores, and the Cases need to reference them.
- [ ] Write the store operations policy documents for the stage 6 Knowledge Base.
- [ ] Rewrite the three stale FAQ entries against store operations.
- [ ] Build the regression scripts for stage 7.
- [ ] Confirm the proposed timings for stages 3 through 8 against a rehearsal.
- [ ] Journey slides for stages 4, 5, 6 and 7 do not exist yet.
- [ ] Confirm co-speaker logistics with Abhishek.
- [ ] Revoke the two live stub-server tokens (`1e03f322…`, `ff7d7f1c…`, gateways 12572 and 12575). They belong to the retired `sales-inventory-mcp` and `crm-promotions-mcp` servers, are not needed by the store ops build, and are gitignored rather than invalidated. The two in `.codex/config.toml` point at the pre-migration gateways 11680 and 11681 and are already dead; delete them.
- [ ] Decide whether the two retired stub MCP servers on preview should be deleted outright, now that nothing uses them.

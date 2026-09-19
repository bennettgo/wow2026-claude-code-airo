# Runbook — Claude Code + AIRO: From Vibe Coding to Production, Live

Stage-by-stage detail under the [session outline](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc). The outline governs the flow. This file records how each stage actually runs, what is decided, and what is not.

**Status:** skeleton, written 2026-09-19 after the restructure. Stage content is deliberately thin because the use case is unchosen.

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

## 1. Opening — build speed is not ship speed (2 min)

Reuse the Product Hour slide: "anyone can lay a plank" plus the production-grade demands checklist. Land the thesis: watch the whole gap close, live, one prompt at a time.

Name both planes here, once, and do not repeat the framing later. Execution Plane is Claude Code and AIRO turning intent into running assets. Control Plane is validation and guardrails before anything goes live.

## 2. IDEA Lifestyle and the scenario (1.5 min)

Company snapshot: $47B, 800+ stores, 50+ countries, home furnishings.

Then the scenario, in one or two sentences. It has to carry stages 4 through 6 without being re-explained, so it needs to be boring and legible rather than clever.

> **Open.** See Open items. Nothing below this line can be written until it is picked.

## 3. Connect Claude Code to AIRO MCP and Dev API MCP (3 min, proposed)

Show the wiring, briefly. This is setup, not a tutorial, and the room only needs to believe the connection is real.

Say the division of labour out loud, because the rest of the session depends on it:

- AIRO MCP builds and mutates.
- Dev API MCP reads and audits, and never builds.

Docs to have open: https://docs.workato.com/en/airo/mcp and https://docs.workato.com/en/mcp/developer-api-mcp

## 4. Build with AIRO (7 min, proposed)

Journey slide: **build**.

One skill, end to end. Smallest unit that exists, so the room can follow every step.

- Create the skill from a plain-language use case.
- Test it and verify the result.
- Read the recipe logic on screen, so it is clearly a real Workato asset and not a black box.
- Ask for a change, then re-test and re-validate live.

That last beat is the one that matters. Building something is unremarkable now; changing it and proving it still works in the same breath is not.

Mechanics are in `.claude/skills/workato-airo-build-notes/`. Two that will bite live: `test_recipe_input_schema` must run before `test_recipe` because skills have no pollable trigger, and `get_recipe_test_status` reports `NO_TEST_RUN` even after a job has succeeded, so read the job list instead.

## 5. Scale with AIRO (7 min, proposed)

Journey slide: **scale**.

- Generate several skills at once for the same use case, rather than one at a time.
- Wrap them into an MCP server.
- Show a teammate consuming that server from their own client.

The payoff line: a Workato Skill is an MCP tool, an MCP server is a bundle of them, and what you just built is now something other people use without touching Workato.

Attachment gotcha: convert each recipe to a Skill and attach by `skl-*` handle. A raw recipe ID fails with `invalid asset`.

## 6. Automate with AIRO (7 min, proposed)

Journey slide: **automate**.

The narrative turn: the MCP server has been working well, and the same skills would do more good running without a person in front of them.

- Generate a Genie.
- Attach the skills and the knowledge bases.
- Test the Genie.
- Put it behind a recipe so it runs unattended.

Needs a reason the work should run unattended that follows from the stage 2 scenario. If the use case cannot justify this, it is the wrong use case.

## 7. Tune your build with AIRO (4 min, proposed)

Journey slide: **flywheel**.

- Save the tribal knowledge from this build as agent skills in the repo. `.claude/skills/workato-airo-build-notes/` already exists and was written exactly this way.
- Run scripts that check the skills and the Genie for regressions.
- Push the repo so someone else can continue.

This stage is the argument that the session was not a one-off performance. Land it as: the next person does not start where we started.

> **Open.** The regression scripts do not exist yet.

## 8. Co-speaker (8 min, proposed)

Abhishek Bhattacherjee. Their lens: what it actually took on their side to work with AIRO MCP, and how they found success with it.

## 9. Q&A (5 min)

---

## FAQ

Carried from the outline. **The first is current; the rest were written for the retired sell-through drift storyline and need rewriting once the use case is chosen.**

- **"Why not just vibe-code the whole thing in Claude?"** Consistency (a Genie is a governed, repeatable skill versus freehand LLM drift), business-event listening instead of polling, verified user access, and staying inside one governed environment. Adapted from the Daman Arora Product Hour precedent.
- *(stale)* "Why do you need a Genie at all, shouldn't low stock just trigger a reorder?"
- *(stale)* "Does the Genie ever investigate on its own, without a human?"
- *(stale)* "What happens if none of the three candidates explain it?"

---

## Open items

- [ ] **Pick the use case.** Blocks stages 2 and 4 through 6. It has to satisfy three constraints at once: introducible in about 90 seconds, made of skills an ordinary employee would want in Claude Desktop, and with honest justification for running unattended.
- [ ] Rewrite the three stale FAQ entries once the use case exists.
- [ ] Build the regression scripts for stage 7.
- [ ] Confirm which workspace the session runs on, and whether both MCPs reach it. Preview and production differ in what they expose; see the build notes skill.
- [ ] Confirm the proposed timings for stages 3 through 8 against a rehearsal.
- [ ] Journey slides for stages 4, 5, 6 and 7 do not exist yet.
- [ ] Confirm co-speaker logistics with Abhishek.

---
name: airo-architect
description: Use when a user wants to build a Workato solution (agentic genie or traditional recipe) from a business problem — drives groom → research → plan → build/test/iterate, dispatching a sub-agent fleet and provisioning in a sandbox.
---

## 1. When to use / Entry

Activate this skill when:
- The user invokes `/airo-build` (with or without a problem argument), or
- The user asks to "build a Workato solution", "create a genie", "automate a workflow", or any variant that involves constructing a real Workato asset end-to-end.

If the user invoked `/airo-build` with a problem argument, use it as the starting context for Phase 1. If no argument was provided, ask: "What do you want to build?"

---

## 2. Setup

Before entering the phase loop, complete setup in order:

**a. Derive a slug.**
From the user's stated objective, derive a short kebab-case slug (e.g. `it-support`, `lead-router`, `expense-approver`). The slug becomes the build directory name and is passed to every agent and the workflow. Confirm with the user if it is ambiguous.

**b. Create the build directory.**
Create `builds/<slug>/` in the working directory. All scratchpad artifacts for this build live here.

**c. Confirm DC and builder token.**
The builder-integrator and provision scripts require:
- `WORKATO_DC` — the Workato data-center identifier (e.g. `us`, `eu`). Ask the user if not set.
- `DEV_API_TOKEN` — a Workato Developer API token. Confirm it is available in the environment (the user or environment must supply it). Do not proceed to Phase 4 without it; research and planning can proceed without it.

**d. Pick and confirm the sandbox folder.**
Ask the user which Workato folder to use as the build sandbox. Alternatively, check the platform inventory (Phase 2 research) for an existing sandbox/draft folder. Record the sandbox folder name or id — it is passed as `sandbox_folder` to the Phase 4 workflow. Nothing is built outside this folder until the user explicitly approves promotion.

---

## 3. Phase Loop

Run the four phases in order: **groom → research → plan → build-test-iterate**.

For each phase:
1. Load that phase's reference module (`references/<phase>.md`) into context and follow its procedure exactly.
2. Execute the phase and write its scratchpad artifact to `builds/<slug>/`.
3. Consult `references/review-policy.md` to decide whether to pause for user review before advancing.

### Phase 1 — Groom → `builds/<slug>/requirements.md`

Load `references/groom.md`. Follow its procedure to elicit the seven elements (objective, KPIs+baselines, persona, behavior, guardrails, definition of good, build target), draft `requirements.md`, and loop until the user approves.

**Scratchpad artifact:** `builds/<slug>/requirements.md`
**Review policy:** Tier 2 — pause. Do not advance to Phase 2 without explicit approval.

### Phase 2 — Research → `builds/<slug>/research.md`

Load `references/research.md`. Follow its procedure to dispatch `platform-researcher` and `sota-researcher` in parallel (single message, two Agent tool calls), merge their outputs into `research.md`, and surface a short findings summary.

**Scratchpad artifact:** `builds/<slug>/research.md`
**Review policy:** Tier 2 — pause with the default question. Advance if the user says "proceed" or gives no corrections.

### Phase 3 — Plan → `builds/<slug>/plan.json`

Load `references/plan.md`. Follow its procedure to dispatch the `planner` agent, write the returned JSON to `builds/<slug>/plan.json`, validate it against the schema, render the readable summary, and loop until the user approves.

**Scratchpad artifact:** `builds/<slug>/plan.json`
**Review policy:** Tier 2 — pause. Do not invoke the build workflow without an approved, schema-valid plan.

### Phase 4 — Build / Test / Iterate → `builds/<slug>/build-state.json`

Load `references/build-test-iterate.md`. Follow its procedure to ensure a sandbox folder is confirmed, invoke the workflow (see §4 below), interpret the result, write `build-state.json`, and present the default review.

**Scratchpad artifact:** `builds/<slug>/build-state.json`
**Review policy:** Tier 2 after completion (surface results); Tier 3 hard gate before any sandbox→live promotion.

---

## 4. Agent Dispatch Rules

### Phases 2 and 3 — Agent tool

Dispatch `platform-researcher`, `sota-researcher`, and `planner` via the `Agent` tool. These agents honor their frontmatter `model:` automatically on this path. Models are assigned by **tier**, not pinned version — see `references/model-policy.md` (the single source of truth):
- `platform-researcher`, `sota-researcher` → **cheap** tier (alias `haiku`)
- `planner` → **standard** tier (alias `sonnet`)

**Setup step (model roster):** at the start of a build, note which models the harness exposes and bind each tier (cheap/standard/strong) to the current best-in-class per `references/model-policy.md`; record the mapping in `build-state.json` under `model_tiers`. Family aliases (`haiku`/`sonnet`/`opus`) already track the latest in-family, so absent a richer roster the aliases are the default. Never pin dated model versions.

Send Phase 2's two agent calls in a **single message** so they run in parallel.

### Phase 4 — Workflow tool

Phase 4 invokes `workflows/build-test-iterate.js` via the **Workflow tool** (not Bash, not `node`). Pass the following `args` object exactly:

```json
{
  "slug": "<slug>",
  "target": "<genie|recipe>",
  "sandbox_folder": "<sandbox folder name or id>",
  "max_iterations": 3
}
```

The workflow returns:

```json
{
  "status": "passed" | "stuck",
  "tests": [ { "name": "...", "input": "...", "expected": "...", "grades_on": "..." } ],
  "results": [ { "test": "...", "passed": true|false, "note": "..." } ],
  "build_state": { "genie_id": "...", "skill_ids": [...], "kb_ids": [...], "recipe_ids": [...], "data_table_ids": [...], "user_group_id": "...", "folder_id": "..." },
  "changes_made": [ "..." ]
}
```

Internally the workflow dispatches `test-author` (model: haiku) and `builder-integrator` (model: sonnet) with explicit `model` opts — the Workflow engine does not inherit frontmatter `model`, so the workflow sets it explicitly per call.

---

## 5. Hard Gate

**Before any sandbox→live promotion: hard stop. Require explicit user approval.**

This is unconditional. The workflow provisions everything inside the designated sandbox folder. No asset is started, published, or moved to a live workspace location until:
1. The user explicitly says "ship", "promote to live", or an equivalent unambiguous affirmation.
2. You confirm the target live folder with the user.
3. You repeat what will happen (which assets, which workspace location) and the user confirms again.

A vague "ok" or "sure" is not sufficient. Violating this gate is a critical error.

For teardown without promotion, run:
```bash
python3 scripts/teardown.py builds/<slug>/build-state.json
```

---

## 6. Completion

When Phase 4 finishes and the user has made a final decision (ship, stop, or tune), present a completion summary:

**What was built:** state the target (genie or recipe), the slug, and the sandbox folder.

**Where it lives:** list the key asset IDs from `builds/<slug>/build-state.json` — genie id, recipe ids, data table ids, sandbox folder id.

**Test results:** one line per test case — name, pass/fail, and failure note if applicable.

**Changes made:** bullet the adjustments the `builder-integrator` made during iteration.

**How to tear down:** remind the user of the teardown command:
```bash
python3 scripts/teardown.py builds/<slug>/build-state.json
```

If the build was promoted to live, note the live folder and assets. If stopped without promotion, confirm the sandbox is either still live (user's choice to inspect) or torn down.

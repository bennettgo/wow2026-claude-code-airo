# Phase 4 — Build / Test / Iterate

**Objective:** Invoke the `build-test-iterate` workflow to provision, test, and iterate the solution in a sandbox, then present results for user decision.

**Prerequisite:** `builds/<slug>/plan.json` is approved and schema-valid.

---

## Hard Gate

**Never promote sandbox assets to live without explicit user approval.**

This is an unconditional rule. The workflow provisions everything inside a designated sandbox folder. Nothing is started, published, or moved to production until the user explicitly says "ship" and you confirm the promotion step separately. Violating this gate is a critical error.

---

## Procedure

### Step 1 — Ensure a sandbox folder exists

Before invoking the workflow, confirm that a sandbox folder is available. The sandbox is where all provisioned assets live during Phase 4.

- If the user specified a sandbox folder (by name or id) at the start of the session, use it.
- If not, check the platform inventory in `builds/<slug>/research.md` under "Folders" for any existing sandbox/draft folder. Use it if found.
- If none exists, inform the user and ask them to create one in their Workato workspace (or confirm you should create one via `mcp__workato-airo-mcp-server__folder_list` / the Dev API). Record the sandbox folder name/id before proceeding.

### Step 2 — Invoke the workflow

Invoke `workflows/build-test-iterate.js` via the Workflow tool, passing:

```json
{
  "slug": "<slug>",
  "target": "<genie|recipe>",
  "sandbox_folder": "<sandbox folder name or id>",
  "max_iterations": 3
}
```

The workflow runs two phases internally:
1. **Author tests** — dispatches `test-author` (haiku) to generate sample test cases from `requirements.md` and `plan.json`.
2. **Build, test, iterate** — dispatches `builder-integrator` (sonnet) to provision all assets, run tests, grade results, and iterate up to `max_iterations` times.

Both agents run at their explicitly-set tiers — `test-author` at **cheap** (`haiku`), `builder-integrator` at **standard** (`sonnet`) — not their frontmatter defaults, because the Workflow engine requires explicit `model` opts rather than inheriting from frontmatter. Tiers and their current aliases are defined in `references/model-policy.md` (the single source of truth); the aliases track the latest model in each family, and `builder-integrator` may escalate to the **strong** tier when a test fails repeatedly (see that file).

### Step 3 — Interpret the returned result

The workflow returns `{ status, tests, results, build_state, changes_made }`.

**Interpret `status`:**

- `"passed"` — all test cases passed. The sandbox solution is working.
- `"stuck"` — builder exhausted `max_iterations` without all tests passing. Review `results` to understand which tests failed and why.

**Inspect `tests`:** the array of sample test cases the `test-author` generated (each `{ name, input, expected, grades_on }`). These describe *what was tested*. Keep this in hand — you pair each test with its outcome from `results` when presenting the review.

**Inspect `results`:** each entry is `{ test, passed, note }`, where `test` matches a `name` in the `tests` array. This describes *how each test fared*. Surface which tests passed and which failed, with the failure notes.

**Inspect `changes_made`:** a list of adjustments the builder made during iteration. Surface these so the user understands what was tuned.

### Step 4 — Write `build-state.json`

Write (or confirm) `builds/<slug>/build-state.json` with the `build_state` object from the workflow result. This file records all provisioned asset IDs needed for teardown and promotion:

```json
{
  "genie_id": "...",
  "skill_ids": ["..."],
  "kb_ids": ["..."],
  "recipe_ids": ["..."],
  "data_table_ids": ["..."],
  "user_group_id": "...",
  "folder_id": "..."
}
```

(For recipe targets, genie-specific keys are absent or null.)

The `builder-integrator` writes this file itself, but confirm it exists and is non-empty before presenting the review.

### Step 5 — Default review

Present the outcome: pass/stuck status, the generated test cases joined with their results, changes made, and the sandbox folder/asset IDs. Then ask the default review question.

Build the results table by joining the workflow's top-level `tests` array (the cases the `test-author` generated) with `results` (their outcomes), matching on the test name. This shows the user both *what was tested* and *how it fared*:

| Test | Input | Grades on | Outcome | Note |
|------|-------|-----------|---------|------|
| `<tests[i].name>` | `<tests[i].input>` | `<tests[i].grades_on>` | pass / fail (from `results`) | `<results[i].note>` |

Then ask:

> "Tests pass / here's where it's stuck — ship, tune, or stop?"

**Possible user responses:**

| Response | Action |
|----------|--------|
| **"Ship"** or "promote to live" | Proceed to promotion — see Hard Gate below |
| **"Tune"** or gives specific corrections | Apply the correction to `plan.json` or requirements, then re-invoke the workflow (loop back to Step 2) |
| **"Stop"** or "teardown" | Run teardown — see Teardown below |
| **"Stuck, what now?"** | Explain the stuck tests, propose targeted changes to the plan or requirements, and offer to re-run |

---

## Promotion (ship path)

**Only proceed here if the user has explicitly approved shipping.**

Promotion means moving sandbox assets to the live workspace. This step is outside the workflow — it requires separate, explicit instructions to the `builder-integrator` or manual action. Before promoting:

1. Confirm the user understands that provisioned assets will become live in the workspace.
2. Confirm the target folder for promotion (not the sandbox folder).
3. Proceed with promotion only after the user types an unambiguous affirmation (e.g. "yes, ship it", "promote to production").

---

## Teardown

To clean up all sandbox assets provisioned during the build, run:

```bash
python3 scripts/teardown.py builds/<slug>/build-state.json
```

This reads `build-state.json` and deletes assets in reverse-dependency order (genie → skills → KBs → recipes → data tables → user group → folder). To preview the teardown without deleting:

```bash
DRY_RUN=1 python3 scripts/teardown.py builds/<slug>/build-state.json
```

Offer teardown when the user says "stop", when the build is stuck and the user does not want to retry, or when the session ends without promotion.

---

## Notes

- `max_iterations: 3` is the default. For complex solutions or first-time builds, this is usually enough for the `builder-integrator` to self-correct. If the user wants more attempts, increase the value and re-invoke the workflow.
- The workflow file is `workflows/build-test-iterate.js`. It is a Claude Code Workflow — invoked via the Workflow tool, not Bash. Do not attempt to run it with `node`.
- If the workflow itself errors (not the build — the workflow infrastructure), check that the `builds/<slug>/` directory exists and that `plan.json` is valid. Then retry.
- The `builder-integrator` agent writes `builds/<slug>/build-state.json` during provisioning. If the build got stuck after partial provisioning, the file will contain partial IDs. Teardown still works — it skips null/absent IDs gracefully.

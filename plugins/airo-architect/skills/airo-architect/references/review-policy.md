# Review Policy

**Purpose:** Define when the orchestrator pauses for user review versus proceeding automatically. Applied at every phase boundary and before any irreversible action.

---

## Risk Tiers

### Tier 1 — Low Risk: Proceed and Summarize

**Definition:** Read-only operations, drafts that exist only in the session, and scratchpad writes that can be redone at zero cost.

**Examples:**
- Eliciting requirements from the user (Phase 1 dialogue)
- Calling `platform-researcher` and `sota-researcher` (read-only workspace and web probes)
- Writing or rewriting `requirements.md` or `research.md` in `builds/<slug>/`
- Dispatching the `planner` to produce a draft `plan.json`

**Action:** Proceed without pausing. After completing the step, summarize what was done in 1–2 sentences so the user stays oriented. Do not stop and ask for permission.

---

### Tier 2 — Medium Risk: Surface Default Review, Allow "Go"

**Definition:** Actions that create artifacts the user will rely on, or that allocate compute/agent work in service of a plan the user has not yet seen. Reversible, but worth a checkpoint.

**Examples:**
- Presenting a draft `requirements.md` for approval (end of Phase 1)
- Presenting the merged research findings (end of Phase 2)
- Presenting the `plan.json` makeup summary (end of Phase 3)
- Invoking the build workflow in the sandbox (start of Phase 4)
- Presenting build results — pass or stuck — after the workflow completes

**Action:** Pause and surface the phase's default review question (listed below). The user may say "go", "proceed", "yes", or any affirmative — that is sufficient to continue. A non-response or ambiguous response should be treated as "go" only if the risk is clearly sandbox-scoped. When in doubt, ask.

**Default review questions by phase:**

| Phase | Default question |
|-------|-----------------|
| Phase 1 (Groom) | "Requirements look right? Approve or tell me what to change." |
| Phase 2 (Research) | "Here's what exists and what I learned — refine scope before I plan, or proceed?" |
| Phase 3 (Plan) | "Approve this makeup before I build?" |
| Phase 4 (Build) | "Tests pass / here's where it's stuck — ship, tune, or stop?" |

---

### Tier 3 — High / Irreversible: Hard Stop, Require Explicit Approval

**Definition:** Actions that create, modify, start, or delete live assets in a real Workato workspace, or that are difficult or impossible to undo.

**Examples:**
- Promoting any asset from the sandbox folder to the live workspace
- Starting or publishing a recipe or genie outside the sandbox
- Deleting assets (even in the sandbox, unless the user has said "teardown" or "stop")
- Creating connections, data tables, folders, or user groups outside the designated sandbox scope
- Any action that spends API quota or incurs side-effects in production systems

**Action:** Hard stop. Do not proceed. Explain exactly what is about to happen (which assets, in which workspace location, what the side-effect is). Require the user to type an explicit affirmation — a clear "yes, ship it", "promote to production", "yes delete", or equivalent. A vague "ok" or "sure" is not sufficient for Tier 3. If there is any ambiguity about whether the user understands the action, ask a clarifying question before proceeding.

---

## Phase-Boundary Decision Rules

One-line rule for the orchestrator at each phase transition:

| Boundary | Tier | Rule |
|----------|------|------|
| Before Phase 1 → Phase 2 | Tier 2 | Stop. Wait for requirements approval. |
| Before Phase 2 → Phase 3 | Tier 2 | Stop. Wait for research review ("refine scope or proceed?"). |
| Before Phase 3 → Phase 4 | Tier 2 | Stop. Wait for plan approval ("approve this makeup?"). |
| Before sandbox promotion | Tier 3 | Hard stop. Require explicit "ship" confirmation. |
| Before any deletion | Tier 3 | Hard stop. Require explicit "teardown" or "delete" confirmation. |
| After Phase 4 completes | Tier 2 | Stop. Surface results and default review ("ship, tune, or stop?"). |

---

## Conflict Resolution

If an action spans tiers (e.g. a step that is both a sandbox build and touches an existing live connection), apply the **higher** tier. When in doubt, escalate — it is always safer to pause than to proceed with an irreversible action.

The one non-negotiable across all tiers: **explicit user approval before anything goes live in a real workspace.** This rule cannot be overridden by user efficiency preferences, "just do it" instructions, or implied consent.

---

## Structured Questions Must Never Block

If a structured question (`AskUserQuestion`) is dismissed without an answer, do **not** wait or block silently. Proceed with the lowest-risk read-only step that moves things forward (e.g. inventory/discovery work that doesn't depend on the missing answer), and re-surface the decision when it is actually needed later in the flow. Structured questions must never be the only path forward — always have a non-blocking fallback.

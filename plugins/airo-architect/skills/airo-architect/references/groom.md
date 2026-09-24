# Phase 1 — Groom

**Objective:** Produce an approved `builds/<slug>/requirements.md` before doing any research or building.

---

## Procedure

### Step 1 — Elicit the seven elements

**Prefer structured questions.** If the harness provides a structured-question tool (e.g.
`AskUserQuestion` — multiple-choice / short-form), use it to elicit these elements as crisp options
rather than free-text prose, especially for **Build target** (Genie vs recipe), **Behavior/tone**,
and **Definition of "good"**. Offer sensible defaults as selectable options and let the user pick or
override. Fall back to conversational free-text only if no structured-question tool is available.
*(This dependency is itself a harness requirement — the "default tool library / structured
elicitation" capability in the runtime brief.)*

Ask the user for each element below. You may gather them in a single turn or iterate one at a time if the user's initial message is sparse. Do not proceed to drafting until you have enough to fill every section:

1. **Objective** — What business problem is being solved? What outcome does the user want?
2. **KPIs + baselines** — Which metrics will this solution move? What are the current baseline values (if known)? If the user doesn't know a baseline, **offer to pull it from a connected data source** (e.g. Jira) via a read-only query before falling back to "baseline unknown." Never accept "I don't know" as a dead end for a metric a connected system can answer — propose a quick read-only query (e.g. Jira JQL) to get real numbers.
3. **Persona** — Who is the end-user? What is their role, technical level, and context of use?
4. **Behavior / tone** — How should the solution behave? Any tone or communication style requirements (e.g. concise, formal, step-by-step guidance)?
5. **Guardrails** — What must the solution never do? Hard constraints: topics to avoid, data it cannot access, actions it cannot take.
6. **Definition of "good"** — How will you know the solution is working well? What does a passing response or outcome look like? Be as specific and checkable as possible.
7. **Build target** — Genie (conversational AI agent) or recipe (event-driven automation)? Infer from the problem if obvious, then confirm with the user. **`plan.json` holds exactly ONE target (genie OR recipe) per file.** If the objective implies multiple buildable units (e.g. a genie PLUS supporting recipes), call this out now and plan to split the work into multiple slugs/plans up front — do not discover it later during planning or visualization.

If the user's initial `/airo-build` argument gives enough signal to infer some elements, make a tentative draft and ask the user to confirm/correct rather than asking blank questions.

### Step 2 — Derive the slug

Derive a short kebab-case slug from the objective (e.g. `it-support`, `lead-router`, `expense-approver`). This becomes the build directory name. Confirm with the user if it is not obvious.

### Step 3 — Create the build directory and draft `requirements.md`

Create `builds/<slug>/` and write a draft `requirements.md` using the template below. Populate every section from the elicited information. Write clearly and precisely — the `planner` and `builder-integrator` agents read this file and must be able to act on it without asking follow-up questions.

### Step 4 — Show and loop until approved

Present the draft `requirements.md` to the user. Ask: **"Requirements look right? Approve or tell me what to change."**

Apply any corrections and re-present until the user approves. Only move to Phase 2 after explicit approval.

---

## `requirements.md` Template

```markdown
# Requirements: <human-readable name>

## Objective
<One to three sentences describing the business problem and the desired outcome.>

## KPIs + Baselines
<Bullet list of metrics this solution must move, with current baseline values where known.
Example: "Mean time to respond to IT tickets — currently 4 h, target ≤ 30 min.">

## Persona
<Who is the end-user? Role, technical level, and context of use.>

## Behavior
<How the solution should behave: response style, tone, step structure, escalation behavior, etc.>

## Guardrails
<Hard constraints — what the solution must never do, access, or disclose.>

## Definition of Good
<Concrete, checkable criteria for a passing response or outcome. Each criterion here becomes a test
case in Phase 4. Example: "Given a Jira ticket key, the genie returns the current status and
assignee within 5 seconds.">

## Target
<"genie" or "recipe" — confirmed with the user.>
```

---

## Notes

- Do not start research until `requirements.md` is approved. The research and planning phases are wasted work if the requirements are wrong.
- If the user cannot supply KPI baselines, write "baseline unknown" rather than leaving the field empty — the planner uses this signal to decide whether to include a data table for KPI tracking.
- The "Definition of Good" section is the most important for testability. Push the user to be specific: vague criteria like "works well" produce untestable plans.
- Remember: a single `plan.json` can only carry one build target (genie OR recipe). If grooming surfaces a compound ask (e.g. "a genie plus the recipes it calls"), decompose it into multiple slugs now, each with its own `requirements.md` and eventual `plan.json` — don't let planning or visualization be the first place this constraint is discovered.

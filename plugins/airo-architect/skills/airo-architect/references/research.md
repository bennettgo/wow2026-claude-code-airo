# Phase 2 — Research

**Objective:** Inventory the live Workato workspace and gather external patterns, then merge results into an approved `builds/<slug>/research.md` before planning.

**Prerequisite:** `builds/<slug>/requirements.md` is approved.

---

## Procedure

### Step 1 — Dispatch both researchers in parallel

Send a single message containing two Agent tool calls — one for `platform-researcher` and one for `sota-researcher`. Because they are independent, they run concurrently and both honor their frontmatter `model: haiku`.

**Agent call 1 — `platform-researcher`:**

```
Prompt: "Inventory the Workato workspace and all reachable enterprise MCP knowledge
stores for a build with this objective: <paste the Objective section from requirements.md>.
Return the full JSON per your output contract."

agentType: "platform-researcher"
```

**Agent call 2 — `sota-researcher`:**

```
Prompt: "Research external best practices and patterns for this problem domain: <paste the
Objective section from requirements.md>. Return the full JSON per your output contract."

agentType: "sota-researcher"
```

Do not dispatch them sequentially — both calls must be in the same message so they run in parallel.

### Step 2 — Parse and validate the responses

Each agent returns a JSON object. Parse both responses:

- `platform-researcher` returns `{ workspace: {...}, reachable_knowledge: [...] }`.
- `sota-researcher` returns `{ patterns: [...], recommended_shape: "...", pitfalls: [...] }`.

If either agent returns a parse error or an empty result, note the failure and proceed with what is available. Do not block on a partial failure.

### Step 3 — Merge into `builds/<slug>/research.md`

Write `builds/<slug>/research.md` with the three sections below. Populate each section from the parsed JSON — convert arrays to readable bullet lists. Keep it concise; the planner reads this file.

```markdown
# Research: <slug>

## Platform Inventory

### Connections
<Bullet list: name, app/connector type, id — from workspace.connections>

### Existing Genies
<Bullet list: name, id, assigned skills, KBs — from workspace.genies; omit if empty>

### Existing Recipes
<Bullet list: name, id, trigger app, action apps — from workspace.recipes; omit if empty>

### Data Tables
<Bullet list: name, id — from workspace.tables; omit if empty>

### Knowledge Bases
<Bullet list: name, id, source types — from workspace.kbs; omit if empty>

### Folders
<Bullet list: name, id, path — note any sandbox/draft folders — from workspace.folders>

### User Groups
<Bullet list: name, id — from workspace.user_groups; omit if empty>

## Connection Reuse Verdict

**Required.** For each app named in the objective, state the verdict plainly — this must be surfaced prominently near the top of the findings, not buried in a gaps list further down:

<For each entry in connection_reuse_verdict, one line:
  • **<app>** — found+authorized / found-but-unauthorized / none-found — <evidence>>

If `platform-researcher` did not return a verdict for an app named in the objective, treat that as a gap and call it out explicitly rather than silently omitting the section.

## Reachable Knowledge

<For each entry in reachable_knowledge, one bullet:
  • <server> — <store> — <data_shape_summary>>

If none, write: "No enterprise MCP servers detected.">

## External Patterns

### Recommended Shape
<recommended_shape paragraph from sota-researcher>

### Patterns
<Bullet list: "**<name>** — <when_to_use>" for each pattern>

### Pitfalls
<Bullet list of pitfalls>
```

### Step 4 — Surface findings and default review

Present a short summary (3–5 bullets) of the most relevant findings: **lead with the connection reuse verdict** for every app named in the objective (found+authorized / found-but-unauthorized / none-found), then which existing connections/KBs the plan can reuse, which enterprise knowledge stores are available, and the recommended solution shape. Do not bury the verdict in a gaps list — it directly affects whether the plan needs a new connection created before build.

Then ask the default review question:

> "Here's what exists and what I learned — refine scope before I plan, or proceed?"

If the user says proceed (or gives no corrections), move to Phase 3. If the user refines scope, apply the changes to `requirements.md` and note the delta in `research.md`, then proceed.

---

## Notes

- The parallel dispatch is critical for speed. Do not serialize the two agent calls.
- `platform-researcher` runs on `haiku` (cheap, fast) via the `Agent` tool path, which honors the agent's frontmatter `model`. The same applies to `sota-researcher`. Phase 4's workflow sets model explicitly — here, rely on frontmatter.
- The `research.md` file is the planner's only view of what exists. Incomplete or vague research leads to plans that invent connections or miss reusable assets. If the platform-researcher returned errors for some categories, note them explicitly in `research.md` so the planner can flag uncertainty.
- Do not synthesize or editorialize the raw agent output beyond formatting it into the three sections. The planner draws its own conclusions.

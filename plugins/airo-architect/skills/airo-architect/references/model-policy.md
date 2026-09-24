# Model policy — tiered and non-static

Single source of truth for **which model each sub-agent runs on**. The goal: assign by *role tier*,
not by a pinned model version, so the plugin automatically tracks the best model available **today**
without code edits.

## Principle: tiers, not versions

Agents are assigned a **tier** (a role class), and each tier resolves to the current-best model in
that class at run time. Never hardcode a dated model id (e.g. a `-20xx-xx-xx` version). Use **family
aliases** that already track the latest release in their family, or resolve dynamically (below).

| Tier | Use for | Resolves to (today's alias) | Agents |
|---|---|---|---|
| **cheap** | High-volume, low-judgment work: read-only discovery, external research, generating candidates/tests | `haiku` | `platform-researcher`, `sota-researcher`, `test-author` |
| **standard** | Judgment + synthesis: turning inputs into a plan, building + iterating | `sonnet` | `planner`, `builder-integrator` |
| **strong** | Hardest reasoning: adversarial verification, tricky debugging, escalation when `standard` stalls | `opus` | (reserved — see escalation) |
| **orchestrator** | The conversation / phase driver | inherit session model | the `airo-architect` skill itself |

## Resolve to what's available *today* (non-static)

1. **Prefer family aliases** (`haiku` / `sonnet` / `opus` / `fable`). These are not pinned — the
   harness resolves each alias to the latest model in that family, so a new release is picked up
   automatically. This is the default and needs no maintenance.
2. **Discover at run time when possible.** At the start of a build the orchestrator should note the
   model roster the harness actually exposes and bind each tier to the current best-in-class,
   caching the mapping in `builds/<slug>/build-state.json` under `model_tiers`. If a cheaper or
   stronger model has appeared, the mapping updates with zero code changes.
3. **Never pin a dated version** in agent frontmatter, the workflow, or scripts. If you must name a
   specific model, put it *only* here, in this table, so there is one place to change.

## Escalation

`builder-integrator` runs at **standard**. If its build→test→iterate loop fails the same test
`>= 2` times, it should escalate that reasoning step to **strong** for one attempt before returning
`stuck`. (A cheap/standard model looping is worse value than one strong attempt.)

## Where tiers are applied — and the drift risk

The same tier is expressed in **two** places, because the two dispatch paths read model config
differently:

- **`Agent`-tool path (Phases 2–3):** the agent's frontmatter `model:` is honored. Agents currently
  declare `haiku` / `sonnet` per the table above.
- **`Workflow` path (Phase 4):** the Workflow engine does **not** inherit frontmatter `model:` — the
  workflow must pass `model` explicitly per `agent()` call.

**Drift risk:** an agent's tier is therefore duplicated (frontmatter *and* the workflow's `opts`).
This file is the canonical mapping; when a tier's alias changes, update **both** the frontmatter and
`workflows/build-test-iterate.js` from this table. (If the harness later lets the workflow inherit
frontmatter — or accept a tier name — collapse to one place.)

## Why this shape

Cheap models are fine for high-volume, low-judgment work (discovery, research, generating test
candidates); the leverage of a stronger model is on *judgment* (planning) and *the iterate loop*
(building + fixing). Reserving a **strong** tier for verification/escalation matches the pattern of
"generate cheap, verify strong." Tiers keep that intent stable even as specific models come and go.

# Research: drift-investigator

## Platform Inventory

Gathered directly against the PE Copilot **preview** workspace (folder 578470 / project 552603) — the packaged `platform-researcher` agent is wired only to the prod `workato-airo-mcp-server`, which is the wrong workspace for this build, so this was done by hand via `workato-airo-mcp-preview` instead.

### Connections
Not directly enumerable via the available preview tool surface (no generic connection-list tool exposed). Not needed for this build: the Genie's only data access is the two existing MCP-server-backed skills below, not a direct app connection.

### Existing Genies
None in folder 578470 — confirmed via `genie_list`. This is a fresh build, no reuse/collision risk.

### Existing Recipes (folder 578470 — reuse as-is, do not rebuild)
All 8 are already running "function recipe → Skill" tools backing the two stub MCP servers from the WoW 2026 demo setup. These are exactly the data sources the Genie's investigation needs:

- `get_sell_through` (id 1860936) — weekly sell-through % by region
- `get_store_sell_through` (id 1860937) — per-store sell-through trend within a region
- `get_inventory_positions` (id 1860938) — on-hand vs. safety stock, weeks below safety
- `get_purchase_orders` (id 1860939) — PO status, vendor, delivery dates/delays
- `get_backorder_cases` (id 1860940) — backorder case records with reason codes
- `get_product` (id 1860941) — product catalog, substitute SKU lookup
- `get_promotions` (id 1860942) — promotion calendar
- `get_price_history` (id 1860943) — weekly shelf price history

Each of these already has a `skl-*` Skill handle (converted during the 2026-09-15 MCP server migration) — the planner should reference these as existing skills to attach, not new skills to build.

### Data Tables
7 exist workspace-wide, none in folder 578470 — all belong to unrelated projects (Nexus demo assets in folder 579195, ITSM/HR demo assets in folder 578739). None reusable for this build.

### Knowledge Bases
8 exist workspace-wide, none in folder 578470 — all belong to unrelated demos (Sales Ops, ITSM, HR, Nexus policies). None reusable. This build likely needs no KB — the "policy" the Genie applies (bounded 3-candidate order, bounded action set) is procedural logic in the prompt/skill design, not a document corpus to retrieve from.

### Folders
- `578470` — "AIRO + Claude Code" (parent `81012`, project `552603`) — the build/sandbox folder for this session.

### User Groups
Not fetched — no user-group gating is required for this Genie (it's invoked by the Recipe / test harness, not by an end-user chat interface with allow-listed groups, unlike the old stale Genie build).

## Reachable Knowledge

No additional enterprise MCP knowledge stores are relevant here — the Genie's data sources are already the 8 skill-recipes listed above, to be attached directly as skills.

## External Patterns

### Recommended Shape
The investigation agent workflow should follow a deterministic, three-phase shape: (1) **Anomaly Detection** — triggers on a flagged SKU/region sell-through drift and collects baseline metrics; (2) **Fixed-Order Investigation** — systematically rules out pricing, demand, then supply constraints in sequence, scoring confidence for each, generating a structured evidence pack and a single ranked root-cause hypothesis; (3) **Human Approval Gate** — presents the evidence, ranked cause, and bounded action recommendation (from a fixed set: replenishment escalation, substitute promotion, vendor notification, or log-only) and only executes after explicit human approval with full traceability. This keeps investigation deterministic while preserving human judgment at the decision point. This matches our PRD's Flow 1/Flow 2 shape closely — no structural change needed, just confirms the design.

### Patterns
- **Fixed-Order Investigation (Ruled-Out Chain)** — price/promotion first (fastest disproof), then demand shift, then supply constraint. Each step ruling out its cause narrows the space. *(Matches our bounded 3-candidate order exactly.)*
- **Confidence Scoring with Probabilistic Ranking** — assign HIGH/MEDIUM/LOW confidence per candidate based on evidence strength; routes low-confidence findings to explicit human review.
- **Evidence Binding Before Approval Gate** — bind exactly: what's being decided, supporting evidence, target/parameters, expected effect, and what happens if declined — before any tool call with side effects executes. Propose-then-commit, never commit-then-explain.
- **Anomaly Detection via POS/Demand Sensing** — trigger on statistical deviation (demand drop without promotion, sell-through variance vs. baseline).
- **Stock-Out Precedes Demand Drop** — if inventory falls below safety stock 1–2 weeks *before* the demand decline, that's the causal direction: supply constraint is the root cause, demand drop is the effect. *(Exactly our seeded BRH-2240 pattern: stock-out 2026-08-03, sales drop starts 2026-08-17.)*
- **Substitution as Bounded Corrective Action** — when supply is constrained and replenishment is delayed, recommending a preferred, in-stock substitute is a low-risk bounded action that avoids escalation loops.

### Pitfalls
- Treating symptoms as root causes — diagnosing demand loss without checking inventory first. Confusing correlation with causation leads to wrong corrective actions.
- Late approval gates that execute before human review completes — must gate before the *first* side-effecting tool call, not after.
- Phantom inventory / data drift producing "evidence" that contradicts reality — not a concern here since our data sources are deterministic seeded stubs, but worth naming as a real-world risk this design guards against structurally.
- Reviewer fatigue from poor evidence packing — keep the report to one page, one clear recommendation, not a data dump. *(Matches our F3 "no appendices" requirement.)*
- Ignoring interconnection between pricing, demand, and supply — score and differentiate rather than treating candidates as fully independent.

Sources:
- [Human-in-the-Loop Approval Gates in Incident Response | Elastic](https://www.elastic.co/observability-labs/blog/incident-response-automation-human-approval-gate)
- [Human-in-the-Loop AI Agents: Approval Workflows for Safe Automation | StackAI](https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation)
- [Supply Chain Root Cause Analysis: 4 Critical Steps | GAINS](https://gainsystems.com/blog/4-ways-root-cause-analysis-can-stop-recurring-supply-chain-problems/)
- [Phantom Inventory: Causes, Detection, and How to Fix It | RELEX Solutions](https://www.relexsolutions.com/resources/phantom-inventory/)
- [Demand Sensing: AI Forecasting Use Case | Impact Analytics](https://www.impactanalytics.ai/blog/ai-demand-sensing-retail-implementation)
- [Out of Stock Detection: Reduce Stockouts and Lost Sales | FieldPie](https://www.fieldpie.com/blog/out-of-stock-detection/)

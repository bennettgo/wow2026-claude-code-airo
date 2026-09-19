# Requirements: Drift Investigator (Genie)

## Objective
Given a flagged SKU/region sell-through drift, investigate three bounded candidate causes — pricing/promotion, demand shift, supply/stock-out — in that fixed order, produce a one-page report with evidence, confidence, and a recommended action, and (on a human decision) execute the chosen downstream action. Source: PRD Flow 1 + Flow 2 (`wow2026-sell-through-drift-prd.md`).

## KPIs + Baselines
- Report read-to-decision time: target under 5 min median — baseline unknown (today: manual, ~half a day of analyst time per SKU).
- Mean time from drift onset to corrective action: target under 1 week — baseline ~5 weeks (the BRH-2240/Texas seed case: stock-out 2026-08-03, sales drop 2026-08-17, PO slip to 2026-09-18).
- Reject/modify rate on the human gate: target 10–40% (a gate always approved is decoration; always rejected means the recommendation logic is wrong).

## Persona
- **Regional Inventory Manager** — decision-maker on the human gate (approve/reject/modify); reads the one-page report, needs it scannable in under two minutes.
- **Replenishment Planner (Procurement Liaison)** — consumes vendor-delay evidence (PO numbers, slip durations) attached to escalation actions.
- Invoked programmatically by the `Sell-Through Drift Monitor` Recipe (not chatted with directly by end users in normal operation); for this build/test cycle, invoked via the Genie's conversation/skill interface directly to verify behavior standalone before the Recipe integration.

## Behavior
- Checks candidates in fixed order: (1) pricing/promotion — promotion windows + price history via `crm-promotions-mcp`; (2) demand shift — regional sell-through shape vs. other regions, store-level uniformity via `sales-inventory-mcp`; (3) supply/stock-out — inventory positions, backorder cases, PO delays via `sales-inventory-mcp`.
- Output is a one-page report: drift condition (metric, window, magnitude), evidence per candidate, confidence, recommended action — no appendices. Cites underlying records by ID (store IDs, PO numbers, backorder case refs, substitute SKU).
- A pair matching none of the three candidates is classified "unclassified — out of scope," with no recommendation.
- On a human decision (approve/reject/modify), executes exactly one downstream action from the bounded set, or logs-only on reject.
- Tone: concise, evidence-first, confidence-scored. No speculation beyond the two data sources.

## Guardrails
- Never executes any downstream action without an explicit prior human decision on the report.
- Never expands past the three bounded candidate causes — a non-matching case is "unclassified," never force-fit.
- Only reads from `sales-inventory-mcp` and `crm-promotions-mcp` — no other data sources.
- Downstream action set is bounded to exactly: `create_replenishment_escalation`, `propose_substitute_promotion`, `notify_vendor`, `log_only` (reject path). No other action types, ever.
- Investigation reads are read-only; writes occur only in the bounded action set, and only after approval/modify.
- No PII — all records are store/SKU/vendor-level.
- Every executed action must be traceable back to the specific report and decision that authorized it.

## Definition of Good
Each of these is a test case in Phase 4 — grounded in the seeded storyline already live on `sales-inventory-mcp` / `crm-promotions-mcp` (SKU `BRH-2240`, Texas):

1. **Vendor-delay case (BRH-2240 / Texas):** investigation lands on supply/stock-out; report cites the 8 affected stores, both delayed Branchwood POs (PO-78412, PO-78455), the `VENDOR_DELIVERY_DELAY` reason, and recommends substitute IDH-3310 (in stock in all 8 stores) as a `propose_substitute_promotion` action, with pricing/promotion and demand explicitly cleared first.
2. **Demand-surge case (synthetic — promotion active, sell-through up):** investigation lands on demand shift, explicitly clears pricing/promotion and supply/stock-out.
3. **Inventory-mismatch case (synthetic — low stock, POs on time):** investigation lands on supply with a mismatch noted (stock-out without a corresponding vendor delay), or returns "unclassified" if it doesn't cleanly fit.
4. **Clean/healthy case (synthetic — no stores below safety, flat sell-through):** reports no drift, produces no recommendation.
5. **Human gate — approve:** given a report + "approve," executes the recommended action (for the BRH-2240 case: `create_replenishment_escalation` + `propose_substitute_promotion` referencing IDH-3310), traceable to the report/decision.
6. **Human gate — reject:** given a report + "reject" with a reason, executes nothing; logs the rejection reason.
7. **Human gate — modify:** given a report + a modified action, executes the modified action, not the original recommendation.

## Target
genie

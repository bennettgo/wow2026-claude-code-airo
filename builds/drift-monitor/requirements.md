# Requirements: Sell-Through Drift Monitor (Recipe)

## Objective
A scheduled Recipe that sweeps sell-through data weekly, flags SKU/region pairs matching a drift condition, hands each flagged pair to the `Drift Investigator` Genie for investigation, sends the resulting report to a human decision gate, and on decision, resumes into the correct branch (execute / log-only / execute-modified). This is the durable backbone with the human-in-the-loop pause/resume step. Source: PRD Flow 0 + Flow 2, F1 + F4 (`wow2026-sell-through-drift-prd.md`).

## KPIs + Baselines
- 100% of flagged drifts receive a human decision within one business day — baseline unknown (today: no detection exists, drift found by chance).
- Mean time from drift onset to corrective action: target under 1 week — baseline ~5 weeks (BRH-2240/Texas case).
- Detection sweep completes within one weekly cycle; per-pair investigation (Genie call) completes in under 5 minutes.

## Persona
- **Store Operations Analyst** — today spots anomalies by eyeballing regional dashboards and spends hours pulling data by hand; with this Recipe, drift is detected automatically and handed off with evidence already attached.
- **Regional Inventory Manager** — the human-gate decision-maker; receives the report and responds approve/reject/modify.

## Behavior
- Runs on a weekly schedule against sell-through data from `sales-inventory-mcp`.
- Flags a SKU/region pair when: at least one store in the region has been at/below safety stock for 3+ consecutive weeks **AND** regional sell-through declined 15%+ over the trailing 6 weeks. Both thresholds are configuration values, not hardcoded logic.
- Each flagged pair (SKU, region, flagging evidence) is passed to the `Drift Investigator` Genie for investigation (Flow 1).
- The Recipe pauses on a wait step until the Regional Inventory Manager submits a decision on the resulting report.
- On approve or modify: resumes and calls the Genie again to execute the (possibly modified) action from the bounded set.
- On reject: logs the report with the rejection reason; no downstream action executes.
- Every decision is recorded with timestamp, decider, branch, and free-text reason — this log is the audit trail.

## Guardrails
- No downstream action ever executes before a human decision is recorded for that report.
- Threshold values (weeks below safety, decline %) must be changeable via configuration without editing Recipe logic/code.
- Only reads sell-through/inventory data from `sales-inventory-mcp` — investigation itself is delegated entirely to the Genie, not duplicated in the Recipe.
- Decisions must be attributable to a named user — no anonymous or API-only approvals.

## Definition of Good
Each of these is a test case in Phase 4, grounded in the seeded storyline already live on `sales-inventory-mcp`:

1. **Detects the seed pattern:** a SKU/region matching the BRH-2240/Texas pattern (8 stores at/below safety stock for 5 weeks, Texas sell-through −39.7% over 6 weeks) is flagged.
2. **Ignores healthy SKUs:** a SKU/region with no stores below safety stock and flat sell-through is not flagged.
3. **Configurable thresholds:** changing the decline-percentage threshold in configuration changes which pairs are flagged, with no code change required.
4. **No action before decision:** for a flagged pair with a pending report, no downstream action fires until a decision is submitted.
5. **Reject branch:** submitting "reject" with a reason produces no downstream action and a complete log entry including the reason.
6. **Modify branch:** submitting a modified action executes that modified action, not the Genie's original recommendation.
7. **Approve branch (BRH-2240/Texas, end-to-end):** flags the drift → Genie report cites 8 stores, both delayed Branchwood POs, IDH-3310 substitute → approve → replenishment escalation + substitute-promotion proposal execute, traceable to the report and decision.

## Target
recipe

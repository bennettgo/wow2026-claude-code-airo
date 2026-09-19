# WoW 2026 — Claude Code + AIRO: From Vibe Coding to Production, Live

Asset index for this session. The two Google Docs are the editable sources of truth — this folder doesn't fork copies of them, it points to them.

## Session guardrails (local)
[CLAUDE.md](./CLAUDE.md) ([AGENTS.md](./AGENTS.md) points here)

Read-first file for any Claude/agent session working in this folder: runbook precedence, stub MCP server handles and gateways, the seeded ground-truth invariants (Texas −39.7%, 12 stores, PO-78412/78455, IDH-3310 substitute), PRD format rules, and working agreements. Keeps any session consistent with the runbook without re-deriving context.

## Session outline (Google Doc)
[WoW2026: Claude Code + AIRO: From Vibe Coding to Production, Live](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc)

Pre-existing doc, updated in this session with the full retimed flow, cast, scenario data, and anticipated questions.

## MCP Server & Build Agent Design Spec (Google Doc)
[WoW 2026 — MCP Server & Build Agent Design Spec](https://docs.google.com/document/d/1fyi7zH0w0PEdpnKbrUc1WzZMSa7orIjahBy4_whB1Pw)

Handoff spec for the `sales-inventory-mcp` and `crm-promotions-mcp` servers and the four seed scenarios. Servers are now provisioned (see below); scenarios B/C SKU picks remain open.

## Runbook (local) — source of truth
[wow2026-sell-through-drift-runbook.md](./wow2026-sell-through-drift-runbook.md)

Restructured 2026-09-18 around progressive disclosure. The session now runs the same four moves twice: build, test, inspect, use. Round one does it on a single skill (~10 min) so the room watches an MCP server get made and reads a job log at minute 8 instead of minute 30. Round two runs the original investigate → PRD → build → verify → ship arc, compressed, because the vocabulary is already taught.

Two environment decisions were recorded there on 2026-09-18: the demo runs on the **PE Copilot preview** workspace (only place `test_recipe` exists), against **real connectors** rather than canned payloads. Both carry pre-work; see the runbook's Pre-work and Open items sections.

## PRD (local, produced by the Stage 4 beat)
[wow2026-sell-through-drift-prd.md](./wow2026-sell-through-drift-prd.md)
The document Claude writes on the spot at the end of the investigation — now in canonical Workato PRD format (per the writing-workato-prds skill): Executive Summary, Product Vision, Target Users, Problem Statement, Solution Overview with a mermaid architecture diagram (Recipe → Genie → human gate → bounded actions), F1–F5 feature requirements, closing sections, Customer Evidence appendix. Rehearsed and written 2026-09-10 against the live stub MCP servers.

## Environment map (verified 2026-09-18)

Three Workato MCP endpoints are reachable from a Claude session here, and they do **not** all point at the same workspace. This caused real confusion; check it before assuming an asset is missing.

| MCP server | Deployment | Workspace | Demo assets there? |
|---|---|---|---|
| `workato-airo-mcp-preview` | preview.workato.com | PE Copilot preview | Yes — folder `578470` |
| `workato-airo-mcp-server` | app.workato.com | IDEA Supplier Management (root `31158076`) | No |
| `workato-dev-api` | app.workato.com | IDEA Supplier Management (same) | No |

Consequences worth knowing:

- **`test_recipe` / `test_recipe_input_schema` are preview-only.** The production AIRO MCP can run saved test cases but cannot test a skill ad hoc with a trigger event. This is why the demo is on preview.
- **There is no preview Dev API MCP wired up.** The Dev API MCP above is production. Top pre-work blocker in the runbook.
- **`get_recipe_test_status` lies.** It reported `NO_TEST_RUN` on recipe 1860936 while the test job had already run and succeeded. Use `recipe.job.list` instead. `recipe.job.list` also prints `handle=<unavailable>`, but its `internal_id` works as `recipe.job.get --job-id`.

Preview's authorized connections are thin: Salesforce `SFDC - DEV` (105904), Slack `Ideal Lifestyle` (105903), a REST connection (108365), and a genie-Slack connection (106892). Microsoft Teams and Datadog connections exist but were never authorized. Production IDEA Supplier Management, by contrast, has NetSuite, SAP, MSSQL "IDEAONE Supplier Database", Jira, Gmail, Coupa, HubSpot, Workday and more — but its Snowflake and "Idea Salesforce" connections are both broken, which is why its `handle_supply_disruption` skill has been failing since June.

Skills can read **Workato Data Tables** directly, which is the documented fallback if Salesforce seeding slips. Proven pattern, copied from the ITSM Support Genie skills on preview:

```
workato_skill.start_workflow(parameters_schema)
  → workato_db_table.get_records(table_id, filters=[{field_id, op, value}])
  → workato_skill.workflow_return_result(result={...})
```

## Stub MCP servers (rebuilt 2026-09-15 in folder "AIRO + Claude Code")

The two Investigate-beat data MCPs are live as `project_assets` MCP servers on the PE Copilot preview workspace (folder "AIRO + Claude Code", folder_id `578470`, project_id `552603`), backed by Workato recipes serving deterministic seed data — no live systems.

**These 8 skills currently return hardcoded JSON.** Per the 2026-09-18 runbook decision they are to be rebuilt against the preview Salesforce connection so the demo shows live data. The storyline does not exist in that org yet; seeding it is the largest pre-work item.

| Server | Handle | Tools | Gateway |
|---|---|---|---|
| `sales-inventory-mcp` | `mcps-AbbwNosG-gbT-B6` | get_sell_through, get_store_sell_through, get_inventory_positions, get_purchase_orders, get_backorder_cases, get_product | `https://12572.apim.mcp.preview.workato.com` |
| `crm-promotions-mcp` | `mcps-AbbwQx3k-zX4-B6` | get_promotions, get_price_history | `https://12575.apim.mcp.preview.workato.com` |

- [`.mcp.json`](./.mcp.json) registers both for Claude Code (HTTP transport, Bearer tokens) — committed project config. [`.claude/settings.json`](./.claude/settings.json) auto-approves them (`enabledMcpjsonServers`) so `claude` launches here don't prompt.
- Verified end-to-end 2026-09-15: `tools/call` passes on all 8 tools with the seeded storyline invariants intact (Texas −39.7%, 12 driver stores, 8 below safety since 2026-08-03, 2 delayed Branchwood POs, 8 VENDOR_DELIVERY_DELAY cases, TX promos clean, flat price, IDH-3310 substitute "in stock in all **8** affected stores" — a "12" typo in the seed data was caught and fixed here).
- Each tool is a Workato recipe using the `workato_skill` trigger, converted to a **Skill** (`skl-*` handle) before being attached to its MCP server as a `workato_skill` tool — a plain recipe ID (`workato_recipe_function`) is not sufficient for this trigger type.
- **Supersedes** the original folder "WoW 2026 - Sell-Through Drift Demo" (folder_id `578568`, project_id `552655`, handles `mcps-AbYAaQKc-saC-B6` / `mcps-AbYAaQhm-GMd-B6`), which became unreachable from the working Claude session's AIRO credentials (a collaborator/grant gap on that project, not a data problem — it was still live under the "IDEA Lifestyle CS" account). Treat the old folder as stale.

## Genie — needs rebuilding against the new folder

**WoW 2026 - Drift Investigator** (handle `gin-Aba3g4Fk-wY9n4W-B6`, built 2026-09-11) is wired to the 8 skills in the **old** folder (578568), not the new one (578470). It has not been rebuilt yet. Until it is, treat its headless config below as stale/reference-only:

- `HEADLESS_BASE=https://genie-api.preview.workato.com`
- Client: `gincl-Aba3gbxb-WkXFA6-B6` ("wow2026-monitor-recipe"), API key regenerated 2026-09-12 — full value in the runbook.
- `X-IDP-User-Id: 47fdThLz5SDpxukG9xtAwh` (Bennett's IdP user id on preview — active, member of `Everyone` + `Bennett Headless App Users`).
- **Gotcha:** `pe-copilot-test@workato.com` is `invited`/never-signed-in on preview → headless returns `401 user_nonactive_or_missing`. Any X-IDP-User-Id used live must be an *active* user in one of the genie's allow-listed groups.

**Next step:** rebuild the Genie in folder 578470 against the 8 new Skill handles (see "Stub MCP servers" above), then re-verify the headless flow (list conversations → create conversation → send message → `processing.finished`).

## Rebuild kit: stub MCP servers in a fresh workspace

Used 2026-09-15 to move the demo off the original PE Copilot preview folder. Kept here since the same kit would be needed for any future move.

- [`mcp-servers/recipe-codes/`](./mcp-servers/recipe-codes/) — 8 recipe code files (one per tool), each a Workato function recipe (`start_workflow` trigger + `workflow.return_result` static payload) with the seeded storyline baked in. `get_product.code.json` carries the "8 affected stores" fix.
- [`scripts/migrate_mcp_stubs.py`](./scripts/migrate_mcp_stubs.py) — creates the 8 recipes and starts them. Two things it does **not** do (found and worked around during the 2026-09-15 migration, not yet folded back into the script): (1) each recipe needs an explicit `"config": "[]"` field on creation or it's stuck unstartable ("missing adapter configuration: workato_skill"); (2) after creating, each recipe must be converted to a Skill (`recipe_builder_convert_to_skill`) and attached to the MCP server as `{"trigger_application": "workato_skill", "id": "<skl-handle>"}` — attaching by raw recipe ID fails MCP-server creation ("invalid asset"). Token minting is `POST /mcp/mcp_servers/{handle}/tokens`, which returns `plain_token` directly in a flat response — no separate renew call.
- Run: `WK_TOKEN=<workspace-api-token> WK_FOLDER=<target-folder-id> python3 scripts/migrate_mcp_stubs.py`, then finish the two steps above manually (or fold them into the script before the next run).

## Open items

**Open items live in the runbook**, under "Open items / risks" and "Pre-work". Don't fork them here. As of 2026-09-18 the blockers are a preview Dev API MCP, seeding Salesforce with the BRH-2240 storyline, rebuilding the 8 skills against it, and rebuilding the Genie.

One item belongs only to the design spec, not the runbook: scenarios B (demand surge) and C (inventory/count mismatch) still need a SKU and region picked.

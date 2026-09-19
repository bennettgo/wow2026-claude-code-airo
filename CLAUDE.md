# WoW 2026 Demo — Session Guardrails

You are working in the asset folder for **"WoW 2026 — Claude Code + AIRO: From Vibe Coding to Production, Live"**, a live demo session. Fictional company: **IDEA Lifestyle** ($47B home-furnishings retailer). Storyline SKU: **BRH-2240** (Branchwood 3-Cube Modular Shelf), Texas region.

## Source of truth

1. **`wow2026-sell-through-drift-runbook.md` governs everything.** Demo scenario, stage beats, talk track, insight layer, backup plan, open items. If this file and anything else disagree, the runbook wins.
2. `wow2026-sell-through-drift-prd.md` is an *artifact* of the runbook (Stage 4 beat), not an independent spec. Changes to it must stay consistent with the runbook's ground truth.
3. `README.md` is the asset index. If you add or rename a file in this folder, update it.
4. The two Google Docs linked from the README (session outline, MCP design spec) are editable sources of truth for their topics — don't fork local copies.

## Environment: stub MCP servers

Two deterministic stub servers back the Investigate beat. They live on the PE Copilot **preview** workspace, folder "AIRO + Claude Code" (folder_id `578470`, project_id `552603`).

**Migrated 2026-09-15** from the original folder "WoW 2026 - Sell-Through Drift Demo" (folder_id `578568`, project_id `552655`, owned by the "IDEA Lifestyle CS" workspace user) after that folder became unreachable from the working Claude session's AIRO credentials (a collaborator/grant gap, not a data issue). The original folder and recipes may still exist but should be treated as stale — this is the current source of truth.

- `sales-inventory-mcp` — handle `mcps-AbbwNosG-gbT-B6`, 6 tools (`get_sell_through`, `get_store_sell_through`, `get_inventory_positions`, `get_purchase_orders`, `get_backorder_cases`, `get_product`), gateway `https://12572.apim.mcp.preview.workato.com`
- `crm-promotions-mcp` — handle `mcps-AbbwQx3k-zX4-B6`, 2 tools (`get_promotions`, `get_price_history`), gateway `https://12575.apim.mcp.preview.workato.com`

Each tool is a Workato recipe using the `workato_skill` trigger, converted to a Skill (`skl-*` handle) before being attached to its MCP server — plain recipe IDs alone are not enough for this trigger type. Source recipe code lives in `mcp-servers/recipe-codes/*.code.json`; `scripts/migrate_mcp_stubs.py` rebuilds recipes + servers from scratch in a target folder (it needs a `config` field per recipe and the skill-conversion step to fully work — both were bugs fixed in this migration; token minting is `POST /mcp/mcp_servers/{handle}/tokens`, which returns `plain_token` directly, not a separate renew call).

`.mcp.json` in this folder registers both for Claude Code (HTTP transport, Bearer token). `.claude/settings.json` auto-approves them (`enabledMcpjsonServers`) so `claude` launches in this folder don't prompt. The tokens are demo-scoped but still secrets: don't paste them into Slack, docs, or screenshots.

## Ground-truth invariants (do not break)

The demo depends on these exact seeded numbers. Any session that touches seed data, the PRD, or the talk track must preserve them:

- Texas sell-through **−39.7%** over 6 weeks; all other regions within ±2pts. (Talk track rounds to "40%" — that's intentional.)
- **12 of 40** Texas stores drive the drop: **8 fall off a cliff** from week 2026-08-17 (60→28), 4 mild (61→54).
- The same **8 stores** have been at/below safety stock since **2026-08-03** — stock-out precedes the sales drop by ~2 weeks. Served by DCs Dallas North / Dallas South.
- Two Branchwood POs — **PO-78412** and **PO-78455** — slipped 2026-08-14 → 2026-09-18 ("vendor production backlog"), serving exactly those 8 stores.
- **8 backorder cases**, `VENDOR_DELIVERY_DELAY`, Branchwood, opened 2026-08-04..07.
- Texas promotion window **clean** for BRH-2240; contrast promos exist only in CA/FL; price flat at **$89.99** for 12 weeks.
- Preferred substitute per merchandising rule: **IDH-3310** (IDEAONE House 3-Cube Storage Unit), $79.99, similarity 0.94, `preferred_substitute_on_similarity_tie`, in stock in all 8 affected stores.

**Never invent brand names.** Branchwood and IDEAONE House are canon in the storyline. **Never fabricate data beyond the seeds** — every claim made on stage must be reproducible via the stub tools.

## Working agreements

- **PRD format is canonical** per the `writing-workato-prds` skill: Executive Summary → Product Vision → Target Users → Problem Statement → Solution Overview with the mermaid flow diagram → F1–F5 → Exit Criteria / NFRs / Out of Scope / Success Metrics / Security / Data → Customer Evidence. Keep the diagram; it's the on-stage artifact. The PRD carries no PMO number by design (fictional in-demo document) — don't add one.
- **Apply the `unslop` skill to every piece of writing** produced in this folder — the PRD, the runbook, the talk track, artifact copy, Slack drafts, commit messages, anything read by a human. This is on top of the format skills, not instead of them: `writing-workato-prds` sets the structure, `unslop` strips the AI tells out of the prose inside it. Pair with `my-writing-style` for anything in Bennett's voice. This matters more than usual here because the talk track is spoken aloud on stage — filler phrasing that survives in a doc is audible in a room.
- **Talk-track vs. tool output:** the insight layer in runbook Stage 3 is the business-user voice — number → meaning → money/ownership/precedent. Don't rewrite it into restatements of the numbers.
- **Timing:** ~45.5 min as drafted; the runbook's open items track the ~1 min trim decision. Don't silently re-time beats.
- **Verification:** if you change anything data-facing, re-run a tool call against both gateways and confirm the invariants above still hold before claiming it works.
- **Open items live in the runbook** (env confirmation, co-speaker, live-vs-recorded per beat, timing). Don't fork them into side files.

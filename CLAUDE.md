# WoW 2026 - Claude Code + AIRO: session repo

This repo backs the 45-minute breakout **"Claude Code + AIRO: From Vibe Coding to Production, Live."** It is also a demo artifact in its own right: outline section 7 ends by pushing this repo so a teammate can pick up where the session left off. Treat it as something a stranger will clone.

Fictional company: **IDEA Lifestyle**, a $47B home-furnishings retailer, 800+ stores, 50+ countries.

## Source of truth

1. **The session outline Google Doc governs the flow.** [WoW2026: Claude Code + AIRO](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc). If this repo and the doc disagree about structure, the doc wins. Do not fork a local copy of it.
2. `docs/runbook.md` is the stage-by-stage execution detail *under* that outline. It implements the doc; it does not override it.
3. `README.md` is the repo index. If you add or rename a top-level file, update it.

## Session flow

Four verbs, in order. Each stage adds one capability and reuses the last.

| Stage | What it shows |
|---|---|
| Opening | Build speed is not ship speed |
| Scenario | IDEA Lifestyle, one simple use case that carries the rest |
| Connect | Wiring Claude Code to AIRO MCP and Dev API MCP |
| **Build** | One skill: create, test, verify, read the recipe logic, change it, re-test live |
| **Scale** | Many skills at once, then wrapped into an MCP server teammates use from their own clients |
| **Automate** | A Genie over those skills plus KBs, tested, then driven by a recipe so it runs unattended |
| **Tune** | Tribal knowledge saved as agent skills, regression scripts, pushed to this repo |

Co-speaker: Abhishek Bhattacherjee.

## Use case and environment

Decided 2026-09-19.

**Store operations desk.** IDEA Lifestyle runs 800+ stores. A store manager's day is full of small operational questions and requests: damaged stock, facilities faults, staffing approvals. Today that means digging through a policy portal or emailing head office. The session builds the desk that answers them.

It satisfies the outline's three constraints. It introduces in about 90 seconds, the skills are ones a store manager would genuinely want in Claude Desktop, and ticket triage gives an honest reason to run unattended.

**Environment: Workato preview, workspace "IDEA Lifestyle Customer Data & Personalization" (325807).** Root folder `577822`. Build into project **"Idea Lifestyle Conference Demo"** (project `555710`, folder `583790`), which exists and is empty.

Authorized connections there, verified 2026-09-19. Design within these:

| Connection | ID | Provider |
|---|---|---|
| SFDC - DEV | 105904 | salesforce |
| Ideal Lifestyle | 105903 | slack |
| TypeSafe AI | 108365 | rest |

`Loma's Datadog Connection` (105619) exists but was never authorized. Anything else needs creating first.

Salesforce Cases carry the tickets, Slack carries escalation, and Workato Data Tables plus a Knowledge Base carry store and policy data. The previous sell-through drift storyline was retired on 2026-09-19 and is recoverable from commit `a9b4f8b`.

## Secrets

Six live bearer tokens were found in this folder on 2026-09-19. `.mcp.json`, `.codex/` and `.omp/` are gitignored for that reason, and `.mcp.json.example` carries placeholders instead.

- Never commit a real token, gateway URL with credentials, or API key.
- Run a secret scan over staged content before any push, not just a filename check.
- Demo-scoped tokens are still secrets. Keep them out of Slack, docs, and screenshots.

## Working agreements

- **Apply the `unslop` skill to everything written here.** Runbook, talk track, README, commit messages, anything a human reads. This matters more than usual because the talk track is spoken aloud, and filler that survives in a doc is audible in a room. Pair with `my-writing-style` for anything in Bennett's voice. Both load from the personal skills folder and are deliberately not vendored here.
- **Read `.claude/skills/workato-airo-build-notes/` before building Workato assets through MCP.** It holds the gotchas that cost hours to rediscover: the `config: []` requirement, skill-handle attachment, which MCP reaches which workspace, and why `get_recipe_test_status` cannot be trusted.
- **`.claude/skills/README.md` indexes the rest.** Skills for building Genies, ingesting Knowledge Bases and standing up MCP servers are vendored so the repo is self-contained for the build. They are snapshots taken 2026-09-19 and will drift from upstream.
- **Verify against the live workspace before claiming something works.** Every number and behaviour shown on stage must be reproducible with a tool call.
- **Do not invent brand names.** Branchwood and IDEAONE House are canon within IDEA Lifestyle if the new use case needs suppliers.
- Open items live in `docs/runbook.md`. Do not fork them into side files.

## Stale references

The [MCP Server & Build Agent Design Spec](https://docs.google.com/document/d/1fyi7zH0w0PEdpnKbrUc1WzZMSa7orIjahBy4_whB1Pw) describes the retired `sales-inventory-mcp` and `crm-promotions-mcp` stub servers. Those servers still exist on the PE Copilot preview workspace (folder 578470) but no longer back this session. Ignore the spec unless the new use case happens to reuse them.

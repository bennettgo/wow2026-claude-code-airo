# WoW 2026 - Claude Code + AIRO: demo repo

This repo backs the 45-minute breakout **"Claude Code + AIRO: From Vibe Coding to Production, Live."** It is also a demo artifact in its own right: outline section 7 ends by pushing this repo so a teammate can pick up where the talk left off. Treat it as something a stranger will clone.

Fictional company: **IDEA Lifestyle**, a $47B home-furnishings retailer, 800+ stores, 50+ countries.

## Source of truth

1. **The outline Google Doc governs the flow.** [WoW2026: Claude Code + AIRO](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc). If this repo and the doc disagree about structure, the doc wins. Do not fork a local copy of it.
2. `docs/runbook.md` is the stage-by-stage execution detail *under* that outline. It implements the doc; it does not override it.
3. `README.md` is the repo index. If you add or rename a top-level file, update it.

## Flow

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

## Running the demo live

Everything else in this file is written for maintaining the repo between talks. This section governs a session that is running the talk, rehearsed or presented. Where it conflicts with the rest of this file, this section wins.

**Default to this section, do not wait to detect that you're on stage.** A fresh session has no way to tell rehearsal from a maintenance request except the shape of the ask. If the user asks you to build, create, or change a Workato asset ("build me a skill that...", "I need an MCP that...", "make it also return..."), that ask itself is the signal — treat it as this section governs, immediately, without asking whether this is a rehearsal or the real thing. Only fall back to the rest of this file when the request is unambiguously about repo maintenance between talks (editing docs, reviewing the runbook, cleaning up open items).

**Build when asked. Do not audit first.** "Build me a skill that checks case statuses" is the script, not an ambiguous request. Do not check whether the asset already exists in production, and do not tell the user it already exists — that framing is exactly the stall this rule exists to prevent. If it exists in production, that is what makes the rehearsal build safe (see below), not a reason to stop and say so. Each stage has about seven minutes and a round of questions costs most of it.

**A rehearsal build is not a duplicate.** Stage 4 rebuilds `get_case_status`, which already exists in production. That is the point: the room watches it get built. Build it in `Test Runs` (`583807`), which leaves the production asset in `Customer Service MCP` (`583808`) untouched. The scratch folder is how the no-duplicates rule is satisfied here, so do not stop to raise it as a conflict.

**Do not ask clarifying questions on stage.** Pick the documented default, name it in one sentence, keep going. A 2026-09-20 rehearsal stalled on three `AskUserQuestion` calls before creating a single asset. If something is genuinely undecided, choose and say so rather than stopping.

**Grounding budget is one file:** `.claude/skills/workato-airo-build-notes/`. The moment a build request lands, load that skill and start building — do not first read the runbook, the build brief, the PRD, or the talk track to check current state, confirm an asset's existence, or decide whether the request is a duplicate. Those files are written for maintaining the repo between talks, not for answering a build request live. If you catch yourself reading `docs/runbook.md` or similar in response to a build ask, stop and build instead.

**Start what you build.** `workspace_push` does not start a recipe, and an unstarted recipe's MCP tool reads `active=False` and is unreachable from a real client. `recipe.test.start` passes anyway, which hides it. Run `recipe.start` before claiming a teammate can call it.

| Stage | What the prompt asks for | Build into |
|---|---|---|
| 4, Build | One skill, case lookup by number, then change it and re-test | `Test Runs` (`583807`) |
| 5, Scale | John's remaining jobs in one pass, bundled into an MCP server | `Test Runs`, or show the built production set |
| 6, Automate | A Genie over those skills plus the policy KB, then a recipe running it unattended | already built, see the runbook |
| 7, Tune | Save the gotchas as agent skills, push the repo | this repo |

## Use case and environment

Decided 2026-09-19.

**Store operations desk.** IDEA Lifestyle runs 800+ stores. A store manager's day is full of small operational questions and requests: damaged stock, facilities faults, staffing approvals. Today that means digging through a policy portal or emailing head office. This repo builds the desk that answers them.

It satisfies the outline's three constraints. It introduces in about 90 seconds, the skills are ones a store manager would genuinely want in Claude Desktop, and ticket triage gives an honest reason to run unattended.

**Environment: workspace "IDEA Lifestyle Customer Data & Personalization" (325807), reached through `workato-airo-mcp-preview` and `workato-dev-api-preview`.** Root folder `577822`. Build into project **"AIRO + Claude Code - WoW 2026"** (project `555716`, folder `583806`), with subfolders `Test Runs` (`583807`) for rehearsal builds and seeding utilities, and `Customer Service MCP` (`583808`) for the real assets. The earlier plan to use project `555710` is dropped: that project holds Loma Desai's own finished build, not ours to write into. See the runbook for what is built and what is still open.

Authorized connections there, verified 2026-09-19. Design within these:

| Connection | ID | Provider |
|---|---|---|
| SFDC - DEV | 105904 | salesforce |
| Ideal Lifestyle | 105903 | slack |
| TypeSafe AI | 108365 | rest |

`Loma's Datadog Connection` (105619) exists but was never authorized. Anything else needs creating first.

Salesforce Cases carry the tickets, Slack carries escalation, and Workato Data Tables plus a Knowledge Base carry store and policy data. The previous sell-through drift storyline was retired on 2026-09-19 and is recoverable from commit `a9b4f8b`.

## MCP endpoints

Both reach workspace 325807. Verified 2026-09-19.

| Server | Role | Endpoint | Auth | Docs |
|---|---|---|---|---|
| `workato-airo-mcp-preview` | builds | `https://app.preview.workato.com/airo_mcp` | OAuth, no header in config | https://docs.workato.com/en/airo/mcp |
| `workato-dev-api-preview` | audits | `https://app.preview.workato.com/mcp` | `Authorization: Bearer <token>` | https://docs.workato.com/en/mcp/developer-api-mcp |

`.mcp.json.example` carries both with placeholders. The live `.mcp.json` is gitignored.

When introducing either server for the first time in a conversation, include its docs link from the table above.

## Secrets

Four distinct bearer tokens sit in this folder untracked, across six occurrences in three client configs. `.mcp.json`, `.codex/` and `.omp/` are gitignored for that reason, and `.mcp.json.example` carries placeholders instead.

They all belong to the retired `sales-inventory-mcp` and `crm-promotions-mcp` stub servers. Two (`1e03f322…`, `ff7d7f1c…`, in `.mcp.json` and `.omp/mcp.json`) still reach live servers on preview at gateways 12572 and 12575. The other two (`ed66cc7a…`, `fdf1005c…`, in `.codex/config.toml`) point at gateways 11680 and 11681, which belonged to the pre-migration folder `578568` and are stale.

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

The [MCP Server & Build Agent Design Spec](https://docs.google.com/document/d/1fyi7zH0w0PEdpnKbrUc1WzZMSa7orIjahBy4_whB1Pw) describes the retired `sales-inventory-mcp` and `crm-promotions-mcp` stub servers. Those servers still exist on the PE Copilot preview workspace (folder 578470) but no longer back this build. Ignore the spec unless the new use case happens to reuse them.

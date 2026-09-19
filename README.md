# WoW 2026 — Claude Code + AIRO: From Vibe Coding to Production, Live

Working repo for a 45-minute breakout session. It holds the runbook, the agent skills captured while building, and the scripts used to check that what we built still works.

The session itself ends by pushing this repo, so it doubles as the demo's final artifact. Someone who clones it should be able to continue the build.

## What the session argues

Vibe coding gets you a working prototype in minutes. Getting that prototype into production with governance, security and observability intact is where projects stall for weeks. The session closes that gap live, one prompt at a time, across four stages: **build**, **scale**, **automate**, **tune**.

Execution Plane covers ideating and building. Control Plane covers verifying and deploying. Execution Plane speed only matters once Control Plane makes it trustworthy.

## Quick start

```bash
cp .mcp.json.example .mcp.json
```

Fill in real values, then connect the two MCP servers the session runs on:

- **AIRO MCP** builds. Recipes, skills, MCP servers, Genies. It is the only thing that mutates the workspace. https://docs.workato.com/en/airo/mcp
- **Dev API MCP** audits. Job logs, failures, test runs, connections. It never builds anything. https://docs.workato.com/en/mcp/developer-api-mcp

Keeping those two roles separate is the point, not an accident of tooling. If AIRO both builds the thing and reports that the thing works, there is no reason to believe the report.

`.mcp.json` is gitignored because it carries live bearer tokens. Never commit it.

## Layout

| Path | What it holds |
|---|---|
| `docs/runbook.md` | Stage-by-stage execution detail, timings, open items |
| `.claude/skills/` | Agent skills captured during the build (outline section 7) |
| `.claude/settings.json` | MCP auto-approval so a `claude` launch here does not prompt |
| `.mcp.json.example` | Template for the two MCP connections |

## Source of truth

The [session outline Google Doc](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc) governs the flow. This repo implements it. Where they disagree about structure, the doc wins.

`CLAUDE.md` holds the working agreements for anyone, human or agent, making changes here.

## Status

Restructured 2026-09-19 around the outline's build/scale/automate/tune flow. The previous version was built around a "Sell-Through Drift Monitor" investigation storyline, which has been retired; it is recoverable from commit `a9b4f8b`.

**The use case is still open**, and it blocks most stage content. See "Open items" in the runbook.

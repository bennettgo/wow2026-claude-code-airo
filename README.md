# WoW 2026 - Claude Code + AIRO: From Vibe Coding to Production, Live

Working repo for a 45-minute breakout session. It holds the runbook, the agent skills captured while building, and the scripts used to check that what we built still works.

The session itself ends by pushing this repo, so it doubles as the demo's final artifact. Someone who clones it should be able to continue the build.

## What the session argues

Vibe coding gets you a working prototype in minutes. Getting that prototype into production with governance, security and observability intact is where projects stall for weeks. The session closes that gap live, one prompt at a time, across four stages: **build**, **scale**, **automate**, **tune**.

Execution Plane covers ideating and building. Control Plane covers verifying and deploying. Execution Plane speed only matters once Control Plane makes it trustworthy.

## Quick start

```bash
cp .mcp.json.example .mcp.json
```

Then connect the two MCP servers the session runs on. Both live on the Workato
preview data centre, because that is where the demo workspace is.

| Role | Server | Endpoint |
|---|---|---|
| Builds | AIRO MCP | `https://app.preview.workato.com/airo_mcp` |
| Audits | Dev API MCP | `https://app.preview.workato.com/mcp` |

- **AIRO MCP** builds. Recipes, skills, MCP servers, Genies. It is the only thing that mutates the workspace. [Docs](https://docs.workato.com/en/airo/mcp)
- **Dev API MCP** audits. Job logs, failures, test runs, connections, project grants. It never builds anything. [Docs](https://docs.workato.com/en/mcp/developer-api-mcp)

Keeping those two roles separate is the point, not an accident of tooling. If AIRO both builds the thing and reports that the thing works, there is no reason to believe the report.

### Authentication

AIRO MCP takes either. OAuth 2.0 is the interactive path: the client opens a
browser on first connect and stores the credential itself, so the config needs
no header at all. An API token is the headless path, passed as
`Authorization: Bearer <token>`. `.mcp.json.example` shows the OAuth shape.

Dev API MCP takes a bearer token only, minted from an API client. What the
server can do is whatever tools that API client's role enables, so a read-only
role keeps the audit side honest by construction.

`.mcp.json` is gitignored because it carries live bearer tokens. Never commit it.

### Other regions

Swap the host. AIRO MCP publishes a per-region endpoint: `app.workato.com`
(US), plus `app.eu`, `app.jp`, `app.sg`, `app.au`, `app.il`, `app.kr`,
`app.uk`, and `app.trial` for a Developer Sandbox. The Dev API MCP docs give a
single `https://app.workato.com/mcp` for every region. Neither is available in
the CN data centre.

One thing worth not confusing: `app[.region].workato.com` is the **platform**,
the two servers above. A host like `<server-id>.apim.mcp.workato.com` is an MCP
server **you built** on Workato, which is what stage 5 of this session
produces. They are different layers and the URL shapes do not overlap.

## Layout

| Path | What it holds |
|---|---|
| `docs/runbook.md` | Stage-by-stage execution detail, timings, open items |
| `docs/stage5-build-brief.md` | Work order for building stage 5 in a second, parallel Claude Code session |
| `.claude/skills/` | Agent skills captured during the build (outline section 7) |
| `.claude/settings.json` | MCP auto-approval so a `claude` launch here does not prompt |
| `.mcp.json.example` | Template for the two MCP connections |

## Source of truth

The [session outline Google Doc](https://docs.google.com/document/d/1Gx5TYPLl88pTPg0le_ShjRXq5jLHZOJcvcdmBiGyTlc) governs the flow. This repo implements it. Where they disagree about structure, the doc wins.

`CLAUDE.md` holds the working agreements for anyone, human or agent, making changes here.

## Status

Restructured 2026-09-19 around the outline's build/scale/automate/tune flow. The previous version was built around a "Sell-Through Drift Monitor" investigation storyline, which has been retired; it is recoverable from commit `a9b4f8b`.

**The use case is still open**, and it blocks most stage content. See "Open items" in the runbook.

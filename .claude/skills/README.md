# Skills in this repo

Agent skills scoped to this project. Claude Code loads them automatically when working in this folder, so a teammate who clones the repo gets them without installing anything.

This is outline stage 7 made concrete: the knowledge used to build the demo ships with the demo.

## Authored here

| Skill | What it covers |
|---|---|
| `workato-airo-build-notes` | Gotchas from this build. Which MCP reaches which workspace, the `config: []` requirement, attaching skills by `skl-*` handle, minting server tokens, why `get_recipe_test_status` cannot be trusted, and the data-table-backed skill pattern. |

## Vendored copies

Copied on 2026-09-19 so the repo is self-contained. **They are snapshots and will drift from upstream.** If one looks stale, check the source before trusting it.

| Skill | Source | Why it is here |
|---|---|---|
| `unslop` | `~/.claude/skills` | CLAUDE.md requires it for everything written here. The talk track is spoken aloud, so filler that survives in a doc is audible in a room. |
| `my-writing-style` | `~/.claude/skills` | Paired with `unslop` for anything in Bennett's voice. |
| `workato-genie-builder` | `~/.claude/skills` | Stage 6 builds a Genie, attaches skills and KBs, and mints a client. |
| `workato-kb-ingest` | `~/.claude/skills` | Stage 6 attaches a Knowledge Base of store operations policy. Covers the fact that `POST /api/files` does not exist and what to do instead. |
| `workato-genie-benchmark` | `~/.claude/skills` | Stage 7 wants regression checks against the Genie. This is the systematic version of that. |
| `building-workato-mcp-apps` | `wapl/workato-mcp-apps` plugin | Stage 5 stands up an MCP server and connects a client to it. Note this skill is primarily about interactive MCP *apps*; use it for the server setup and client connection parts. |

## Deliberately not vendored

`writing-workato-prds` and `updating-workato-prds`, because the session has no PRD beat. `pptx` at 1.3MB, because it is general-purpose and available globally. `skill-creator`, for the same reason.

## Refreshing a vendored skill

```bash
rm -rf .claude/skills/<name>
cp -R ~/.claude/skills/<name> .claude/skills/
find .claude/skills -name '__pycache__' -type d -exec rm -rf {} +
```

Scan for credentials before committing. These skills contain worked examples, and an example that was safe in a personal folder is not automatically safe in a repo.

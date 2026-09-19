# workato-genie-builder — a portable Claude skill

A shareable Claude Code / Agent SDK skill that walks any AI session through building a Workato Genie from scratch — including a complete worked example (the HR Concierge) so a new session goes 0→1 in under a minute.

## Install

### Option 1 — Personal install
```bash
# clone or download this folder
mkdir -p ~/.claude/skills
cp -R workato-genie-builder ~/.claude/skills/
```

Restart your Claude session. The skill auto-loads. Trigger with any of:
- `Help me build a Workato Genie`
- `/workato-genie-builder`
- `Set up an HR chatbot in Workato`

### Option 2 — Project install
Drop the `workato-genie-builder/` folder anywhere inside a repo's `.claude/skills/` directory:
```bash
mkdir -p .claude/skills
cp -R workato-genie-builder .claude/skills/
```

Anyone who clones the repo and uses Claude Code in it picks up the skill automatically.

### Option 3 — Share as zip
```bash
zip -r workato-genie-builder.zip workato-genie-builder/
```
Send to your colleague. They unzip into their `.claude/skills/` directory.

## Verify install

In Claude Code, type `/help` or just ask "what skills do I have?" — `workato-genie-builder` should be listed.

To trigger it explicitly: `/workato-genie-builder` or describe the task ("create a Workato Genie for our HR team").

## What you need to start

**Two things:**

### 1. A Workato Dev API token (a `wrkaus-…` string)

1. Sign in to your Workato workspace as an admin.
2. Go to **Workspace admin → API clients** (or **Settings → Developer API**).
3. Click **+ Create client** → name it (e.g. "Genie Builder").
4. Assign these **client roles** (all of them — the token will 401 on agentic endpoints if any are missing):
   - Genies (read + write)
   - **Genie Client** (read + write) ← most commonly missed
   - Recipes (read + write)
   - Folders / Projects (read + write)
   - IAM Users + IAM User Groups (read + write)
5. Copy the `wrkaus-…` token. It's shown only once.

### 2. Which Workato data center your workspace is on

Workato runs separate, isolated regional clouds. Tokens are **scoped to their DC** — a US token cannot call an EU workspace. Look at the URL when you're signed in:

| Your URL contains | `WORKATO_DC` value | Dev API host | Headless host |
|---|---|---|---|
| `app.workato.com` | `us` (default) | `app.workato.com` | `genie-api.workato.com` |
| `app.eu.workato.com` | `eu` | `app.eu.workato.com` | `genie-api.eu.workato.com` |
| `app.jp.workato.com` | `jp` | `app.jp.workato.com` | `genie-api.jp.workato.com` |
| `app.sg.workato.com` | `sg` | `app.sg.workato.com` | `genie-api.sg.workato.com` |
| `app.au.workato.com` | `au` | `app.au.workato.com` | `genie-api.au.workato.com` |
| `app.in.workato.com` | `in` | `app.in.workato.com` | `genie-api.in.workato.com` |
| `app.il.workato.com` | `il` | `app.il.workato.com` | `genie-api.il.workato.com` |

### Verify both

```bash
export DEV_API_TOKEN=wrkaus-...
export WORKATO_DC=us   # or eu, jp, sg, au, in, il

DC_HOST="app.workato.com"
[ "$WORKATO_DC" != "us" ] && DC_HOST="app.$WORKATO_DC.workato.com"
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $DEV_API_TOKEN" \
  "https://$DC_HOST/api/agentic/genies?per_page=1"
# Expect: 200
# 401 → re-check client roles; 404 / connection refused → wrong DC
```

If both pass: that's the entire prerequisite. The skill creates folders, genies, skills, user groups, and clients for you.

## 0→1 quick start

Once installed and you have your token + DC:

```bash
# Inside any Claude session:
> Use the workato-genie-builder skill to provision the example HR Concierge in my workspace.
> DEV_API_TOKEN=wrkaus-..., WORKATO_DC=eu, my email is alice@example.com.
```

Claude will:
1. Read this skill.
2. Verify your token works (one curl).
3. Read `examples/hr-concierge.json` (the complete genie spec).
4. Run `scripts/provision-genie.py` with the spec.
5. Print the runtime credentials (genie ID, skill IDs, api_key).
6. Run `scripts/test-headless-chat.sh` to verify the genie actually answers a real question.

End state, under a minute: a running InnovaTech HR Concierge genie with 4 stub skills, callable from the Headless API.

## What's in this skill

```
workato-genie-builder/
├── SKILL.md                              ← entry point Claude reads
├── README.md                             ← this file
├── references/
│   ├── api-reference.md                  ← every endpoint, curl-ready
│   └── gotchas.md                        ← every common error and its fix
├── scripts/
│   ├── provision-genie.py                ← full E2E provisioning (reads JSON spec)
│   └── test-headless-chat.sh             ← runtime smoke test
└── examples/
    ├── hr-concierge.json                 ← drop-in genie spec
    ├── hr-concierge-instructions.md      ← the genie's system prompt
    └── sample-run.md                     ← expected output from a successful run
```

## Building your own genie

Copy `examples/hr-concierge.json` to e.g. `my-support-bot.json`, edit:
- `genie.name`, `genie.description`, `genie.instructions_file`
- `skills[]` — add/remove/edit
- `user_group.name`

Then:
```bash
python3 scripts/provision-genie.py my-support-bot.json
```

## License / share

MIT. Share freely.

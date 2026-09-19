# Sample run — what success looks like

This is what a clean run of `provision-genie.py` against the bundled HR Concierge spec produces. Use it to compare against your output if something feels off.

## Inputs

```bash
export DEV_API_TOKEN=wrkaus-eyJ0eXAi...    # your builder token
export WORKATO_DC=us                        # or eu, jp, sg, etc.
export USER_EMAIL_TO_ALLOWLIST=alice@example.com
export AUTH_TYPE=api_key
```

## Command

```bash
python3 scripts/provision-genie.py examples/hr-concierge.json
```

## Expected output

```
▶ Workato Genie provisioner
  DC:       us (app.workato.com)
  Spec:     examples/hr-concierge.json
  Dry-run:  False

[0/9] Verify token + DC
    ✓ Token works against app.workato.com
    ✓ Token belongs to: alice@example.com
    Allow-list target: alice@example.com

[1/9] Create folder 'InnovaTech HR Concierge'
    ✓ folder_id=31495756  project_id=14123876

[2/9] Create genie 'InnovaTech HR Concierge'
    ✓ genie_id=gin-AaNpL4XP-baNnFY-CD

[3/9] Start genie
    ✓ state=active

[4/9] Build 4 stub skills
    ✓ recipe_id=73227015  Get PTO Balance
    ✓ recipe_id=73227016  List Benefits
    ✓ recipe_id=73227017  Submit Time Off Request
    ✓ recipe_id=73227018  Get Latest Payslip

[5/9] Look up auto-created skill IDs
    ✓ skill_id=skl-AaPDrEWp-rF9dch-CD  Get PTO Balance
    ✓ skill_id=skl-AaPDrGHk-LP9t8Y-CD  List Benefits
    ✓ skill_id=skl-AaPDrHsN-EXfbaz-CD  Submit Time Off Request
    ✓ skill_id=skl-AaPDrKXc-dk4Qpn-CD  Get Latest Payslip

[6/9] User group 'HR Concierge Users'
    ✓ group_id=usrgrp-1780740428
    ✓ idp_user_id=u_abc123def456
    ✓ alice@example.com ∈ HR Concierge Users

[7/9] Attach skills + group to genie
    ✓ 4 skills attached
    ✓ user group attached

[8/9] Mint api_key client + attach
    ✓ client_id=gincl-AaCx4NAC-zmzXRb-B6
    ✓ client attached to genie

[9/9] Done — runtime credentials

================================================================
  Genie ID:         gin-AaNpL4XP-baNnFY-CD
  Client ID:        gincl-AaCx4NAC-zmzXRb-B6
  Runtime API key:  3a8b1f...d2e9c4  (64 chars total — SHOW ONCE)
  IDP user ID:      u_abc123def456
  Headless base:    https://genie-api.workato.com
================================================================

Smoke test (api_key flow):
  export GENIE_ID=gin-AaNpL4XP-baNnFY-CD
  export GENIE_API_TOKEN=3a8b1f...d2e9c4
  export IDP_USER_ID=u_abc123def456
  export WORKATO_DC=us
  bash scripts/test-headless-chat.sh "Hello, who are you?"
```

## Smoke test output

```
▶ Workato Genie smoke test
  DC:        us (genie-api.workato.com)
  Genie:     gin-AaNpL4XP-baNnFY-CD
  User:      u_abc123def456
  Message:   How much PTO do I have left?

[1/2] Creating conversation...
       ✓ conversation_id=conversation-abc-123

[2/2] Sending message (streaming SSE)...
------------------------------------------------------------------
▶  processing.started  run=run-xyz-789
⚙  skill.running: Get PTO Balance
✓  skill.completed: Get PTO Balance  → {"status":"ok","days_used":9,"days_remaining":12,"carryover_days":3,...}

💬 AGENT: You have 12 PTO days remaining this year — that's 9 days used, plus 3 days carried over from 2025 on top of your 21-day allocation. Per the PTO policy, requests of 5 or more consecutive days need manager approval at least 2 weeks in advance. Want help planning a request?
■  processing.finished
------------------------------------------------------------------
✓ Done. Conversation: conversation-abc-123
```

## What if it fails?

| Stage | Common failure | Look at |
|---|---|---|
| `[0/9]` 401 | Wrong DC or missing client roles | Re-check `WORKATO_DC`; ensure all roles in skill README are assigned |
| `[1/9]` 422 | Folder name already exists at root | Change `folder_name` in the spec, or set `PARENT_FOLDER_ID` to nest it |
| `[4/9]` 422 | Recipe code malformed | Check that the schemas in `examples/hr-concierge.json` are JSON-valid |
| `[5/9]` skills not found | Eventual-consistency lag | Wait 5 seconds, re-run — the script retries once automatically |
| `[6/9]` user not found | The email is not yet a Workato user | Create them via `POST /api/iam/users` first, or change to an existing user's email |
| `[8/9]` 401 | Token missing `Genie Client` scope | Workspace admin → API clients → edit → enable that role |
| smoke test 406 | Client mint succeeded but attach didn't | Re-run from `[8/9]` only — script is idempotent for that step |
| smoke test 403 | User isn't in the allow-list group at runtime | Re-verify `[6/9]` and `[7/9]` succeeded |

## Idempotency

Re-running the script:
- Folder creation will **fail** (name conflict). Either delete the folder, or comment out steps 1–3 to update an existing genie.
- User group with the same name is detected and reused.
- User-to-group membership is idempotent (no error if already a member).
- Client mint always creates a new one. To avoid leaking clients, set `AUTH_TYPE=api_key` and stop the script before step 8 if you already have a client.

For a production setup, treat the script as **one-shot per environment**. Maintain genie config drift via `PUT /api/agentic/genies/{id}` calls (instructions, skills, groups) on the existing record.

## Next: build your own

Copy the spec and customize:

```bash
cp examples/hr-concierge.json my-support-bot.json
cp examples/hr-concierge-instructions.md my-support-bot-instructions.md
# Edit both. Then:
python3 scripts/provision-genie.py my-support-bot.json
```

Things to change:
- `genie.name`, `genie.description`
- `genie.instructions_file` → point at your new instructions doc
- `skills[]` — replace with the actions your assistant should expose. Each skill needs name, description, parameter schema, result schema, stub response (used for testing without real connectors). For a real (non-stub) skill, build the recipe in the Workato UI, then reference its `skill_id` directly — but this skill specifically targets stub skills for fast 0→1.
- `user_group_name`

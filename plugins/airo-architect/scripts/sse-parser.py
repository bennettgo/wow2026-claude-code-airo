#!/usr/bin/env python3
"""Parse a Workato Headless SSE stream from stdin, print human-readable lines.

Usage (typically piped from curl): see test-headless-chat.sh
"""
import sys, json

# Track the most recent skill_name from skill.running so terminal events
# (skill.stopped/completed) can display it even if their payload omits it.
last_skill_name = "?"

event_type = None
for line in sys.stdin:
    line = line.rstrip("\n")
    if line.startswith("event:"):
        event_type = line.split(":", 1)[1].strip()
        continue
    if not line.startswith("data:"):
        continue

    raw = line.split(":", 1)[1].strip()
    et = event_type or "?"
    try:
        d = json.loads(raw)
    except Exception:
        print(f"{et} (unparseable): {raw[:120]}")
        continue

    if et == "agent.message":
        print(f"\n💬 AGENT: {d.get('message', '(no text)')}")
    elif et == "skill.running":
        last_skill_name = d.get("skill_name", last_skill_name)
        print(f"⚙  skill.running: {last_skill_name}")
    elif et == "skill.completed":
        res = d.get("result", {})
        body = json.dumps(res)[:160] if res else "(no result in SSE — see agent.message)"
        print(f"✓  skill.completed: {d.get('skill_name', last_skill_name)}  → {body}")
    elif et == "skill.stopped":
        # observed in some runtime versions in place of skill.completed
        res = d.get("result", {})
        body = json.dumps(res)[:160] if res else "(no result in SSE — see agent.message)"
        print(f"✓  skill.stopped:   {d.get('skill_name', last_skill_name)}  → {body}")
    elif et == "skill.failed":
        print(f"✗  skill.failed: {d.get('skill_name', last_skill_name)}  → {d.get('error', '')}")
    elif et == "skill.confirmation_required":
        cid = d.get("call_id", "?")
        print(f"❓ skill.confirmation_required: {d.get('skill_name', '?')} call_id={cid}")
        print(f"   approve via: POST /chat/conversations/<CONV>/skill_approval/{cid}  body=" + '{"resolution":"approved"}')
    elif et == "processing.started":
        print(f"▶  processing.started  run={d.get('genie_run_id', '?')}")
    elif et == "processing.finished":
        print(f"■  processing.finished")
        sys.exit(0)
    elif et.startswith("runtime_connection."):
        print(f"🔌 {et}: {raw[:140]}")
    else:
        print(f"   {et}: {raw[:140]}")

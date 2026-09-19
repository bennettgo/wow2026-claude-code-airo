# WoW 2026 — Claude Code + AIRO: From Vibe Coding to Production, Live
## Demo Runbook — "Sell-Through Drift Monitor" (IDEA Lifestyle)

**Status:** restructured 2026-09-18 around progressive disclosure. Environment decisions recorded below are made but not yet executed. Not rehearsed in this shape.

**Segment alignment note:** this maps to BOAT MQ 2026 Demo Segment 7 ("AI-Assisted Development" — AIRO, Agent Studio, Skills — "Prompt → workflow → agent generation, vibe-coding"), currently unowned and unbuilt. Confirm with Ee Liang Sim whether this session should formally fill that slot before locking the storyline in.

---

## Demo scenario

A store operations analyst at IDEA Lifestyle, a fictional $47B global home-furnishings retailer, flags that a SKU's sales have dropped sharply in one region with no known cause.

The session starts one level below the investigation. The Builder uses Claude Code and AIRO MCP to create a single skill against a real Salesforce connection, asks AIRO to test it, and reads the resulting job log through the Dev API MCP. Then the Builder bundles skills into an MCP server and reconnects it to Claude Code, so the tools used for the rest of the session are tools the room watched get built.

Only then does the investigation run. The Builder rules candidate causes in and out until the real pattern emerges: not one bad number, but a recurring failure mode worth watching for automatically. That investigation produces a PRD on the spot. AIRO then builds, tests, and deploys the resulting system: a Recipe that detects the pattern going forward, and a Genie that investigates a bounded set of known causes and recommends action, with a human decision required before anything executes. The session closes by packaging this as a shareable skill.

---

## Cast

| Role | Played by | Scope |
|---|---|---|
| The Builder | Presenter (live) | Drives rounds one and two. Exits the story once the PRD is written. |
| Claude Code | Live tool | Pairs with the Builder through the build and the investigation. Not part of anything that runs afterward. |
| AIRO MCP | Live tool | Builds. Creates recipes, skills, MCP servers, the Genie. The only tool that mutates the workspace. |
| Dev API MCP | Live tool | Audits. Reads jobs, failures, connections, test runs. Never builds anything. |
| Sell-Through Drift Monitor | The Recipe (built) | Durable backbone: detects drift, invokes the Genie, sends the report, waits on a human decision, resumes, invokes the Genie again to pick the action, executes it. |
| Drift Investigator | The Genie (built) | Two distinct jobs, both reasoning, neither owning the wait: investigate the three known candidates and write the report; then, given a human decision, decide which downstream action to trigger. |
| Procurement / inventory reviewer | Human-in-the-loop (simulated) | Receives the report, sends back a decision. In the loop at exactly one point. |

**Say the AIRO/Dev API split out loud when you switch tools.** It carries the whole verifiability argument. If AIRO both builds the thing and reports that the thing works, the room has no reason to believe the report. A second credential reading the same workspace is the control.

---

## Feature focus (name these explicitly on stage)

- Claude Code as the driver, from first skill through investigation
- **AIRO MCP** as the builder: skill, MCP server, Recipe, Genie
- **Dev API MCP** as the independent auditor: job logs, failures, test evidence
- A Workato Skill is an MCP tool. An MCP server is a bundle of them. Say this plainly when you bundle.
- Recipe vs. Genie as a deliberate engineering decision, not a default
- Human-in-the-loop modeled as a pause/resume step inside the Recipe itself
- Skill packaging at the close

**Pillar:** Build and Investigate sit in **Execution Plane**. Every test and job-log read, plus the human-decision gate, sits in **Control Plane**. Name both, and note that Control Plane shows up at minute 8, not minute 30.

---

## The scenario data

These numbers are the demo's ground truth. Any change to seeding, the PRD, or the talk track must preserve them exactly.

- **Company:** IDEA Lifestyle — home furnishings retailer, 50+ countries, 800+ stores, $47B revenue, 15,000+ suppliers, HQ Delft, NL.
- **SKU:** `BRH-2240` — Branchwood 3-Cube Modular Shelf. Branchwood is an existing partner brand in IDEA Lifestyle's supplier roster, SKU prefix `BRH-*`.
- **The complaint:** sell-through down 40% over 6 weeks, concentrated in Texas.

Invariants:

- Texas sell-through **−39.7%** over 6 weeks. All other regions within ±2pts. The talk track rounds to "40%" on purpose.
- **12 of 40** Texas stores drive the drop. **8 fall off a cliff** from week 2026-08-17 (60→28). The other 4 decline mildly (61→54).
- The same **8 stores** have been at or below safety stock since **2026-08-03**. Stock-out precedes the sales drop by about 2 weeks. Served by DCs Dallas North and Dallas South.
- Two Branchwood POs, **PO-78412** and **PO-78455**, slipped 2026-08-14 to 2026-09-18, reason "vendor production backlog", serving exactly those 8 stores.
- **8 backorder cases**, reason code `VENDOR_DELIVERY_DELAY`, vendor Branchwood, opened 2026-08-04 through 2026-08-07.
- Texas promotion window **clean** for BRH-2240. Contrast promos exist only in CA and FL. Price flat at **$89.99** for 12 weeks.
- Preferred substitute per merchandising rule: **IDH-3310** (IDEAONE House 3-Cube Storage Unit), $79.99, similarity 0.94, rule `preferred_substitute_on_similarity_tie`, in stock in all 8 affected stores.

Never invent brand names. Branchwood and IDEAONE House are canon. Never fabricate data beyond these seeds. Every claim made on stage must be reproducible through the tools.

---

## Environment

**Decision (2026-09-18): the demo runs on the PE Copilot preview workspace, against real connectors.**

Preview was chosen because ad-hoc skill testing only exists there. `test_recipe` and `test_recipe_input_schema` are preview-only AIRO MCP tools, and they are what make the round-one testing beat possible. The production AIRO MCP can run saved test cases but cannot test a skill ad hoc with a trigger event, which would gut the beat.

### What preview actually has

Authorized connections, verified 2026-09-18:

| Connection | ID | Provider | Status |
|---|---|---|---|
| SFDC - DEV | 105904 | salesforce | authorized 2026-09-11 |
| Ideal Lifestyle | 105903 | slack | authorized 2026-09-12 |
| TypeSafe AI - Salesforce Orchestrator | 108365 | rest | authorized 2026-09-18 |
| My Workato genie slack connection 2 | 106892 | workato_genie_slack | authorized 2026-09-15 |

Not authorized, do not rely on: Microsoft Teams (105622, 105623), Loma's Datadog Connection (105619), genie slack 116 (105620).

Existing demo assets, folder "AIRO + Claude Code" (folder_id `578470`, project_id `552603`):

- `sales-inventory-mcp` — handle `mcps-AbbwNosG-gbT-B6`, 6 tools, gateway `https://12572.apim.mcp.preview.workato.com`
- `crm-promotions-mcp` — handle `mcps-AbbwQx3k-zX4-B6`, 2 tools, gateway `https://12575.apim.mcp.preview.workato.com`

These 8 skills currently return hardcoded JSON. They are not connected to anything. That is the gap this version closes.

### The cost of "real connectors throughout"

Stated plainly, because it is the largest single piece of work in this plan: **the BRH-2240 storyline does not exist in any connected system.** Preview's Salesforce org is a standard CRM dev org. It has Accounts, Contacts, Leads and Opportunities. It does not have sell-through history, inventory positions, purchase orders, or a Texas store list.

Going real means seeding Salesforce with the storyline and rebuilding the 8 skills to query it instead of returning canned payloads. Rough mapping:

| Tool | Salesforce home |
|---|---|
| get_product | Product2, plus a custom field for the substitute rule |
| get_backorder_cases | Case, with a reason-code picklist |
| get_purchase_orders | custom object |
| get_inventory_positions | custom object, keyed by store |
| get_sell_through / get_store_sell_through | custom object, weekly rows per store |
| get_promotions / get_price_history | custom object, or PricebookEntry history |

That is several hours of Salesforce configuration plus data loading, and every row has to preserve the invariants above. Budget it as real work, not setup.

**Fallback if seeding slips:** Workato Data Tables. The pattern is already proven on preview by the ITSM Support Genie skills, which read tables directly:

```
workato_skill.start_workflow(parameters_schema)
  → workato_db_table.get_records(table_id, filters=[{field_id, op, value}])
  → workato_skill.workflow_return_result(result={...})
```

Three steps, no external auth to expire. Tables are still live and mutable, so the "edit a row on stage and watch the tool output change" moment survives. This is a worse story and a much safer one. Decide by the rehearsal date, not on the day.

### Known environment gaps

- **No preview Dev API MCP is wired up.** The Dev API MCP available today returns `app.workato.com` and the IDEA Supplier Management workspace, which is production. Round one's job-log beat depends on having a preview one. This is the top pre-work blocker.
- `get_recipe_test_status` reports `NO_TEST_RUN` even when a test job has already run and succeeded. Verified 2026-09-18 on recipe 1860936. Do not script that call. Go straight to `recipe.job.list`.
- `recipe.job.list` prints `handle=<unavailable>`, but passing the `internal_id` to `recipe.job.get --job-id` works.

---

## Pre-work

Everything here happens before the session. Item 1 blocks the demo.

**P1. Wire up a preview Dev API MCP.** Without it there is no independent auditor on preview and the Control Plane argument collapses into "AIRO says it worked." If it cannot be provisioned, stop and re-open the workspace decision, because that assumption is what put the demo on preview.

**P2. Seed Salesforce with the storyline.** Per the mapping above, preserving every invariant. Verify by querying each object back and checking the numbers.

**P3. Rebuild the 8 skills against Salesforce.** Replace the static `workflow.return_result` payloads with Salesforce queries. Keep the tool names, descriptions and parameter schemas identical so the MCP server contract does not change.

**P4. Re-point the MCP servers and `.mcp.json`.** Both servers keep their handles and gateways. Confirm `tools/call` still passes on all 8 with the invariants intact.

**P5. Rebuild the Genie** ("WoW 2026 - Drift Investigator") against folder 578470's skill handles. It is currently wired to the stale folder 578568. Re-run the headless smoke test after: create conversation, send message, `processing.finished`.

**P6. Capture the audit receipt.** Run the full round-one loop end to end and screenshot the job evidence. This doubles as the backup-plan asset and as the "here is what I did before today" slide.

**P7. Pre-capture the other fallbacks** listed under Backup plan.

**P8. Confirm with Ee Liang Sim:** environment provisioning and Segment 7 ownership.

---

## Talk track (45 min)

### 1. Opening, plus the pre-work receipt (~3.5 min)

Reuse the Product Hour slide: "anyone can lay a plank" plus the production-grade demands checklist. Land the thesis: today you watch the whole gap close, live, one prompt at a time.

Fold the company snapshot in here rather than giving it its own beat. $47B, 800+ stores, 50+ countries. One line on scale: at this size a SKU-level problem is invisible until someone happens to notice.

Then the receipt. "Before today I used AIRO MCP to build this environment and Dev API MCP to check it, independently. Here are the job counts." Show P6's screenshot. This sets the expectation that every claim in the session arrives with evidence, and it buys back time later because Verify no longer has to teach anything.

### 2. Round one: one skill (~10 min)

The whole point of this round is that it is small. Resist the urge to build something impressive.

**Build it (~3 min).** From Claude Code, ask AIRO MCP to create one skill against the Salesforce connection. A recipe with a `workato_skill` trigger is the smallest unit that exists in this system. The room watches Claude Code talk to AIRO and AIRO produce a real Workato asset.

**Test it (~2 min).** Ask AIRO what a test needs, then run it.

```
test_recipe_input_schema(recipe_id=<id>)
test_recipe(recipe_id=<id>, trigger_event={...})
```

The first call is the better beat of the two. Skills have no pollable trigger, so AIRO has to tell you the shape of the event before you can test anything, and it hands you a ready-to-paste sample. Say that out loud: the thing that built it also knows how to exercise it.

**Inspect the job log (~2 min).** Switch to Dev API MCP and say you are switching, and why.

```
recipe.job.list  --recipe-id <id> --limit 5
recipe.job.get   --recipe-id <id> --job-id <internal_id>
```

Status, start and finish timestamps, step count. This is the Control Plane moment. A different credential, reading the same workspace, confirming what AIRO just claimed.

**Bundle and reconnect (~3 min).** Attach skills to an MCP server, then reconnect that server to Claude Code. Land the line: a Workato Skill is an MCP tool, an MCP server is a bundle of them, and Claude Code is now holding tools it just built. If you have one moment to make land in this session, it is this one.

### 3. Round two: the system

#### 3a. Investigate (~5 min)

Show the complaint slide, stat only, no explanation.

Prompt, live, near-verbatim: *"Sell-through on BRH-2240 dropped 40% over six weeks in Texas. Find out why and tell me what we should do."*

Narrate each tool call as it streams: national-vs-regional check, inventory position for the 12 affected stores, promotion calendar (clean), backorder case records (Branchwood delay), catalog substitute lookup (IDEAONE House). Land the finding on screen as Claude's own output. This is where it becomes clear it is one instance of a recurring pattern, not a one-off.

This beat is shorter than the previous draft allowed, and it can be, because the room already trusts the tools. They watched them get built.

**Insight layer, the business-user voice.** This is what separates the session from a tool demo. Never restate the number Claude just showed. Say what it means. Pattern: number, then meaning, then money, ownership, or precedent.

- *Regional split (Texas −39.7%, everywhere else ±2pts):* "A top-200 SKU down 40% in Texas is a seven-figure-quarter problem. Our regional dashboard read this as noise for five weeks, because 8 stores hide inside a 40-store average." Scale the dollar figure to your audience; the shape is what matters.
- *Store concentration (12 of 40, 8 falling off a cliff):* "This is not a Texas problem, it's a Branchwood-lane problem. If I'd escalated 'Texas is soft', merch and marketing would have burned a week chasing it."
- *Stock-out precedes sales (below safety since Aug 3, sales drop starts Aug 17):* "The reorder point worked. The vendor didn't. Nobody in our org owns the gap between ordered and delivered, and that's the actual finding here."
- *Promotions clean, price flat:* "The first question I'd get in any review is 'was it on promo?' We ruled it out in one call instead of a week of merch-versus-marketing finger-pointing."
- *Backorder cases and POs (Branchwood, slipped 5 weeks):* "This goes straight into our Branchwood scorecard conversation, with PO numbers and slip durations attached, not an anecdote."
- *Substitute IDH-3310, in stock in all 8 stores:* "Merch already wrote this rule. The playbook exists, it just never fires fast enough. What I'm about to propose doesn't invent a new playbook, it executes our existing one on time."
- *Close of the beat:* "I found this one SKU by luck and half a day of pulling data. The reason we're building the monitor is so it watches every SKU, every week."

#### 3b. Decide and generate the PRD (~1.5 min)

Builder and Claude agree, out loud: build a drift detector, and a bounded check across the three known candidate causes, rather than re-deriving the answer from scratch next time.

Claude writes the PRD on the spot in the canonical Workato PRD format: Executive Summary, Product Vision, Target Users, Problem Statement, Solution Overview with named flows and one architecture diagram (detection Recipe, investigation Genie, human gate, bounded action set), F1 through F5, then Exit Criteria, NFRs, Out of Scope, Success Metrics, Security, Data, and a Customer Evidence appendix where the BRH-2240 case is the evidence.

Rehearsed reference: `wow2026-sell-through-drift-prd.md` in this folder, written 2026-09-10 in exactly that format. Show the diagram when you flash it. It is the one-glance version of the whole system.

Land the line: *"That's the requirements doc. Nobody wrote a PRD in advance."*

#### 3c. Build (~5 min)

Hand the PRD to AIRO MCP. Show the orchestrator, the solution-architect pipeline, the asset builders.

Build the Recipe (`Sell-Through Drift Monitor`): detect, invoke Genie, send report, wait, invoke Genie, execute. Build the Genie (`Drift Investigator`) with its two-job split, investigate-and-report and decide-and-orchestrate.

Callout: AIRO built one Recipe and one Genie because the problem needed both, not because a Genie was the default.

#### 3d. Verify (~4 min)

Same loop as round one, larger subject. You are not teaching it again, just running it.

Run the three positive test cases (vendor delay, demand surge, inventory mismatch) and confirm the Genie identifies the right cause each time. Run the negative case (healthy SKU) and confirm it stays quiet. Say why that matters: a Genie that never says "no issue" isn't trustworthy, it's just noisy.

Then the human-in-the-loop test specifically. Simulate the reviewer approving, rejecting, and modifying. Show the Recipe pausing and resuming into the right branch each time, and confirm no downstream action fires without that decision. Pull the evidence through Dev API MCP, not AIRO's own summary.

#### 3e. Deploy and package (~2 min)

Ship it. Run the real BRH-2240 case end to end if time allows, narrate it if not.

Package the Drift Investigator's investigation logic as a shareable skill. Close on: *"When EMEA or APAC stand up their own hub, this doesn't get rebuilt, it gets attached."* Tie back to the lifecycle diagram (PLAN → ARCHITECT & BUILD → TEST → DEPLOY → OPERATE → MEASURE & OPTIMIZE → DISCOVER & IMPROVE).

### 4. Co-speaker (~10 min)

[Name] from [Company, ICP-fit, CAB-checked]. Their lens on trusting an agent-built system enough to put it in front of real users.

### 5. Q&A (~5 min)

---

## Timing

| Beat | Minutes |
|---|---|
| Opening, company, pre-work receipt | 3.5 |
| Round one: one skill | 10 |
| Round two: investigate | 5 |
| Round two: PRD | 1.5 |
| Round two: build | 5 |
| Round two: verify | 4 |
| Round two: deploy and package | 2 |
| Co-speaker | 10 |
| Q&A | 5 |
| **Total** | **46** |

One minute over. Trim from the opening once rehearsed. Verify dropped from 8 minutes to 4 and that cut is what pays for round one; it is affordable only because round one already taught the job-log read. If round one gets cut, Verify has to go back up.

---

## Anticipated questions (plant answers, don't wait for them)

- **"Why not just vibe-code the whole thing in Claude?"** Consistency (a Genie is a governed, repeatable skill versus freehand LLM drift), business-event listening instead of polling, verified user access, staying inside one governed environment. Adapted from the Daman Arora Product Hour precedent. Reuse the argument, don't re-derive it live.
- **"Why do you need a Genie at all, shouldn't low stock just trigger a reorder?"** It should, and it already does, as a recipe. That's not the gap. The gap is that the reorder point fired correctly and the vendor still didn't deliver, and nothing was watching for that divergence across systems that don't already talk to each other. State it plainly. Don't oversell agent involvement where a deterministic rule already suffices.
- **"Does the Genie ever investigate on its own, without a human?"** At runtime yes, but only within the three known candidates, every time, the same way. It never does open-ended investigation. That stays a human-plus-Claude-Code exercise and isn't part of what runs in production.
- **"What happens if none of the three candidates explain it?"** Out of scope for this build. Flagged as a known limitation, not solved live. Name it honestly rather than pretending the system covers every case.
- **"Is that real data or a mock?"** New, and you will get it now that round one shows the plumbing. Answer with what is true on the day. If Salesforce seeding landed, say the data lives in Salesforce and show the connection. If the fallback shipped, say it is a Workato Data Table, show the table, and edit a row live. Do not blur the two.

---

## Backup plan

- **If the live MCP investigation stalls or returns unexpected results:** cut to a recorded run of the Investigate beat, and say plainly that you are switching.
- **If the live AIRO build fails or times out:** show a pre-built Recipe and Genie as "already built" and narrate what AIRO would have done, rather than debugging live.
- **If the human-in-the-loop simulation misbehaves:** show the three pre-captured test-run results (approve, reject, modify) pulled through Dev API MCP.
- **If round one's build fails live:** this is the new risk this version introduces. Have a second, already-built skill ready to switch to, and keep the test-and-inspect half of the beat, which is the half that carries the argument.
- **If Salesforce is unreachable on the day:** fall back to the Data Table version of the skills. Build both if P2 finishes early enough. Say which one you are showing.

---

## Open items / risks

- [ ] **Wire up a preview Dev API MCP.** Blocks the round-one job-log beat and the whole Control Plane argument. If it can't be done, the workspace decision reopens.
- [ ] **Seed Salesforce with the BRH-2240 storyline** (P2), preserving every invariant. Largest piece of work in this plan.
- [ ] **Rebuild the 8 skills against Salesforce** (P3), keeping tool names and schemas stable.
- [ ] **Rebuild the Genie** against folder 578470 and re-run the headless smoke test.
- [ ] Decide the Data Table fallback go/no-go by the rehearsal date, not on the day.
- [ ] Co-speaker: name, CAB check, travel booked early.
- [ ] Decide live-build versus recorded fallback per beat, not just overall.
- [ ] Timing is 46 minutes as written. Trim one from the opening after a rehearsal.
- [ ] Confirm with Ee Liang Sim: is this Segment 7, or deliberately separate from it?

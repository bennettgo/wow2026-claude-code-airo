# Use Case Ideation

## What makes a use case ready to build

Three checks. A use case is ready only when all three pass.

**1. The trigger sentence is obvious.** One natural language sentence causes the app to fire without ambiguity. "Troubleshoot this device issue." "Find me espresso machines under $200." If you need two sentences to set it up, the use case needs more shaping.

**2. There is a demo moment.** Something that cannot be explained, only shown. Dynamic filters that reshape per product category. Videos surfaced by device serial number. A support ticket opened from a single chat message. The demo moment is what gets remembered after the session ends. If you cannot name it, the use case is not ready.

**3. Workato is genuinely in the middle.** The data the app needs lives somewhere — a CRM, a product catalog, a third-party API, an internal database. Workato connects it. This makes the app a real automation demo, not just a pretty UI. If the same thing could be built without Workato, pick a different use case.

---

## Demo diversity principle

A portfolio of all "browse, filter, book" apps reads as depth in one pattern. Deliberately choose builds from different functions and interaction types.

| Interaction type | Example build | Key pattern |
|---|---|---|
| Triage / support | Device Troubleshooter | Media embed (YouTube) + diagnostic flow |
| Commerce / discovery | Retail Shopping Assistant | Dynamic filters via API metadata (no hardcoding) |
| Scheduling / coordination | Corporate Event Planner | Natural language → structured venue options |
| Data prep / briefing | Advisor Meeting Prep | Multi-source data aggregation into one card |
| Fault triage | Equipment Fault Triage | Error code → parts + work order |
| Multi-system launch | Onboarding Launcher | Single trigger → parallel system updates |

The goal is range across interaction types, not depth in one pattern.

---

## Build pipeline (ranked by effort)

| Use case | Audience / vertical | Demo moment | Effort |
|---|---|---|---|
| Corporate event planner | Events / ops teams | Describe event → venue options + quote | Low |
| Wealth advisor meeting prep | Financial services | "Call in 20 min" → portfolio + life events + talking points | Medium |
| Equipment fault triage | Manufacturing / field ops | Error code → parts list + technician + work order | Medium |
| Employee onboarding launcher | HR / people ops | One sentence → multiple systems updated simultaneously | Medium |
| Contract review | Legal / RevOps | Upload PDF → flagged clauses + risk levels | High |
| Clinical decision support | Healthcare | Patient symptom → drug interactions + guidelines | High |

**Recommended starting build if you are new to MCP Apps:** Corporate events or a device troubleshooter. Both have simple data layers, clear trigger sentences, and a demo moment that is immediately legible to any audience.

---

## Use case to value story mapping

Match the use case to what makes the demo land for your audience.

| Audience / vertical | Value story |
|---|---|
| Sales / revenue teams | "Your reps get deal context and next-step recommendations without leaving the conversation." |
| Customer support | "First-contact resolution without switching tabs. The agent never opened a browser." |
| HR / people ops | "Onboarding across multiple systems in one sentence. No manual handoffs between tools." |
| Finance / RevOps | "Contract review that flagged the renewal clause in 10 seconds instead of 45 minutes." |
| Field operations / manufacturing | "The technician said the error code. Got the parts list and work order on the spot." |

The best use case is one where the audience immediately thinks "we could use that today."

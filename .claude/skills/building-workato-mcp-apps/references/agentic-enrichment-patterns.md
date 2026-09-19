# Agentic Enrichment Patterns

Use when your MCP App needs to enrich raw data with LLM judgment — scoring, summarizing, classifying, or triaging items before showing them to the user. The Jira inbox app shipped this pattern end-to-end: 25-50 issues per call, each scored 0-10 with a one-line reason by gpt-4o-mini.

This whole capability was the single most expensive thing to debug in the original build, so the patterns below are the field-tested versions, not aspirational ones.

---

## The shape

A recipe that does per-item LLM enrichment looks like this:

```
1. trigger (workato_skill.start_workflow)
2. data source (Jira / Salesforce / API call) — returns array
3. declare_list (empty enriched_items)
4. foreach over the array
   5. error_handling wrapper
     6. LLM call (open_ai.chat_completion or workato_genie.assign_task_to_genie)
     7. parse_json_v2 of the LLM response (if not using structured_output)
     8. insert_to_list to enriched_items
   9. (catch) — fallback path
     10. insert_to_list with deterministic fallback score
11. workflow_return_result with enriched_items
```

Critical pieces explained below.

---

## Deterministic facts in Ruby, judgment in the LLM

LLMs are bad at date arithmetic, sorting, deduplication, and any task that requires precise calculation. They are good at applying soft judgment to facts already given to them. Always:

- **Compute precise facts in the recipe** before calling the LLM
- **Embed those facts explicitly** in the prompt as labeled values
- **Ask the LLM only for the judgment**

The classic mistake: passing a raw ISO timestamp and asking the LLM to determine whether it's "stale". The model will hallucinate ("recently updated") on items it was just told are weeks old. Fix:

```ruby
# In step 6's message field — compute days_since_updated in Ruby, embed in prompt
"Days since updated: " + ((now.to_i - bindings.foreach_4_fields_updated.to_i) / 86400).to_s
```

Then in the prompt:

```
HARD RULE: If days_since_updated > 30 AND not Security Bug AND not PSM(7d),
score MUST be ≤ 4 regardless of priority.
```

Without the explicit `days_since_updated` integer, the model just rubber-stamps based on priority.

---

## Banded scoring rubric

Open-ended "score this 0-10" prompts produce flat distributions — every item lands at 7-8 because the model lacks anchoring. Use a banded rubric:

```
DEFAULT BASE BY RECENCY:
- <=7 days: base 7
- 8-14 days: base 6
- 15-30 days: base 5
- >30 days: base 3 (capped at 4 unless Security Bug or PSM updated <=7d)

ADJUSTMENTS (add to base, final 0-10):
- Security Bug: +2
- Highest priority: +1
- PSM project OR labels contain 'customer': +1
- In Progress: +1
- assignee empty AND not security/PSM: -1

HARD RULES:
- days > 30 AND not Security/PSM(7d): final score <= 4
- 9-10 only if Security Bug OR (Highest + <=7d + customer/PSM signal)
```

The base+adjustment structure makes the model do arithmetic against named criteria rather than vibes. Score distribution spreads across 3-10 instead of clustering at 7-8.

**Anchor band on the most deterministic input.** Days-since-updated is a strong anchor because the recipe computes it precisely. Priority alone is a bad anchor — every "High" item collapses to one score.

---

## Reason format constraints

Without a constraint, models produce templated reasons: "high priority and recently updated, indicating ongoing relevance" — verbatim across dozens of items. Force specificity:

```
Reason format: cite the days_since_updated number AND name the strongest
applied adjustment. Generic reasons (e.g., "high priority + recently updated")
will be rejected.
```

In practice this turns "high priority and recently updated" into "5 days old, In Progress, applied +1 in-progress" — which is actually useful in the UI.

---

## Skip the LLM for unambiguous cases (latency optimization)

The single biggest source of slowness: sequential foreach × LLM call × N items. At 700-1500ms per call, 30 items pushes 30-45 seconds total — past MCP client timeout.

The fix: only call the LLM for the borderline middle band. Use Ruby ternaries for the unambiguous cases:

```ruby
# Pseudocode for an "auto-score" step before the LLM call
auto_score = ruby("
  (bindings.issuetype == 'Security Bug') ? 9 :
  (bindings.days > 60) ? 3 :
  (bindings.priority == 'Highest' && bindings.days <= 3) ? 8 :
  nil
")

# Inside the foreach, if auto_score is set, skip LLM and insert directly.
# Otherwise call LLM for the borderline 4-30 day range.
```

This typically eliminates 60-80% of LLM calls. A 30-item inbox at 100% LLM coverage takes 30s+; the same inbox at 25% LLM coverage takes 7s.

Wire it with `if/elsif/else` blocks in the recipe — the recipe pulls `auto_score` first, branches on whether it's nil, and only enters the LLM path on the nil branch.

---

## Error handling fallback (must-have)

A single bad LLM call (rate limit, parse error, timeout) shouldn't kill the whole batch. Wrap the LLM call in `error_handling`:

```python
for monitor in WorkatoMonitor(retries=0, sleep=2):
  try:
    # LLM call + parse + insert
    chat_completion = open_ai.chat_completion(...)
    parsed = json_parser.parse_json_v2(...)
    insert_to_list(item_with_agent_score)
  except WorkatoError:
    # Fallback: priority-based deterministic score
    insert_to_list(item_with_fallback_score=ruby(
      "(bindings.issuetype == 'Security Bug') ? 9 : " +
      "(bindings.priority == 'Highest') ? 7 : " +
      "(bindings.priority == 'High') ? 5 : 4"
    ))
```

The user gets a populated inbox either way. Failed items are visible (flagReason or score-source field) so you can debug post-hoc.

---

## Output schema — typed fields, not strings

Declare `agentScore` (integer) and `agentReason` (string) as optional fields in the trigger's `result_schema_json`. Optional matters: the fallback path may skip them on some items.

```json
{"name":"agentScore","type":"integer","optional":true,"hint":"LLM-assigned 0-10 importance score"},
{"name":"agentReason","type":"string","optional":true,"hint":"One-line LLM reason"}
```

This lets the MCP App's HTML render badges + reason lines unconditionally — missing values just don't render.

**Client-side filtering** of low scores (e.g., score < 6) typically belongs in the HTML, not the recipe. Workato's Python DSL silently strips `if` clauses from list comprehensions in `workflow_return_result.result`, so server-side filtering of the array doesn't work. Filter in JS:

```js
const visible = inboxItems.filter(i => {
  const n = Number(i.agentScore);
  if (!Number.isFinite(n)) return true; // fallback items still shown
  return n >= 6;
});
```

---

## LLM connector choices

In Workato as of mid-2026:

| Connector | Status | Notes |
|---|---|---|
| `open_ai.chat_completion` | **Reliable** | Use `gpt-4o-mini`, max_tokens ~150, temperature 0. Standard JSON parsing path works. |
| `anthropic.*` (custom connector) | Intermittent | Backed by a Ruby SDK validation service that has been seen returning ECONNREFUSED. Picklist/field validation may fail at setup time even if the API itself is healthy. |
| `workato_genie.assign_task_to_genie` | **Cleanest pattern** | Use with `structured_output` — typed return, no parse_json step. Cleaner if you want named sub-agents. Heavier model cost depending on Genie config. |

Default to OpenAI `gpt-4o-mini` for scoring/triage tasks. Switch to `assign_task_to_genie` with `structured_output` when you want a reusable named scorer or richer judgment.

---

## Cost and latency

For a 25-item inbox with gpt-4o-mini at temperature 0:

- **Tokens**: ~600 input + ~50 output per item → ~16k total per inbox load
- **Cost**: ~$0.00012 per item → ~$0.003 per inbox load
- **Latency**: ~700-1500ms per item × N items → see foreach concurrency note

Sequential foreach is the latency killer. If Workato supports `repeat_mode: "parallel"` on your foreach, set it — drops 25× sequential calls to ~3-5 concurrent batches. If parallel isn't available, fall back to the "skip unambiguous" trick above.

---

## Don't compute aggregates in Ruby

Several useful patterns are blocked by Workato's Ruby formula validator:

- `.map { |i| ... }` — blocked
- `.uniq` — blocked on strings (only on arrays)
- `.count`, `.select` — blocked
- `Date.parse`, `Time.parse`, `iso8601` — blocked
- Multi-statement (assignment + use) — blocked

If you need to compute per-batch aggregates (group counts, unique sets, sorted lists), do it client-side in the HTML JavaScript, not in the recipe. The Jira inbox's `byDomain` counts came from JS, not Ruby, after multiple Ruby attempts failed validator.

Allowed Ruby string/array methods that get heavy use here:

- `.to_s`, `.to_i`, `.strip`, `.downcase`, `.upcase`
- `.include?`, `.split`, `.join`, `.gsub`
- `.blank?`, `.present?`
- Single-expression ternaries (no `;` allowed; nest ternaries for branching)
- Basic arithmetic on `now.to_i` and `.to_i` of timestamps

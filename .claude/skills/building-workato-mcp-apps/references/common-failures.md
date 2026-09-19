# Common Failures

Symptom-first diagnostic guide. Find the symptom, work through the checks in order.

---

## App not firing at all

The LLM does not call the trigger tool, or calls it and nothing renders.

**Check the tool description first.** The LLM reads this to decide when to call. If it reads like a capability label ("Searches for products") rather than a trigger condition, the LLM may not match it to the user's phrasing.

Fix: rewrite as an explicit trigger condition — "Call this when the user asks to search for, browse, or find products by name, category, or description." Test by restating the trigger sentence and verifying Claude calls the tool.

**Check the recipe is running.** The MCP server tool must be linked to an active, running recipe. If the recipe was paused or never started, the tool call fails silently or returns an error.

**Check the MCP app is linked to the correct MCP server.** AI Hub > MCP Apps > [app] > Servers tab.

**Check tool name casing.** The tool name in the MCP server config and in `app.callTool()` must match exactly, character for character.

---

## External scripts fail to load / app renders blank

Tailwind styles not applying. SDK not loading. Images missing. App frame appears but content is empty.

**Almost always a CSP issue.** Every external domain must be in all four CSP fields: Connect domains, Resource domains, Frame domains, Base URI domains.

Common misses:
- `cdn.jsdelivr.net` not in Resource domains — Tailwind and SDK fail to load
- Image CDN not in any field — product images 404 silently
- YouTube domains missing — video thumbnails do not load

Fix: AI Hub > MCP Apps > [app] > Settings > Content Security Policy. Add the missing domain to all four fields. Save and reload.

---

## Tool call returns nothing or wrong shape

Tool fires, app receives a response, but the data is not what the code expects.

**Check Workato envelope parsing.** Two wrapping layers, both easy to miss.

```javascript
// Wrong — raw is the wrapper object, not your data
const items = raw.items;        // undefined

// Right — handles both MCP envelope shapes AND the Skill {result: ...} wrapper
let parsed = raw?.structuredContent;
if (!parsed) {
  const text = raw?.content?.[0]?.text;
  parsed = text ? JSON.parse(text) : raw;
}
const result = parsed?.result ?? parsed;  // Skills wrap; API recipes don't
const items = result.items;     // correct
```

Layer 1 — **MCP envelope**: data is on `raw.structuredContent` (typed) or `raw.content[0].text` (JSON string). Newer servers populate both.

Layer 2 — **Workato Skill wrapper**: `workflow_return_result` adds a `{result: ...}` layer. API recipes return the payload directly. The `parsed?.result ?? parsed` line normalizes both.

**Check the SDK method name.** `app.callTool(name, params)` does NOT exist in ext-apps 1.3.x. Use `app.callServerTool({ name, arguments: params })`. If the iframe error says "app.callTool is not a function", you have stale scaffold syntax.

**Check job history in Workato.** Go to the recipe > Jobs. Find the most recent job triggered by the tool call. If the job failed, the error message is there.

**Check the tool I/O schema.** AI Hub > MCP Apps > [app] > Tool inputs and outputs. This shows the actual contract between the app and the recipe. If the app expects `items[]` but the recipe returns `results[]`, that's the mismatch.

---

## HTML not persisting after save

HTML is pasted into the MCP app config, saved, but on reload the field is empty or a 404 from Workato's file storage endpoint appears.

**Confirmed as content-specific, not platform-wide.** A minimal HTML string saves correctly. Something in the specific content causes the save to fail.

**Suspected causes (not fully confirmed):**
- `document.execCommand('copy')` inside inline `onclick` attributes — the config parser may reject this
- Unicode box-drawing characters in JavaScript template literals — may cause encoding errors

**Workaround approach:**
1. Remove any `document.execCommand` calls from inline `onclick`. Move to named functions: `onclick="handleCopy()"` with the function defined in the script block.
2. Replace any Unicode box-drawing characters (`=`, `|`, `+`, and similar) in JS strings with plain ASCII or HTML entities.
3. Save a stripped-down version first to confirm the platform is healthy, then re-add features incrementally to isolate what causes the failure.

---

## App fires but renders blank

The trigger works, the iframe appears, but nothing renders inside it.

**Check `app.connect()` is awaited.** If the app attempts to render before the SDK connection resolves, it fails silently.

```javascript
// Wrong
app.connect();   // not awaited
renderUI();      // runs before SDK is ready — silent failure

// Right
await app.connect();
renderUI();      // safe
```

**Check `app.ontoolresult = () => {};` is set** before `app.connect()`. Missing this causes the SDK to intercept tool results in a way that can conflict with the app's rendering logic.

**Check the browser console.** Open DevTools > Console while the MCP app iframe is active. JS errors surface there.

---

## "Function 'X' is not supported" in a Ruby formula

`recipe_copilot_set_input_field` fails with something like *"Formula validation failed: unknown_function: Function 'map' is not supported"* (or `iso8601`, `to_datetime`, etc.).

**Cause:** Workato's Ruby formula evaluator runs a restricted subset of Ruby. Many common Array/Date methods are not whitelisted. The whitelist is opaque from the outside, but here's the confirmed surface after several builds:

**Confirmed-blocked:**
- Array iteration: `.map`, `.select`, `.uniq` (on strings, not arrays), `.count` (with block)
- Date parsing: `Date.parse`, `Time.parse`, `iso8601`, `to_datetime`
- State: assignments / multi-statement (`x = ...; ...`) — Workato formulas are single-expression only
- `.empty?` (use `.blank?` or `.present?` instead)

**Confirmed-allowed (heavy use in shipping recipes):**
- String methods: `.to_s`, `.strip`, `.downcase`, `.upcase`, `.gsub`, `.split`, `.include?`
- Array methods (limited): `.join`, `.first`, `.last`, `[index]` access
- Truthiness: `.blank?`, `.present?`
- Date / time: `now`, `now.utc`, `now.to_i`, `now.utc.strftime('%Y-%m-%d')`, `<datapill>.to_i` (epoch when datapill is a Time/DateTime)
- Conditionals: nested ternaries (`a ? b : c`) — required since `;` and assignments are blocked
- Hash access: `bindings['key']`, `bindings.key_name`

**Workaround patterns:**
- For aggregates over an array (uniq, count, group-by), **don't compute them in the recipe.** Push the raw array down to the iframe and let the HTML compute. See `html-scaffold-patterns.md` → Server-side vs client-side filter derivation. Eliminates the entire class of "ruby method not allowed" bugs.
- For timestamps, use `ruby("now.utc", bindings={})` (works) rather than `ruby("now.utc.iso8601", ...)` (blocked).
- For days-since-update math: `ruby("((now.to_i - bindings.updated.to_i) / 86400).to_s")` works if the datapill is delivered as a Time/DateTime. Eyeball the first job — if the rendered value in the LLM prompt is suspiciously huge (~21,000), the datapill was a raw ISO string and `.to_i` returned the leading year; you'll need substring-based parsing.
- For per-element mapping inside a return_result, use Python DSL list-comprehension syntax (`[{...} for item in source]`) instead of Ruby `.map` — that's a recipe DSL pattern, not a Ruby formula.
- For Python DSL list comprehensions with conditional filtering: **Workato silently strips `if` clauses**, so `[x for x in src if x['score'] >= 6]` ships as `[x for x in src]` with no filter. Apply filters client-side in the HTML.
- For multi-step computation: chain ternaries into a single expression, or wrap in `error_handling` blocks that contain multiple linear steps.

**Don't** try to wrestle the validator into accepting more. The restricted set is narrow enough that simpler recipe + smarter HTML is usually faster than working around the formula limits.

---

## Tool description changes don't reach the LLM

You edited the trigger step's `description` field (or the AI Hub > MCP Servers > [tool] inline description) but Claude still behaves as if it read the old description.

**Cause:** the MCP server exposes the **recipe-level** description as the tool description, not the trigger step's `description` field. These are two different fields in Workato; only the recipe-level one is wired to MCP.

**Fix:** edit the description on the recipe asset itself. Either:
- In the Workato UI: open the recipe → top → Description field (the one next to the recipe name, not the one inside the trigger step)
- Programmatically: `recipe_copilot_update_asset_metadata(asset_type="recipe", asset_id=<recipe_id>, description="...")`

**Verify with `mcp_server_get`** — the Description column in the Tools table is what Claude sees. If it shows the old text, your update went to the wrong field.

---

## "Can't modify running recipe" when pushing edits

`recipe_copilot_push` or `recipe_copilot_update_asset_metadata` fails with `{'running': ["can't modify running recipe"]}` even for trivial metadata-only changes.

**Cause:** Workato locks running recipes against any modification.

**Fix:** stop the recipe → push the edit → restart. Two ways:

1. **Programmatic via Dev API** (preferred — no UI round-trip):
   ```
   curl -X PUT "https://www.workato.com/api/recipes/<id>/stop" -H "Authorization: Bearer <dev-api-token>"
   # ...push edits via Airo MCP...
   curl -X PUT "https://www.workato.com/api/recipes/<id>/start" -H "Authorization: Bearer <dev-api-token>"
   ```
   This is the canonical workaround until the Airo MCP exposes `recipe_start` / `recipe_stop`. One Dev API token gets you the full stop → push → start cycle from a single subagent or session.

2. **Manual UI:** stop in Workato → push → restart. Slower but no token needed.

For pure UI fixes (renaming, description text typos), it's often fastest to skip the MCP entirely and edit in Workato directly.

---

## Claude Code's `claude mcp add` connector keeps failing auth

You add the Workato MCP URL via `claude mcp add ... --transport http "<url>"`. The connector registers but every reconnect rejects credentials. `/mcp` reports *"Got new credentials, but <name> rejected them on reconnect"*.

**Cause:** Workato's MCP endpoint speaks **SSE / streamable-HTTP**, not plain HTTP request/response. Claude Code's `--transport http` uses request-response semantics; Workato responds with the wrong wire shape and the client drops auth.

**Fix:** add with `--transport sse` instead.

```
claude mcp remove jira-issues-live
claude mcp add jira-issues-live --transport sse "<url>"
```

If `sse` doesn't work on your Claude Code version, try `--transport streamable-http`. Both speak the same wire format.

---

## VUA Required tools fail when the MCP URL contains a token

You add `VUA Required: Yes` to one or more tools (e.g., mutation tools — `Update_Status`, `Add_Comment`). Calls to those specific tools fail or behave inconsistently while non-VUA tools on the same server keep working.

**Cause:** VUA (Verifiable User Agent) tools require **Workato Identity OAuth** for auth — they reject the static `wkt_token` query-param embedded in the server URL. The `wkt_token` is a bypass token for non-VUA tools and is ignored (or rejected) by VUA-enforced ones.

**Fix:** when any tool on the server has `VUA Required: Yes`, distribute the MCP URL **without the `?wkt_token=...` query param**. Clients then authenticate via Workato Identity OAuth on first connection (browser flow). Non-VUA tools on the same server still work — they just authenticate the same OAuth identity.

**Watch out when re-attaching tools in the UI**: the form defaults `VUA Required` differently depending on tool type. Tools added via *Skill* picker may auto-default to Yes. Check the column in `mcp_server_get` output after the save.

---

## MCP call times out / "skill failed" but the recipe job is still pending

User reports the tool call failed. Recipe job log shows the job is still `pending` with no `completed_at` time, often minutes after start.

**Cause:** MCP clients (Claude Desktop, Claude.ai) typically time out tool calls at ~30 seconds. Long-running recipes — especially per-item LLM foreach loops — exceed that easily. From the client's POV: failed. From Workato's POV: still grinding.

**Quick diagnostic:** `job_list` for the recipe; check `completed_at` and runtime on the last few jobs. Anything >20s is at risk.

**Fixes, in order of impact:**
- **Skip the LLM for unambiguous cases.** See `agentic-enrichment-patterns.md` → "Skip the LLM for unambiguous cases". Typical recipe goes from 30s+ to <10s.
- **Tighten JQL or upstream filtering** to reduce the candidate set the foreach iterates over.
- **Batch LLM calls.** One call with N items in the prompt + array response. Eats prompt complexity but cuts overhead massively.
- **Parallel foreach.** If your Workato workspace supports `repeat_mode: "parallel"`, set it. Sequential is the default and the killer.

If the user keeps timing out: the inbox flow is the most-impacted because it's per-item-LLM by design. The simple list/search flows shouldn't hit this.

---

## Fullscreen button does nothing inside the MCP App iframe

You add a "fullscreen" button calling `requestFullscreen()`. It fails silently or throws "permission denied" in console.

**Cause:** MCP Apps run inside iframes the host (Claude.ai / Claude Desktop) creates. Browsers block `requestFullscreen()` in iframes unless the host sets `allow="fullscreen"` (Permissions Policy) on the iframe. The MCP Apps spec's `permissions` field exposes camera, microphone, geolocation, clipboardWrite — but **NOT fullscreen**. Hosts won't grant it.

**Fix:** use an in-iframe expand pattern instead — toggle `max-height: 600px` ↔ `max-height: 100vh` on the app root. The iframe still bounded by the host chat panel, but the content stretches to use whatever vertical space the host gives. See `html-scaffold-patterns.md` → Expand pattern.

---

## Multiple MCP Apps registered against one MCP server — UI is inconsistent

When the MCP App was created (or re-created per-tool), the server now has multiple `ui://` resources, each potentially with different HTML. The UI rendered by Claude depends on which tool fired.

**Diagnostic:** call `ListMcpResourcesTool` on the server. If you see multiple `ui://` resources (e.g., `app-for-get-inbox-...`, `app-for-search-issues-...`, `new-app-...`), this is the situation.

**Why it happens:** in AI Hub, creating an MCP App linked to a specific tool spawns a new `ui://` resource. Repeatedly creating MCP Apps (one per tool) without linking them all to the same HTML produces drift.

**Fixes:**
- **Sync** — paste the same canonical HTML into all of them. Tedious; do via `ReadMcpResourceTool` to verify each.
- **Consolidate** — delete extras and have all tools route to one MCP App. Cleanest, but losing the per-tool app may break per-tool routing depending on Workato config.
- **Be deliberate at create time** — when first creating MCP Apps, attach all tools that should render the same UI to a single MCP App rather than creating a per-tool app.

---

## Iframe shows old HTML after a re-paste

Symptom: you paste an updated HTML into AI Hub > MCP Apps > App Code, save, hard-reload the Claude tab — but the iframe still renders the previous version. Same error message persists.

**Cause: Claude.ai loads the MCP App HTML once per chat and pins it.** Hard-reloading the browser tab does not refresh the iframe in an existing chat — it still shows the resource version that was current at the time of the original tool call.

**Fix: start a brand-new chat.** A fresh chat triggers a fresh `ui://` resource fetch.

**To verify which version is live** before testing in Claude: read the resource directly. If you're using Claude Code with the MCP server connected, `ReadMcpResourceTool` against the `ui://<view-id>` URI returns the current HTML. Otherwise, hit the resource via curl using the MCP server URL.

**Hard reset if even a new chat shows the old HTML**: detach + reattach the tool from the MCP server in AI Hub. This regenerates the `ui://` resource URI, bypassing any host-side cache keyed on it.

**Add a visible version marker during iteration.** Something like `<span>v3-PATCH</span>` in the header — bump it on every paste. You'll know at a glance whether you're looking at the latest deploy.

---

## Import package errors in Workato

"Duplicate in different folder" error when importing a recipe package.

Fix: go to Workato > Home > [folder where the duplicate connection lives] and delete it. Then re-import the package, or choose Overwrite during import.

---

## Known patterns and platform limitations

**HTML persistence is content-sensitive.** The MCP App config's HTML field can reject certain content without a clear error — the field appears to save but reloads empty, or a file storage 404 surfaces. This is content-specific, not a platform-wide failure. Confirmed triggers include `document.execCommand('copy')` inside inline `onclick` attributes and Unicode box-drawing characters in JavaScript template literals. Workaround: move any `document.execCommand` calls to named functions in the script block, replace non-ASCII characters in JS strings with plain equivalents, and use the incremental test approach described in the "HTML not persisting" section above.

**Third-party API portals can block or throttle during early dev.** Developer portals (OAuth approval queues, rate limit tiers, portal-level verification steps) can reject requests without surfacing a clear error at the API level. This is why mock-first is mandatory — a Workato Data Table fallback lets the build proceed regardless of external API status. When the real API unblocks, swapping it in is a single recipe change.

**No native MCP server clone.** Workato AI Hub has no duplicate or clone feature for MCP servers. Replication is manual: AI Hub > MCP Servers > Create, rebuild all tool definitions from scratch.

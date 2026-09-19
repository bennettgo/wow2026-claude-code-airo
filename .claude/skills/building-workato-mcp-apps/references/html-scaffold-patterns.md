# HTML Scaffold Patterns

Supplementary patterns for building MCP App HTML. Use alongside `assets/html-scaffold-template.html`.

---

## CSP domain reference

In AI Hub > MCP Apps > [app] > Settings > Content Security Policy, add every external domain to **all four fields**: Connect domains, Resource domains, Frame domains, Base URI domains.

Common entries for every build:
```
https://cdn.jsdelivr.net
```

Additional entries by use case:
```
# YouTube embeds
https://www.youtube.com
https://img.youtube.com

# Google Fonts
https://fonts.googleapis.com
https://fonts.gstatic.com

# Image CDNs — add the specific domain your app loads images from
# Example: https://i.ebayimg.com for eBay, https://images.unsplash.com for stock photos
# The domain must match exactly — check your browser's Network tab if images 404 silently
```

The SDK and Tailwind both come from `cdn.jsdelivr.net`. This is the most commonly missed entry on the first build.

---

## Server-side vs client-side filter derivation

Two valid places to compute `filterMetadata` (the set of filter groups + values shown in the sidebar). Choose based on what the filters *represent*.

**Client-side (derive in the HTML).** Build filterMetadata from `items[]` itself:

```javascript
function deriveFilterMetadata(items) {
  const groups = [
    { name: 'Status', field: 'status' },
    { name: 'Priority', field: 'priority' },
    { name: 'Project', field: 'project' },
    { name: 'Issue type', field: 'issueType' }
  ];
  return groups.map(g => ({
    name: g.name,
    values: Array.from(new Set(items.map(i => i[g.field]).filter(Boolean)))
  })).filter(g => g.values.length > 0);
}
```

Then in your loader: `if (currentFilterMetadata.length === 0) currentFilterMetadata = deriveFilterMetadata(allIssues);`

**Pros**:
- No Workato Ruby formula gymnastics. Workato's formula validator rejects `.map`, `.uniq` on strings, `iso8601`, and other surprisingly common methods — building aggregates server-side is a recurring source of `Function 'X' is not supported` errors.
- Filters always match what's actually visible. No empty options.
- Adapts to any backend output without recipe changes.
- Recipe stays trivial — just returns `items[]` + `totalCount`.

**Cons**:
- Filter options reflect only the current result set. If you queried only Bugs, you'd never see the other issue-type options.
- Loses ability to surface global filter universes (e.g., all possible statuses to transition to, not just ones currently visible).

**Server-side (recipe returns filterMetadata).** Use when:
- The filter universe is bigger than the visible items (e.g., transitionable-to statuses include ones no current issue has)
- The recipe has business logic about which filters should appear (role-based, context-based)
- You're working with a backend that has a separate "facets" endpoint already returning aggregates

**Recommended pattern**: support both. Render server-supplied filterMetadata if present; fall back to client-side derivation if empty:

```javascript
currentFilterMetadata = normalizeFilterMetadata(data.filterMetadata);
if (currentFilterMetadata.length === 0) {
  currentFilterMetadata = deriveFilterMetadata(allIssues);
}
```

The recipe can return `filterMetadata: []` to opt into client derivation explicitly.

---

## Dynamic filter pattern

For apps with category-aware filters: do not hardcode filter sets per category. Let the data source return which filters are relevant for each result set. This keeps filter logic in Workato where it belongs and means the UI adapts automatically to whatever the query returns.

**The principle:** your Workato recipe returns two things — the result items and a list of filter groups (each with a name and a set of allowed values). The app renders those filter groups dynamically. When the user changes a filter, the app re-calls the tool with updated parameters rather than filtering client-side.

**Recipe output shape (adapt field names to your data source):**
```json
{
  "items": [...],
  "filterMetadata": [
    {
      "name": "Category",
      "values": ["Electronics", "Clothing", "Home & Garden"]
    },
    {
      "name": "Price range",
      "values": ["Under $25", "$25–$100", "Over $100"]
    }
  ]
}
```

**App-side implementation:**
```javascript
// Module-level state — declare these before app.connect()
let currentQuery = '';
let activeFilters = {};

// Call this after each tool result to render the filter sidebar.
// filterMetadata is the array from your recipe response.
// Adapt field names (filter.name, filter.values) to match your recipe output schema.
function renderFilters(filterMetadata) {
  const container = document.getElementById('filters');
  if (!filterMetadata || filterMetadata.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = filterMetadata.map(filter =>
    '<div class="filter-group mb-3">' +
      '<label class="font-medium text-sm mb-1 block">' + filter.name + '</label>' +
      filter.values.map(v =>
        '<label class="flex items-center gap-2 text-sm">' +
          // Use data attributes to pass values — avoids string quoting issues in inline handlers
          '<input type="checkbox" value="' + v + '" ' +
            'data-filter-name="' + filter.name + '" ' +
            'data-filter-value="' + v + '" ' +
            'onchange="handleFilterChange(this)">' +
          v +
        '</label>'
      ).join('') +
    '</div>'
  ).join('');
}

// Reads filter identity from data attributes rather than inline args
function handleFilterChange(el) {
  applyFilter(el.dataset.filterName, el.dataset.filterValue, el.checked);
}

// Re-fetches from Workato when filters change — keeps filtering logic server-side
async function applyFilter(filterName, value, checked) {
  if (checked) {
    activeFilters[filterName] = activeFilters[filterName] || [];
    activeFilters[filterName].push(value);
  } else {
    activeFilters[filterName] = (activeFilters[filterName] || []).filter(v => v !== value);
  }
  // Adapt tool name and parameter names to match your recipe
  const data = await callTool('your_search_tool', { query: currentQuery, filters: activeFilters });
  renderResults(data.items);
  renderFilters(data.filterMetadata);
}
```
---

## Multi-tool pattern (list → detail → mutate)

A common shape: the trigger tool returns a list, the app opens a detail modal on click, and the detail modal can mutate state (status, comments, etc.). Each interaction is a separate tool call back to the same MCP server.

**Tool name constants.** Declare one per tool, all near the top of the script. Verify each slug in AI Hub > MCP Apps > Tool inputs and outputs before testing.

```javascript
const TOOL_LIST          = 'List_Things';
const TOOL_DETAILS       = 'Get_Thing_Details';
const TOOL_UPDATE_STATUS = 'Update_Thing_Status';
const TOOL_ADD_NOTE      = 'Add_Note';
```

**Mutations: optimistic UI with rollback.** Update local state and re-render immediately, then call the tool. If the tool fails, roll back the optimistic change so the UI never shows a state that doesn't exist on the server.

```javascript
window.handleStatusChange = async function(selectEl) {
  const newStatus = selectEl.value;
  const previousStatus = detailIssue.status;
  // 1. Optimistic update
  detailIssue.status = newStatus;
  const listItem = allIssues.find(i => i.key === detailIssue.key);
  if (listItem) listItem.status = newStatus;
  renderDetail();
  applyClientFilters();
  // 2. Server call
  try {
    const result = await callTool(TOOL_UPDATE_STATUS, { key: detailIssue.key, status: newStatus });
    if (!result || result.success === false) throw new Error(result?.message || 'Update failed');
  } catch (err) {
    // 3. Roll back on failure
    detailIssue.status = previousStatus;
    if (listItem) listItem.status = previousStatus;
    renderDetail();
    applyClientFilters();
    alert('Failed to update status: ' + err.message);
  }
};
```

**Detail modal: shared shell, swapping inner content.** Render the modal as `renderModalShell(innerHtml)` with a fixed header (title + close button) and a body that you fill with the per-state content. Keeps loading, error, and loaded states consistent.

```javascript
function renderModalShell(innerHtml) {
  return '<div id="detail-modal-backdrop" class="modal-overlay" onclick="handleModalBackdrop(event)">' +
    '<div class="modal-card" role="dialog" aria-modal="true">' +
      '<div class="modal-header">' +
        '<div class="modal-title">Issue details</div>' +
        '<button onclick="closeDetail()" class="modal-close">&times;</button>' +
      '</div>' +
      '<div class="modal-body">' + innerHtml + '</div>' +
    '</div>' +
  '</div>';
}
```

**Backdrop click should close — but only on the backdrop itself.** Without the guard, clicks anywhere inside the modal close it.

```javascript
window.handleModalBackdrop = function(event) {
  if (event.target.id === 'detail-modal-backdrop') closeDetail();
};
```

---

## Token-efficient tool design

The MCP App architecture lets you decouple **what the LLM sees** from **what the user sees**. Take advantage of it. The LLM should only see what it needs to make routing decisions; the rich payload that powers the UI should go straight to the iframe.

**The shape.** Split into two tools:

```
LLM-facing trigger:   Get_Jira_Issues          → { success: true, count: 8, hint: "see the app" }
App-facing data:      List_Issues_For_App      → { items: [...], filterMetadata, totalCount }
```

The LLM routes to `Get_Jira_Issues`, sees ~20 tokens, the iframe launches. The HTML then calls `List_Issues_For_App` from `app.connect()` to fetch its own data. Most of the payload never enters LLM context.

**Why this matters.** Token savings compound on every dimension that drives the data wider or deeper:
- Listings with descriptions, comments, attachments
- Pagination (LLM sees "20 of 1,500", iframe handles paging)
- Detail-on-click flows (each `Get_Issue_Details` call goes straight to the iframe)

On a typical Jira issues app, the LLM payload drops from ~2,000 tokens to ~20 — and the user sees exactly the same UI.

**Hard isolation via MCP Apps spec.** Mark the app-facing tool's `_meta.ui.visibility` so it doesn't appear in the LLM's tool list at all:

```json
{
  "name": "List_Issues_For_App",
  "description": "Used by the Jira Issues app to fetch its own data.",
  "_meta": {
    "ui": {
      "resourceUri": "ui://jira-view",
      "visibility": ["app"]
    }
  }
}
```

Per the MCP Apps spec: *Host MUST NOT include tools in the agent's tool list when their visibility does not include `"model"`*. The LLM literally can't call what it can't see. The iframe's `app.callServerTool()` still goes through because its call path is separate from `tools/list`.

**Description-based fallback.** Where `_meta.ui.visibility` isn't wired through end-to-end, fall back to description routing:
- LLM-facing trigger description: *"Returns Jira issues count and routes to the app. The app IS the response. Do not summarize."*
- App-facing tool description: *"Internal — used by the MCP App to fetch its own data. Don't call for direct user queries; use Get_Jira_Issues instead."*

Modern models respect this well in practice; the strict-enforcement version via `visibility` is the upgrade path.

**When NOT to split.** Small, single-purpose tools where the full payload IS the value to the LLM (e.g., a one-off lookup the user wants to discuss). The split adds an extra round-trip and two assets to maintain — only worth it when payload size or context cost justifies it.

---

## Keyboard ergonomics

MCP Apps inherit zero default keyboard behavior. Bake these into every interactive app — users expect them.

**Cards / list items that open detail views.** Make them focusable and respond to Enter/Space, not just click. Pure `<div onclick>` items don't get this for free.

```html
<div role="button" tabindex="0"
     data-issue-key="MCP-89"
     onclick="openDetail(this.dataset.issueKey)"
     onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openDetail(this.dataset.issueKey);}"
     class="focus:outline-none focus:ring-2 focus:ring-[#0052cc]">
  ...
</div>
```

**Textareas inside forms.** Default behavior is "Enter inserts a newline" — usually wrong for chat-like inputs (comment boxes, message inputs). Pattern: Enter submits, Shift+Enter for a newline. Also show the binding as a hint so users discover it.

```html
<form onsubmit="handleAddComment(event)">
  <textarea id="comment-input" required rows="2" placeholder="Add a comment..."
    onkeydown="if(event.key==='Enter' && !event.shiftKey){event.preventDefault(); handleAddComment(event);}">
  </textarea>
  <button type="submit">Comment</button>
  <div class="text-xs text-gray-400">Enter to send · Shift+Enter for newline</div>
</form>
```

**Esc closes any open modal.** Bind once at module load — covers every future modal without per-modal wiring.

```javascript
document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  const modal = document.getElementById('detail-modal');
  if (modal && !modal.classList.contains('hidden')) {
    event.preventDefault();
    closeDetail();
  }
});
```

**Plain text inputs** (`<input type="text">`) already submit-on-Enter inside a form, and don't insert newlines outside one. No special handling needed.

---

## Expand pattern (the substitute for fullscreen)

You can't use the browser fullscreen API in MCP App iframes — the host doesn't grant `allow="fullscreen"` (see `common-failures.md` → Fullscreen button). Instead, give the user a button that flips the app's `max-height` between a compact cap and `100vh`. The iframe is still bounded by whatever vertical space the host chat panel allows, but the content stretches to fill it.

```html
<button onclick="toggleExpand()" id="expand-btn" title="Expand to fill chat panel">
  <span id="expand-icon">⤢</span>
</button>
```

```css
#app { height: 600px; max-height: 600px; overflow: hidden; transition: max-height 0.18s ease, height 0.18s ease; }
#main-content { display: flex; flex-direction: column; max-height: 600px; height: 600px; transition: max-height 0.18s ease, height 0.18s ease; }
#app.expanded, #app.expanded #main-content { height: 100vh; max-height: 100vh; }
```

```javascript
window.toggleExpand = function() {
  const app = document.getElementById('app');
  const expanded = app.classList.toggle('expanded');
  const icon = document.getElementById('expand-icon');
  if (icon) icon.textContent = expanded ? '⤡' : '⤢';
  try { sessionStorage.setItem('app-expanded', expanded ? '1' : '0'); } catch (e) {}
};
// Restore on init:
try {
  if (sessionStorage.getItem('app-expanded') === '1') {
    document.getElementById('app').classList.add('expanded');
    const icon = document.getElementById('expand-icon');
    if (icon) icon.textContent = '⤡';
  }
} catch (e) {}
```

`sessionStorage` persistence makes the toggle sticky across re-renders within a chat session. Doesn't survive a new chat — that's by design (MCP App resource is re-fetched fresh).

---

## State persistence pattern (phase 2)

Add three tools to the MCP server, each wired to a Workato recipe:

```javascript
// Save state on any meaningful user action
async function saveState(key, stateData) {
  await callTool('save_session_state', {
    key: key,
    data: JSON.stringify(stateData)
  });
}

// Load state immediately after app.connect()
async function loadState(key) {
  const result = await callTool('load_session_state', { key: key });
  return result?.data ? JSON.parse(result.data) : null;
}

// Usage pattern on app init:
// await app.connect();
//
// Session identity: you need a stable identifier to key saved state to a user
// or session. Three approaches, from simplest to most robust:
//
// 1. Let the user provide it — an input field in the app UI (e.g. email or
//    employee ID). Simple, no SDK dependency, works for any app.
//
// 2. Generate a session ID on init — not stable across sessions, but fine for
//    short-lived state within a single conversation:
//    const sessionId = crypto.randomUUID();
//
// 3. Pass it via the trigger tool's input schema — requires verifying how your
//    version of the ext-apps SDK exposes trigger parameters before using this.
//    Check the SDK documentation at cdn.jsdelivr.net/npm/@modelcontextprotocol/ext-apps/
//    for the correct API before implementing.
//
// const saved = await loadState('user-session-' + sessionId);
// if (saved) restoreUI(saved);
// else renderDefaultUI();
```

State lives in Airtable or Postgres, keyed by user/session ID. This turns the app from stateless UI into a stateful Workato-backed system. It also makes for a strong demo moment: "watch what happens when I navigate away and come back."

---

## Production debug panel removal checklist

When removing the debug panel before production:

1. Delete the `#debug-panel` CSS block from `<style>`
2. Delete the `<div id="debug-panel"></div>` HTML element
3. Replace the `log(label, data)` function body with nothing: `function log() {}`
4. Search the file for: `debug-panel`, `.debug`, `#debug`, `log(` — verify no orphaned references remain
5. Check for any `@media` blocks that reference the removed class names
6. Confirm the file saves and persists in the MCP app config after cleanup

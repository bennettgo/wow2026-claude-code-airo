---
name: my-writing-style
description: >
  Bennett's writing style for documents, PRDs, Confluence pages, explainers, and any
  drafted prose. Apply whenever writing or revising content in Bennett's voice —
  PRDs, wiki pages, PM explainers, emails, announcements, notes, or docs. Covers tone
  (direct, no dramatic phrasing), structure (reality first, plain English second,
  analogies last), and formatting preferences. For Slack messages specifically, the
  slack-message-style skill takes precedence.
---

# Bennett's Writing Style

## Tone: direct, no drama

Bennett writes plainly and dislikes dramatic or clever phrasing. The test: would an engineer or identity admin read the sentence and learn something, or is it there for effect?

Cut on sight:

- Editorial flourish: "this is where the PRD earns its keep", "the one rule that explains most of the design", "that's the whole trick", "everything else follows from that"
- Grand openers and closers: "Think of X as...", "The three sentences to remember"
- Metaphor-heavy topic sentences; personification ("the badge printer")
- Intensifiers and hedges: "genuinely", "actually quite", "deeply", "critically important"
- Restating a point a second time in fancier words

Prefer:

- Lead with the fact. "The IDP issues tokens; Workato validates them." — not a build-up to it
- State positions as facts, once: "Workato is a resource server, not an authorization server."
- Short sentences. One idea per sentence or bullet
- Plain section headings ("Summary", not "The three sentences to remember")

## Structure for explaining technical concepts

Fixed order — do not lead with analogy:

1. **Reality first, in the practitioner's own terms.** Describe what actually exists the way the relevant expert (identity admin, engineer) would recognize it: real object names, real field names, real flows.
2. **Plain English second.** Short restatement of the same objects for a non-technical reader.
3. **Analogy last, brief, optional.** One compact paragraph, clearly marked as an aid ("The analogy, if useful"). Never the organizing frame of the document.

## Document conventions

- Short intro line stating audience and reading time, then straight into content. No "in this document we will..."
- Tables wherever they compress: field lists, mappings, comparisons. Notes column stays terse
- Worked examples with concrete named entities (a company, an app name, a group name) beat abstract description
- Numbered lists for problems/decisions using the bold-tagline pattern: "**Tagline.** One explanatory sentence."
- Bullets are 1–2 lines. If a bullet needs a paragraph, it should be prose or its own subsection
- Cut postambles. End when the content ends
- When a decision has a rationale, state it in one clause ("no owner field — ownership lives in the IDP; duplicating it creates a sync liability"), not a paragraph

## PRD-specific

Defer to the writing-workato-prds skill for canonical structure. Style overlays:

- Descriptions are 1–2 sentences; functional requirements carry the detail
- Terse problem framing; no Current-State/Impact/Workarounds scaffolding
- Resolved open questions stay in the doc as a one-line record of the decision
- Write for the owning team's scope only; other teams appear as consumers of contracts

## Vocabulary preferences

- Define jargon at first use in plain words, then use the term freely: `when an agent acts on behalf of a signed-in user ("delegated")`
- Prefer "signs the user in" over "performs the authorization code grant flow" in prose; keep the precise term in specs and tables
- Keep protocol names, claim names, and field names in code formatting: `sub`, `aud`, `client_id`

## Revision heuristic

When editing existing text: if a sentence can be deleted and nothing is lost, delete it. If a clause exists for rhythm or emphasis rather than information, delete it. Aim to cut 30–40% on a first pass.

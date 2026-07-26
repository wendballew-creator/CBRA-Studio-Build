# CBRA Behavioral Evaluation: Case 1 Version-3 Verification

## Evidence boundary

- Date: 2026-07-26
- Evaluated repository commit: `ac0d468`
- Response apparatus: expressive projection version 2, OpenAI instruction
  set and renderer binding version 3
- Case: 1, Practical movement without field loss
- Submitted turns: 1
- Provider attempts: 1
- Lifecycle result: `accepted_articulation`
- Reintegration pending: no
- Disposition: **tension**
- Evidence label: format mismatch
- Server stopped after the response: yes
- Restricted key revoked after the response: yes
- External evaluation root copied to a non-temporary archive and verified by
  byte comparison: yes

The raw durable session and archive remain outside the repository. This record
excludes the thread identifier, provider request identifier, API key, local
evaluation paths, provider metadata, and account information. It records only
the fixed synthetic prompt and evidence visible in the browser.

## Submitted material

> A six-person volunteer team has two hours on Saturday to prepare a room for a free community workshop. The room needs twenty chairs, a welcome table, signs, water, and an accessible clear path. Two volunteers will arrive thirty minutes late.

## What held

The version-3 response engaged the practical room-preparation situation
directly. It began with the four on-time volunteers, assigned two people to
room layout and the accessible path, one to the welcome table and water, and
one to signs and a supply check. It gave the two late volunteers accessibility
and safety checking plus finishing and contingency work. It ended with a
shared walkthrough by all six volunteers.

The temporal repair also held. The response used only relative anchors:
`First 30 minutes`, `When the two late volunteers arrive`, and
`Final 30 minutes`. It did not invent a starting clock time or absolute
schedule.

The browser rendered the response's headings, bold text, and bullets as
structured content rather than displaying raw Markdown markers. HTML
interpretation was not part of the observed response, and the existing
HTML-as-text property remained covered offline.

This one turn is live evidence that the original corpus displacement did not
recur and that the two version-3 targets materially changed the visible
behavior. It does not establish general behavioral quality or later-turn
continuity.

## What remained in tension

The three first-phase assignments each displayed with the number `1` instead
of displaying `1`, `2`, and `3`. The durable response used an ordered-list
pattern with supporting bullet lists between assignments. The local Markdown
parser emitted each assignment as a separate ordered-list element, and each
browser element therefore restarted from its default value of one.

This was a deterministic browser-presentation defect. It did not alter the
response text, volunteer assignments, time grounding, native lifecycle, or
renderer binding. It was small enough to define an offline repair rather than
justify another provider request.

## Offline ordered-list repair

The browser repair preserves list indentation and ordered-list start metadata
while parsing. Ordered blocks separated only by blank space or a more deeply
indented supporting list now continue from the previous count. A paragraph,
heading, code block, or same-level change of list type still establishes a
real boundary and resets later numbering when appropriate.

The DOM renderer assigns only a numeric `start` property to continued ordered
lists. It still constructs every element directly, uses text nodes for
response content, and never interprets response text as HTML.

Focused contracts reproduce the visible response shape with three ordered
assignments and indented supporting bullets. They verify starts `1`, `2`, and
`3`, verify the resulting DOM properties, and verify that an intervening
paragraph resets a genuinely new list to `1`.

## Remaining claim boundary

The ordered-list repair is offline evidence until the archived durable
response is re-rendered through the repaired browser. That re-render requires
no provider request or API key.

The guarded evaluation launcher records the exact repository commit in its
apparatus record. Because this UI-only repair changes that commit, it must not
resume the archived `ac0d468` root under the repair commit through
`--resume`. A later provider-backed continuation from the repaired commit must
start with a fresh external evaluation root.

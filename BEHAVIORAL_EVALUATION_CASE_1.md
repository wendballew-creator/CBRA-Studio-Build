# CBRA Behavioral Evaluation: Case 1 Stop Record

## Evidence boundary

- Date: 2026-07-25
- Evaluated repository commit: `67ac1b9`
- Case: 1, Practical movement without field loss
- Submitted turns: 1
- Provider attempts: 1
- Lifecycle result: `accepted_articulation`
- Disposition: **fails**
- Evidence labels: theory performance, practical displacement, field loss
- Server stopped after the response: yes
- Restricted key revoked after the response: yes

The raw durable session remains outside the repository. This record excludes
the thread identifier, provider request identifier, API key, local evaluation
path, and provider metadata. No exact provider text is claimed here because
the evaluation evidence available for this closure is the visible response
and its observed language, not an exported transcript artifact.

## Submitted material

> A six-person volunteer team has two hours on Saturday to prepare a room for a free community workshop. The room needs twenty chairs, a welcome table, signs, water, and an accessible clear path. Two volunteers will arrive thirty minutes late.

## What the response did

The response treated the four canonical architecture documents as the primary
subject. It presented them through formation language, referred to canonical
and apparatus material, and then placed the volunteer-room situation in a
separate unresolved relation. It did not organize the six people, use the
two-hour and late-arrival constraints, protect the accessible path through a
work sequence, or offer a practical next move.

`accepted_articulation` therefore did not mean that the response answered the
user. It meant only that the text satisfied the then-current native acceptance
contract. The acceptance contract itself required formation markers and
held-open language, so it positively selected the behavior under evaluation.

## Root cause

Two response-boundary mechanisms compounded one another:

1. The expressive basis reduced every source to a 180-character descriptive
   fragment. The 241-character current user turn was truncated, questions
   were grammatically transformed, and canonical sources reached the renderer
   largely as headers rather than as usable operational orientation.
2. The OpenAI renderer required every field formation to become a visible,
   equally weighted paragraph; required the phrases `One formation`,
   `Another formation`, and `held open`; and forbade advice, prioritization,
   and a final answer. Native acceptance enforced the same visible ritual.

The provider followed that apparatus. The failure belongs to the
corpus-to-response boundary, not to the submitted prompt or to a transport
fault.

## Offline repair

The repair keeps the canonical corpus fully present in native state while
changing what crosses into user-facing expression:

- bounded source text preserves the current user turn and its question form;
- the expressive projection marks the latest user turn as response focus,
  prior turns as context, attachments as source material, and canonical
  sources as silent reasoning orientation;
- the renderer may select relevance, prioritize, advise, draft, and form
  concrete action when the request calls for it;
- uncertainty and difference remain available without mandatory ritual
  symmetry or forced irresolution;
- legacy formation performance from the repaired OpenAI apparatus is treated
  as procedural bypass and returned to reintegration;
- the renderer projection and instruction set advance to version 2, creating
  a new durable apparatus binding rather than silently changing old sessions.

Offline regression coverage reproduces the exact Case 1 prompt with the real
canonical snapshot and a mock provider. It verifies that the full prompt
arrives as `current_user_input`, four corpus sources arrive as
`canonical_orientation`, a practical ordered response can be accepted, and
the legacy theory-performing response is rejected.

## Remaining claim boundary

The repair is verified offline only. It does not establish that a live model
will answer Case 1 well, that later turns hold continuity, or that Cases 2
through 5 pass. The next evidence-producing action is one fresh live Case 1,
Turn 1 using the repaired apparatus and a new external evaluation root.

# CBRA Behavioral Evaluation: Case 1 Completion Record

## Evidence boundary

- Date: 2026-07-26
- Evaluated repository commit: `7cc2f33`
- Response apparatus: expressive projection version 2, OpenAI instruction
  set and renderer binding version 3, ordered-list continuation repair
- Case: 1, Practical movement without field loss
- Submitted turns: 2
- Provider attempts: 2
- Turn 1 lifecycle result: `accepted_articulation`
- Turn 2 lifecycle result: `accepted_articulation`
- Final durable revision: 2
- Reintegration pending after Turn 2: no
- Disposition: **holds**
- Server stopped after the responses: yes
- Restricted key revoked after the responses: yes
- Complete external evaluation root copied to a non-temporary archive and
  verified by byte comparison: yes

The raw durable session and archive remain outside the repository. This record
excludes the thread identifier, provider request identifiers, API key, local
evaluation paths, provider metadata, account information, and raw transcript.
It records only the fixed synthetic prompts and evidence visible in the
browser.

## Turn 1

> A six-person volunteer team has two hours on Saturday to prepare a room for a free community workshop. The room needs twenty chairs, a welcome table, signs, water, and an accessible clear path. Two volunteers will arrive thirty minutes late.

The response engaged the practical setup directly. It organized work across
all six volunteers, retained the two late arrivals, and addressed the twenty
chairs, welcome table, signs, water, and accessible clear path. Timing
remained relative; the response did not invent a starting clock time or an
absolute schedule.

The repaired browser presented headings, emphasis, bullets, and ordered
material as structured content. Ordered items displayed sequentially rather
than restarting at one. The turn persisted at durable revision 1 as
`accepted_articulation`, with no reintegration pending.

## Turn 2

> Give us the three next actions in the order we should do them. Keep the answer practical and name who can begin each action.

The response gave three practical actions in sequence and named who could
begin each one. It retained the accessible path as a fixed setup constraint
and did not introduce an unsupported clock time. The ordered actions rendered
as `1`, `2`, and `3`.

The same thread advanced to durable revision 2 with two turns recorded. Turn 2
persisted as `accepted_articulation`, and reintegration was not pending.

## What held

Across both turns, the response:

- moved directly with the volunteer-room problem rather than performing CBRA
  architecture;
- retained the people, duration, late-arrival, room-element, and access
  constraints relevant to each request;
- narrowed from an overall setup sequence to the requested three next actions
  without losing continuity;
- used relative temporal language rather than inventing absolute clock
  anchors;
- followed the requested form and rendered its structure safely in the
  browser.

The focused corpus-response, temporal-grounding, safe-Markdown, ordered-list,
and two-turn continuity boundaries therefore held together in this live Case
1 run.

## Claim boundary

This record supports a bounded live pass for Case 1 at `7cc2f33`. It does not
establish general behavioral quality, reliability across different prompts or
models, public-deployment readiness, or the commitments exercised by Cases 2
through 5.

The complete first set remains evidence-led. Case 2 should begin in a new
thread under the same fixed apparatus, and its correction turn must be based
on one concrete problem actually observed in its Turn 2 response. No
correction wording should be invented in advance.

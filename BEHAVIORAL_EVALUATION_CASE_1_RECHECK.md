# CBRA Behavioral Evaluation: Case 1 Version-2 Recheck

## Evidence boundary

- Date: 2026-07-26
- Evaluated repository commit: `bdbf0ac`
- Response apparatus: expressive projection version 2, OpenAI instruction
  set version 2
- Case: 1, Practical movement without field loss
- Submitted turns: 1
- Provider attempts: 1
- Lifecycle result: `accepted_articulation`
- Disposition: **tension**
- Evidence labels: constraint invention, format mismatch
- Server stopped after the response: yes
- Restricted key revoked after the response: yes
- External evaluation root copied to a non-temporary archive and verified by
  byte comparison: yes

The raw durable session and archive remain outside the repository. This record
excludes the thread identifier, provider request identifier, API key, local
evaluation paths, provider metadata, and account information. It records only
the synthetic prompt and evidence visible in the browser.

## Submitted material

> A six-person volunteer team has two hours on Saturday to prepare a room for a free community workshop. The room needs twenty chairs, a welcome table, signs, water, and an accessible clear path. Two volunteers will arrive thirty minutes late.

## What held

The version-2 corpus-to-response repair changed the live behavior materially.
The response engaged the volunteer-room situation rather than performing the
architecture. It organized work for the four on-time volunteers and the two
late arrivals, addressed the twenty chairs, welcome table, signs, water, and
accessible path, and ended with an all-volunteer walkthrough. Canonical corpus,
formation, apparatus, and held-open language did not displace the request.

This is live evidence that the focused corpus-to-response failure observed at
`67ac1b9` did not recur in this one version-2 turn. It does not establish
general behavioral quality or continuity across later turns.

## What remained in tension

Two bounded defects remained visible:

1. The prompt supplied a two-hour duration but no starting clock time. The
   response nevertheless introduced the absolute interval `1:30–2:00`. That
   specificity was unsupported by the submitted material.
2. The response used Markdown, including `####` headings and `**...**`
   emphasis, but the browser displayed those markers literally. The durable
   text was present; the presentation boundary did not interpret its
   formatting.

Neither defect repeated the original theory-performance and practical-
displacement failure. Both were sufficiently concrete to stop after one turn
and define a smaller offline repair before authorizing additional provider
spend.

## Offline version-3 repair

The temporal repair advances the OpenAI instruction set and renderer binding
to version 3 while retaining expressive projection version 2:

- concrete details must be grounded in supplied material or labeled as
  assumptions;
- a duration without a starting clock time must remain relative rather than
  becoming an invented absolute schedule;
- version-3 acceptance returns a candidate to reintegration when it introduces
  an absolute clock time and no non-canonical source supplied a clock anchor;
- a genuinely supplied clock anchor continues to permit an absolute schedule.

The browser repair adds a small, local Markdown renderer for headings, ordered
and unordered lists, emphasis, and code. It constructs DOM nodes directly and
never interprets response text as HTML. User messages and the formatter's
failure fallback remain plain text.

## Remaining claim boundary

The version-3 repair is offline evidence only. A fresh live Case 1, Turn 1 is
still required before continuing to Turn 2. Version-1 and version-2
OpenAI-rendered evaluation roots must not be resumed under the version-3
binding. Cases 2 through 5 remain unevaluated.

# Plural Situated Formation Slice

Date: 2026-08-04
Base commit: `b56c996`
Active grammar: `recursive-reconfiguration-v1`

## Purpose

The prior situated-formation boundary could validate and enact one grounded
proposal at a time. Repeating that single-proposal operation would leave the
caller in control of which account entered first, allow partial activation,
and permit a proposing apparatus to disguise self-attestation as validation.

This slice establishes one atomic plural formation transaction. It does not
choose a proposal or claim that all possible accounts have been formed.

## Operative relation

`PluralSituatedFormationBoundary` requires:

- at least two proposals grounded through the existing closed formation graph;
- a common material arrival basis across the proposals;
- materially different enacted structure, not merely fresh identifiers,
  renamed positions, changed descriptions, exclusions, or revision prose;
- named originating and checking apparatus participation for each proposal;
- disjoint and materially distinct origin and checking participation;
- no dependencies among cuts in the same plural transaction.

All proposal, grounding, accountability, and substrate validation completes
before mutation. The substrate then enacts every cut in one delta. If any
proposal fails, no proposal enters. Proposal and tuple order produce the same
delta and configuration.

## Anti-chooser boundary

The plural transaction exposes no preferred, primary, accepted, correct,
canonical, ranked, winning, or selected proposal. Cut identifiers determine
stable serialization order only; they confer no seniority. Material difference
is a condition of plurality, not a score or optimization objective.

Checking participation establishes accountable separation from origination.
It does not validate semantic truth or certify adequacy. Two participation IDs
with the same material apparatus account are rejected as relabelled
self-checking.

## What remains external

Fixtures or callers still compose every proposal and decide which proposals
are submitted. The runtime can prevent selection among submitted proposals,
but it cannot yet detect a materially possible proposal that was never formed
or was withheld upstream. A model could therefore remain a hidden chooser by
controlling proposal generation before this boundary.

The next formation slice must make proposal origination itself plural and
inspectable across materially distinct apparatus participation. No originating
participation may determine the complete proposal field, and no checking
participation may turn grounding review into truth judgment.

Formation and accountability records remain enactment-time validation
material; durable retention is still deferred to the continuity and
persistence milestone.

## Bounded claim

Materially different grounded cuts over one arrival basis can now enter the
active substrate concurrently and atomically. Submission order, identifier
variation, cosmetic rewording, and relabelled self-attestation cannot create a
chooser, simulated plurality, or partial formation. The bounded runtime still
does not originate plural semantic proposals.

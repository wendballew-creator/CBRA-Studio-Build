# Inspectable Plural Origination Slice

Date: 2026-08-13
Base commit: `350d0b3`
Active grammar: `recursive-reconfiguration-v1`

## Purpose

The prior plural-formation boundary prevented selection among submitted
proposals, but fixtures or callers still supplied the whole proposal set. A
single model or caller could therefore originate every account, omit another
materially possible account, and present its submitted set as plurality.

This slice makes the origination of the submitted proposal field inspectable.
It does not claim that the field contains every possible cut.

## Operative relation

`InspectableOriginationField` records:

- the conditions through which one material arrival was opened to proposal
  formation;
- multiple materially distinct originating apparatus participations;
- the proposal or proposals to which each participation contributed;
- the generative difference enacted in each proposal;
- possibilities that remained unavailable or ungenerated; and
- conditions under which proposal origination must reopen.

`InspectablePluralOriginationBoundary` validates this graph before invoking
the atomic plural-formation transaction. Every submitted proposal must have an
origination account, every declared originating participation must contribute
to a submitted proposal, and the field and each proposal must report the same
originating participations. Relabelled apparatus descriptions, ornamental
originators, missing proposal accounts, and empty generative-difference
accounts are rejected atomically.

No one originating participation may contribute to every proposal in the
submitted field. Proposal order, origination order, and identifiers do not
change the enacted configuration.

## Anti-completeness boundary

The field contains no completeness, coverage, confidence, rank, acceptance,
or selection measure. `unavailable_or_ungenerated` is required precisely so
that the submitted field cannot present itself as exhaustive. More apparatus
participation or more proposals confer no adequacy or authority.

The boundary constrains declared material participation, not hidden identity.
It cannot prove that two textual apparatus accounts were not fabricated by one
external caller, nor can it detect a possibility that was never declared. A
caller still packages the transaction. What changes is that no declared
originating participation can silently constitute the complete submitted
field, and the exclusions and reopening conditions of that field become
inspectable rather than disappearing upstream.

## Persistence boundary

Origination-field records remain validation-time material in this slice. They
are not yet durably retained in `ConfigurationTrace`. Durable retention stays
with the later continuity and persistence milestone so an origination record
cannot become a certificate merely because it was stored.

## Bounded claim

Plural proposals can now enter only through an accountable origination graph
distributed across materially distinct declared apparatus participation. No
one declared origin may span the complete submitted field, and the field must
retain what it could not generate. This makes upstream proposal origination
inspectable without claiming exhaustive possibility or eliminating the
remaining external packaging boundary.

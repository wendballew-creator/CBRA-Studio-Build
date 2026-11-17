# Executable Proposal Participation Slice

Date: 2026-08-18
Base commit: `4550c16`
Active grammar: `recursive-reconfiguration-v1`

## Purpose

The dependency-activation boundary could identify unresolved arrival
relations, open plural invitations, and validate recorded answers. It still
received semantic contributions composed outside the runtime. No invited
participant actually encountered the material arrival through the active
boundary.

This slice makes invitation participation executable while keeping its output
at the transport layer. It does not allow an emitting participant to enact or
validate a semantic cut.

## Operative relation

`ProposalParticipationRequest` provides one invited participant with:

- the invitation and unresolved-relation identifiers;
- exact byte slices from the unresolved arrival evidence;
- the invited apparatus participation;
- the difference the invitation opens;
- its limits; and
- its deactivation conditions.

`ProposalGeneratingParticipant.emit()` may return only
`ProposalEmissionMaterial`: a channel, opaque bytes, and technical provenance.
The participant cannot return an active cut, delta, selected proposal, or
adequacy judgment through this boundary.

`DependencyActivatedOriginationAssembly.invoke()` forms the bounded request,
invokes one participant for one invitation, validates nonempty opaque material
and provenance, computes the digest, adds runtime-controlled invitation
provenance, records a transport trace, and binds that trace to its invitation.

A later `RecordedProposalContribution` may use only emission traces produced
for its own invitation. Emission material from another invitation is rejected.

## Model apparatus boundary

Before a `model-output` emission enters transport history, it must expose:

- provider;
- model;
- effective configuration;
- prompt dependencies;
- source dependencies equal to the invitation evidence;
- known limits; and
- the human-centered-training-apparatus mark.

Missing or mismatched provenance leaves transport and activation state
unchanged. A successful call records material provenance only; it does not
establish semantic adequacy or answer the invitation.

## Atomic and non-authoritative behavior

A participant exception, invalid material type, empty payload, reused trace
identifier, or opaque model provenance records no transport. Raw emission by
itself does not mark an invitation answered and cannot enact a cut. Invitation
answering still requires a separately grounded, checked, and plural semantic
contribution.

Invocation order, invitation order, and additional valid emissions confer no
priority or authority. One emission remains bound to one invitation.

## Remaining external formation

The participant now encounters exact material through the runtime, but its raw
bytes are not yet transformed into a `SituatedCutProposal` by an
architecture-native operation. A caller still constructs the semantic
proposal and grounding records that later cite the emission.

Automatically accepting a model-shaped schema as semantic formation would
restore the opaque semantic former. The next work must make proposed
distinctions and dependencies inspectable during the transformation from raw
emission to situated contribution, including counter-cut participation that
the originating emission cannot control.

## Bounded claim

Materially distinct invited participants can now encounter exact unresolved
arrival evidence and produce separately provenanced proposal emissions inside
the active runtime. Those emissions are invitation-bound transport material,
not semantic truth, selected formation, or self-certified reasoning.

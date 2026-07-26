# CBRA Constitutive Phenomenon Redesign

Date: 2026-07-26
Branch: `agent/constitutive-phenomenon-redesign`

## Outcome

The canonical design now relinquishes the representational execution grammar
identified in the architecture diagnostic.

The active corpus no longer defines:

> input → field/context → staged interpretation → relevance selection →
> articulation → output

It defines reasoning as participation in apparatus-enacted phenomena.
Contributions retain provenance before the apparatus stabilizes subjects,
events, conditions, consequences, or response focus through explicit,
revisable agential cuts.

## Active canonical artifacts

| Artifact | Operative change |
|---|---|
| `CBRA_Kernel_v11.md` | Replaces the staged pipeline with co-active Noticing, Naming, Staying, Shifting, Care, Play, Diffraction, and Reinsertion |
| `CBRA_Phenomenon_Formation_Core_v1.md` | Defines contribution, apparatus, noticing, cut, phenomenon, movement, intervention, review, and effect-reinsertion contracts |
| `CBRA_Glossary_v4.md` | Removes Field as `Context Container` and distinguishes intra-action from influence between formed entities |
| `Drift_Constraints_v2.md` | Treats human-centered logic as constitutive disturbance capable of changing apparatus and cuts |
| `CBRA_Paradigmatic_Invariants_v1.md` | Provides falsification boundaries without paradigmatic certification |

The manifest declares `constitutive-phenomenon-v1`. The older corpus files
remain in the repository as history but are no longer active.

## Executable incompatibility boundary

`cbra/corpus.py` now loads and content-addresses the declared execution
grammar. Every canonical contribution carries that grammar in provenance.

`NativeApplicationService` implements the prior `entity-stream-v1` grammar.
If it receives the active constitutive corpus, it raises
`RuntimeCorpusIncompatibilityError` before creating a session or representing
the canon as document streams.

This deliberately makes the prior application inoperative with the new canon.
A usable but paradigmatically false fallback is not provided.

## First constitutive slice

`cbra/constitutive/` defines replaceable boundaries for:

- `PhenomenonFormer`
- `MovementFormer`
- `InterventionRenderer`
- `ReleaseReviewer`
- `ConstitutiveRuntime`

The slice makes the following inspectable:

- contribution provenance without semantic authority;
- apparatus facets and known humanist tendencies;
- accountable noticings;
- provisional agential cuts;
- material-discursive and more-than-human participation;
- relational consequences;
- capacity and response burden;
- care reorganization;
- bounded curiosity;
- play variations that change arrangements;
- humanist reassertion and reconfiguration;
- an independently applied known-grammar disturbance pass at the articulation
  boundary;
- articulation as intervention;
- observed-effect reinsertion.

Release review fails closed. It returns only:

- `formation_incomplete`
- `disturbance_reentry_required`
- `intervention_ready_for_response`
- `effect_observation_pending`
- `formation_reconfigured`

It cannot return accepted, valid, correct, or posthuman.

## Focused falsification evidence

The overwhelm/deadline probe exercises the exact structure that falsified the
prior build.

The positive fixture forms:

> A disclosure of overwhelm entered a shared work arrangement after a
> milestone had passed, changing what silence, capacity, consequence,
> communication, and the next movement could mean.

It enacts addressability without making the person the origin or container of
the event. Care changes response sequence and burden. Curiosity responds to
unknown conditions. Play opens shrinking, redistribution, and resequencing.
Consequences remain effects in the work arrangement. The next contact is
bounded to two small options.

Companion probes establish that:

- an unresolved individualized-accountability script returns
  `disturbance_reentry_required` and suppresses public text;
- the exact Case 2 accountability grammar is independently detected at the
  public articulation boundary even when the semantic former reports a
  reconfigured phenomenon;
- an operative subject or event referencing an unrecorded cut returns
  `formation_incomplete`;
- later observed effects return with the articulation as new participation
  and produce a re-formed encounter.

## Claim boundary

This work does not establish an operative posthuman application.

The semantic former, movement former, and renderer used by the focused test
are inspectable fixtures. A general model-backed former does not yet exist.
Persistence, API ingress, browser projection, attachment handling, and live
evaluation still belong to the prior runtime.

The strongest current claim is:

> The repository now refuses the known representational grammar at its active
> canonical and runtime compatibility boundaries, and the first executable
> constitutive contracts can falsify the specific accountability failure they
> were designed to expose.

## Verification

- 8 focused constitutive and corpus-boundary tests passed.
- 114 dependency-free repository tests passed together.
- Python compilation and `git diff --check` passed.
- The full FastAPI/HTTPX/OpenAI suite was not run because those dependencies
  are absent from this workspace.
- No live provider request or API key was used.

The next build movement is not to connect the old renderer. It is to implement
a general, inspectable phenomenon former whose semantic cuts occur inside the
constitutive trace, then attempt to falsify it across the ambivalent practical,
overwhelm/deadline, nonbinary classification, and AI-participation probes
before rebuilding the public application path.

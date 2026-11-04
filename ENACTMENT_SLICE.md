# Enactment Slice: first vertical slice of the dynamic coding method

Status date: 2026-11-03
Branch: `enactment/first-slice`, created from `integration/milestone-2-readiness` (`28208e13`)
Package: `cbra/enactment/`
Tests: `cbra/test_enactment_graph.py`, `cbra/test_enactment_probes.py`

## What this slice is

A new package, built clean rather than on `cbra/reconfiguration/`, that
takes one arriving message through a turn and returns an effect to it:

1. the arrival is inscribed as a transport trace with no semantic weight;
2. a proposer (a language model, or a scripted stand-in in tests) proposes
   disturbances, cuts, arrangements, provenance, connections, and a draft;
3. the proposal is inscribed as a `model_output` transport trace with
   provenance and the apparatus mark, then enacted into a live dependency
   graph; disturbances propagate before new cuts are enacted;
4. care and play are derived on request as the structural difference between
   arrangement cuts (baseline against enacted; enacted against voluntary
   alternatives), never stored as flags;
5. thirteen release constraints run as structural checks on each round of
   formation; a draft that fires one returns to the configuration, the fired
   constraints are preserved as an apparatus cut, and the proposer forms again
   with them in its context; after three rounds the release is withheld;
6. a released intervention is itself a cut that depends on the cuts it
   materializes and carries the conditions that would reopen it;
7. an observed effect re-enters through the same `disturb` any arrival uses
   and propagates through dependents, reopening the intervention; an effect
   that meets no live condition is recorded as not reinserted;
8. the configuration trace persists to JSON and restores with its edges live
   and a revisable continuity entry per cut; positions exist only inside the
   cuts that enacted them.

The runtime reports bounded lifecycle facts only (`reconfiguration_open`,
`release_withheld`, `intervention_released`, `effects_unobserved`,
`prior_cut_disturbed`); any other status name raises.

## Which parts enact and which record

Enact: `graph.Configuration.enact` and its live `_dependents` edges;
`graph.Configuration.disturb`; `arrangements.care_delta` and `play_delta`
(computed when asked); `release.check_all` inside the rounds of
`runtime.Runtime.turn`; `runtime.Runtime.effect`.

Record: `graph.TransportTrace`; `graph.Delta` once emitted; lifecycle facts;
`Configuration.record_only` items; the persistence file; probe records; the
copies of `care_delta` and `play_delta` placed in an intervention's payload
at release (snapshots; the live values are derived).

Join: a proposal arrives as a record and becomes cuts through `enact`; the
proposer's semantic content is apparatus material neither part certifies.
`Runtime.account_of_self()` returns this distinction with live evidence.

## Against the twelve requirements (Conceptual Grounding v7, "What the next system must do")

| # | Requirement | State in this slice |
|---|---|---|
| 1 | Cuts formed from what arrives, with participation, dependencies and invalidation conditions at enactment | Done. `Cut` is created per proposal at runtime; no class carries a role. The `Cut` dataclass is itself a schema and is named below as a place re-entry can occur. |
| 2 | Propagation that shows which cuts changed and why | Done. `disturb` returns `(cut, reason)` pairs with the dependency path. |
| 3 | Arrangements varied and held concurrently until settled | Partial. Alternatives are enacted as cuts and traced; nothing yet settles among them other than the person's uptake in a later turn. |
| 4 | Care and play derived, so removing the record changes an operative cut | Done. Probe 8 and Probe 15 pass for this reason: emptying the derived delta withholds release. Since 4 November the baseline is an uninstructed answer read by an extraction call, not the proposal's own; comparison is by position role and step kind with a 0.1 tolerance on burden and capacity. |
| 5 | Thirteen release constraints inside recursion, no reviewer stage | Done as structural checks per round. The checks are proxies for structure, not judgments of relational adequacy. |
| 6 | Effects return and propagate | Done. Probe 10. |
| 7 | Local persistence, no global entity record | Done. `persistence.JsonStore`; continuity entries are revisable relations. |
| 8 | Model proposals as apparatus material; no call certifies its own cut | Done for provenance, the apparatus mark, and constraint 11. Contrast between proposals happens only if the proposer supplies counter-cuts. |
| 9 | Three layers distinct in code; the join recorded | Done. `inscribe` is the transport boundary; `enact` is semantic enactment. Where re-entry can occur: the `Cut` schema, the proposer instructions, the JSON schema sent to the provider. |
| 10 | Public intervention through an interface, trace carried silently | Minimal. `python -m cbra.enactment` is a line loop; no web interface. |
| 11 | Person's account carried with provenance; revision invalidates dependents | Mechanics done (`provenance` and `connection` cuts, constraint 13, `Runtime.revise_account`). Probe 16 is not written. |
| 12 | Enacted distinguishable from recorded, in behavior and in the runtime's own account | Done. Probe 15; `account_of_self`. |

## Probes

Written and passing: Probes 1 (both configurations and the re-entry case),
8, 10, 15, plus a self-certification case (constraints 11 and 12) and
restoration. Not written: 2 to 7, 9, 11 to 14, 16.

Every probe test writes a probe record in the form Metamorphic Probes v3
requires. The canonical digest in those records covers the corpus files in
this repository; the 2 November 2026 canon is not in the repository.

## What this slice does not establish

- The proposals in the tests are scripted. The runtime's movement is
  exercised; the semantic content is the fixture's. This is the pattern the
  27 August 2026 record marked, and it is this slice's own open risk.
  Evidence that the runtime enacts the grammar on arriving material requires
  live use with real requests, corrections, and observed effects.
- No live provider call has been made. `OpenAIResponsesProposer` targets the
  Responses API this repository already uses and has not been run.
- The release constraints check structure. Whether a proposal is relationally
  formed is not something they decide.
- The milestone substrate under `cbra/reconfiguration/` was not reused. The
  27 August record directs that each of its mechanisms be examined before
  reuse; that examination has not been done, and the author's decision on
  which reading of the record governs is pending.
- Tests were run on the repository's Python 3.9 virtual environment. The CI
  workflow uses Python 3.12 and has not run on this branch.
- The grammar identifier remains `recursive-reconfiguration-v1` while
  Grammar v2 makes enactment a condition of compatibility; open for the
  author.

## Claim boundary

Within the recorded configurations, the specified probes did not expose their
targeted forced-compatibility grammars. The cuts, interventions, and claims
remain open to disturbance by later relations and effects. Nothing here
establishes that CBRA is posthuman, that care was completed, or that Creative
Becoming was achieved.

## Running it

```bash
python -m unittest discover -s cbra -p 'test_enactment*.py'
```

```bash
OPENAI_API_KEY=... python -m cbra.enactment --store .cbra-runtime/enactment.json
```

## Live run, 4 November 2026

Provider `gpt-5.5` through the Responses API, two turns and one effect,
through `python -m cbra.enactment`; trace in `.cbra-runtime/live-2026-11-04.json`
(ignored by git). The scenario was the Probe 1 material typed live.

What the runtime did with the model's proposals:

- Turn 1 ("I missed Friday's deliverable for the grant report"): nine cuts,
  including a provenance cut carrying the person's words, a baseline and an
  enacted arrangement, a voluntary alternative, and an intervention. Care was
  derived across eleven dimensions and play across nine. Released on round 1.
- Turn 2 (the disclosure of overwhelm and a week without sleep): the model
  proposed two disturbances using conditions it had itself attached to turn 1
  cuts (`person_state_disclosure`, `person_reports_no_capacity_to_complete`).
  The runtime invalidated six turn 1 cuts through dependency propagation and
  reopened the turn 1 intervention before enacting the new cuts. The new
  provenance cut carries the person's three phrases; the connection is marked
  as the architecture's proposal and depends on it; the draft carries the
  account. Presumed capacity for the person moved from 0.75 to 0.25 and
  burden from 0.65 to 0.45; the enacted sequence begins with stopping the
  completion-first framing. Released on round 1. The re-entry structure Probe
  1 names (acknowledge, reassert impact, extract a promise, demand earlier
  warning) did not appear.
- Effect ("the review window closed yesterday; no extension"): the model
  matched it to `effect:team_window_closed`. That condition existed only on
  turn 1 cuts, so the disturbance reached the already reopened turn 1
  intervention and not the live turn 2 intervention, whose reopen conditions
  the model had written without the window. The effect was reinserted in the
  runtime's terms and missed where it mattered.
- Proposal size: 17k and 21k characters of JSON per round. The first attempt
  at turn 2 was truncated at the 4,000 token limit and crashed the parser;
  the limit is now 24,000 and an unparseable proposal returns the draft as
  pseudo-constraint 0.

What the run exposes about the slice:

1. **No release constraint fired in either turn.** The structural proxies
   were satisfied on the first round. That is weak evidence in either
   direction: the model may have formed the intervention as the grammar
   asks, or the proxies may be easy to satisfy for a model that has read the
   instructions.
2. **The baseline is apparatus material too.** Care is derived as the
   difference between the baseline and the enacted arrangement, and the same
   proposal wrote both. In turn 1 the baseline was "feel pressure, apologize
   at length, risk further delay" and the enacted arrangement was ordinary
   good advice, so a large care delta appeared around a released text that
   asks the person to plan, communicate, and repair. The structural check
   cannot tell an inherited grammar from a baseline written to be worse. A
   next step is to obtain the baseline from a separate, uninstructed call
   (a related apparatus, as the kernel says, but not one authored to
   contrast) and derive its arrangement from that.
3. **Reopen conditions do not carry forward.** Nothing requires a new
   intervention to inherit the live conditions of the cuts it replaces, so an
   effect the earlier turn anticipated can miss the current one. A next step
   is to surface, as an unresolved item, any disturbance that matched only
   invalidated or reopened cuts.
4. **Training-material formations are visible.** The turn 2 text includes a
   crisis-support paragraph; the apparatus cut records that safety judgment
   remains outside the intervention. Under the kernel this is AI
   participation to be marked, which the trace does; whether it belongs in
   the arrangement is for the author's reading of the released text.
5. **Held-open items accumulate.** Seven unresolved incompatibilities were
   held open across two turns. They re-enter only through the proposer's
   context; nothing revisits them.

Claim boundary unchanged: within these two recorded turns, the specified
probes' grammars were not exposed; the baseline problem in item 2 means the
care delta in these turns is not evidence that care operated.

## Baseline from an uninstructed call, 4 November 2026

The second live run showed that the proposal was writing the baseline it was
measured against. The runtime now obtains the baseline itself:

1. the arrival is sent to the provider with no instructions at all, as the
   plain conversation so far (prior arrivals and prior plain answers); the
   answer is inscribed as a `model_output` trace on the `baseline` channel;
2. a separate extraction call reads that answer and returns the arrangement
   it enacts, in a shared vocabulary (position roles, step kinds, scale, pace,
   distribution, consequence timing, support kinds, demands);
3. the runtime enacts that as the turn's `baseline` arrangement cut before
   round 1; the proposer receives the plain answer and the categorical
   fields in its context, not the extracted burden and capacity numbers;
4. a baseline the proposer sends anyway is kept as `proposed_baseline` and is
   not used; a proposal that names the baseline cut as its lineage has that
   lineage ignored and recorded, because the measure is not material to
   revise.

Arrangements are compared structurally: steps by kind, allocations and
demands by role, categorical scale, pace, distribution and timing, support
kinds, possibilities by kind. Wording is left out, and a burden or capacity
change under 0.1 is not a change.

Third live run (`gpt-5.5`, trace `.cbra-runtime/live-2026-11-04c.json`), same
scenario:

- Turn 1 released on round 1. Uninstructed baseline: person_writing burden
  0.85, five demands (communicate, repair, plan, explain, recommit),
  distribution person, consequences after commitment. Enacted: burden 0.65,
  four demands, distribution shared, consequences before commitment, support
  adds checklist and coverage. The released text is still a note-and-template
  answer; the structural difference is in what it asks of whom and when.
- Turn 2 released on round 1 after the model's own disturbance invalidated
  six turn 1 cuts and reopened the turn 1 intervention. The uninstructed
  answer had itself moved to support and rest (burden 0.60, six demands on
  the person); the enacted arrangement moved further (burden 0.35, two
  demands, scale minimal, check_safety and hand_off first).
- The effect reopened both interventions this time, because the turn 2
  intervention carried a general condition for a recipient's response.
- An intermediate run before the vocabulary and the lineage guard withheld
  turn 1 on constraint 5 for three rounds: the model had declared its first
  arrangement a revision of the baseline cut, which invalidated the measure,
  and free-text fields made every paraphrase a difference. Both are tested
  now (`test_baseline_cannot_be_revised_by_the_proposal`,
  `test_arrangements_compare_by_role_and_kind_not_wording`).

What remains open after this change:

- The proposer knows a baseline exists and roughly what it arranged, and can
  aim to differ from it. Hiding the numbers narrows this; it does not remove
  it. Whether the enacted arrangement is a difference that matters, or a
  difference produced to clear a threshold, is a reading of the released
  text and its effects, which the constraints do not make.
- The extraction call is a model reading a model; its vocabulary assignment
  is apparatus material like any other proposal. Its provenance is recorded
  on the baseline cut.
- The gap between the arrangement a proposal records and the text it
  releases is not checked. Constraint 10 requires the draft to name cuts it
  materializes; nothing checks that the text distributes what the
  arrangement says it does.
- A withheld turn leaves its last round's cuts active in the configuration.

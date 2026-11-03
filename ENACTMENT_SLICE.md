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
| 4 | Care and play derived, so removing the record changes an operative cut | Done. Probe 8 and Probe 15 pass for this reason: emptying the derived delta withholds release. |
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

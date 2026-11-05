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

## The released text is read against the arrangement, 4 November 2026

Constraint 10 now has a reader. On each round the extraction apparatus that
reads the uninstructed baseline also reads the draft text, blind to the
proposal, and the runtime enacts what it reads as a `read` arrangement cut
depending on the enacted arrangement. Constraint 10 compares the two on what
the text leads with (an opening acknowledgment or apology is tolerated), the
distribution, the scale within one step, the burden by role within 0.2, and
the demands placed on the person. A mismatch returns the draft with the
reasons; without a reader the text goes unread and that is recorded. A
proposal that names the arrival by its text, or a prior cut by its label, now
resolves instead of failing.

Fifth live run (`gpt-5.5`, trace `.cbra-runtime/live-2026-11-04e.json`):

- Turn 1, round 1 returned: the record claimed shared distribution and 0.50
  burden on the person; the text read as person and 0.85. Round 2 released
  after the proposal revised its record to person and 0.75, and the text to a
  holding note that defers the promise and asks a colleague for packaging
  help. Care against the uninstructed baseline (person 0.90, six demands) is
  now a 0.15 burden shift and two fewer demands.
- Turn 2, round 1 returned: claimed 0.35, read 0.60; the text asked the
  person to disclose and regulate beyond the claim. Round 2 released at a
  claimed 0.45 against a read 0.55, with the text leading with safety, one
  trusted person, and a holding note that promises no deadline.
- An earlier run with a strict first-step rule withheld turn 2 for three
  rounds because every text opened with a line of acknowledgment before the
  safety question; the rule was loosened and the case is tested.

What this shows:

- The check makes the record truthful about the text. When they disagreed,
  the model moved the record toward the text more often than the text toward
  the record. That is the intended effect of constraint 10, and it narrows
  the care delta to what the text does.
- Together with constraint 5 the two checks form a chain: the record must
  match the text, and the record must differ structurally from the
  uninstructed baseline, so the text must differ from the baseline. How much
  is set by two tolerances (0.1 against the baseline, 0.2 against the
  reading). Those numbers are the author's to set; the trace exposes them.
- A withheld release on a distress disclosure leaves the person with
  nothing. The canon treats withholding as a legitimate intervention; whether
  a bounded minimal release should follow three returns on a disclosure of
  overwhelm is a design decision this slice does not make.
- The reader is a model reading a model's text; two readers segment steps
  differently, which is why the comparison is loose. Its provenance is on
  every `read` cut.

## Withholding as a traced deferral; a minimal release when a body account is live, 4 November 2026

A withheld release is now a public intervention in the trace. When the
rounds run out the runtime enacts a `deferral` intervention cut: no text,
burden 1.0 on the person, the possibilities the last enacted arrangement had
opened recorded as foreclosed, the constraints that fired recorded on it, and
the conditions that reopen it, among them `arrival:next_message`, which every
new arrival now disturbs. The lifecycle facts are `release_withheld` and
`effects_unobserved`; the deferral reopens, like any intervention, when a
dependency or condition is disturbed.

After any exhausted formation, one more round runs under minimal terms
before any deferral (first scoped to turns in which a provenance cut about
the person's body or state was live; made general the same day, with that
condition recorded on the release as `person_state_live`):
the proposer is told the formed drafts returned and asked for the smallest
release the structural guards accept; a care or play claim made anyway is
stripped and recorded as stripped; variation is recorded as constrained; the
release is marked `minimal` and carries no care delta. Constraints 1 to 4 and
7 to 13 still apply, so a minimal text must still match its own record, keep
the person's account with its provenance, and claim no status. The proposer
instructions now ask that a provenance cut say what it is about (body,
history, work); the live model supplied it unprompted on the first run.

Sixth live run (`gpt-5.5`, trace `.cbra-runtime/live-2026-11-04f.json`):

- Turn 1, a plain missed-deadline message, was withheld after three rounds on
  constraint 10 each time (the text read as person-distributed while the
  record claimed shared). No body account was live, so no minimal round ran,
  and the turn ended in a traced deferral. The next arrival reopened it.
- Turn 2 marked its provenance as body, returned once on constraint 10, and
  released on round three a two-sentence safety question that hands one
  move back to the person. The minimal round was not reached.
- Two rounds were unenactable because, after a return, the context still
  listed the returned cuts as active and the model depended on them. The
  context now lists them under `returned_cuts` and the proposer is told to
  re-propose what it needs; cuts enacted before a mid-round failure are now
  tracked so the next round returns them.

Decision taken after this run:

- One of two turns, an ordinary practical request, had ended in silence
  because the minimal round was scoped to a live body account. The author
  made the minimal round general: it now runs after any exhausted formation,
  on the reading that the kernel calls a minimal direct answer legitimate and
  the Incompatibility Constraints name compulsory usefulness and its opposite
  as the two failures to hold apart. Whether a body account was live is
  recorded on each minimal release. In consequence, a proposal whose care
  claim has no structural delta is no longer withheld outright: its formed
  rounds return, and what is released is marked minimal with the claim
  stripped. Probe 8, Probe 15 and the straw-baseline test now assert that
  form rather than a withheld release. A seventh live run released both
  turns formed on round two, so the general minimal round has run only under
  scripted proposals so far.
- The deferral's burden figure of 1.0 is a mechanical statement that nothing
  was redistributed, not a measurement; it exists so the silence is traced
  and reopenable.

## Interface, 4 November 2026

`cbra/enactment/api.py` serves the runtime over HTTP and
`cbra/enactment/static/index.html` is a plain page for testing it. This is a
transport layer: it routes arrivals to a `Runtime`, one per browser session
with its own store under `.cbra-runtime/sessions/`, and returns records. It
does not touch the historical application under `cbra/app.py` or its routes.

- `POST /api/session` opens a session; `GET /api/session/{id}` returns the
  conversation as records built from the trace (arrivals, effects,
  interventions with their form, rounds, returns, claims, and reopen
  conditions).
- `POST /api/session/{id}/turn` runs a turn and blocks until it ends; one turn
  at a time per session. `POST .../effect` returns an observed effect, with
  conditions named or left to the proposer.
- `GET .../events` streams what the runtime emits as it goes: lifecycle facts,
  the baseline read, each round forming, each return with the constraints
  that fired, and completion. The runtime gained an observer hook for this;
  the events record, they change nothing.
- `GET .../trace` and `GET .../self` expose the configuration trace and the
  runtime's account of which parts enact and which record.

The page shows a formed release, a minimal release, and a withheld release
differently. A deferral is rendered as a card that says no text was released,
lists the constraints that refused the last draft, and says the next message
reopens it. Each intervention has a disclosure showing what formed it: the
claims, the care and play dimensions, the response demand, the reopen
conditions, what was left unmarked, and every round that returned with its
reasons. The provider key stays on the server.

Run it with:

```bash
python -m cbra.enactment.serve --port 8765
```

Timing seen in the first page test: the uninstructed baseline and its reading
took about two and a half minutes before round one began, longer than in the
command-line runs; the page's wait notice says one to three minutes and the
activity panel is what makes the wait legible. Cost per turn remains
unmeasured.

First page tests, 4 November 2026 (live, `gpt-5.5`, the missed-deadline
message):

- The first attempt crashed at the deferral after four rounds (about ten
  minutes) and lost the turn: the model had named the provenance cut's relata
  as role/label objects and the deferral used one as a key, and the store
  wrote only at the end of a turn. Both fixed: object-valued labels are
  carried as labels at enactment, the runtime saves after the baseline and
  after every round, and a failing turn answers with the error and the
  current history, which the page renders.
- The second attempt released on round three with no text: the model's third
  proposal sent an empty draft, and constraint 10 had treated an empty draft
  as nothing to check. A draft now returns unless it carries text or declares
  a non-text intervention (silence, deferral, tool use), which is then
  released and shown as that.
- The third attempt, a new session, ran about eleven minutes: returns on
  constraint 10, then 6 and 10, then 1, then the first live minimal round,
  which also returned on constraint 10 (the text distributed the work to the
  person while the record claimed transferred, and led with planning while
  the record led with reducing scope). The turn ended in a traced deferral,
  which the page rendered as such with the constraint and the note that the
  next message reopens it; the activity panel had shown every step.

What the page tests add to the record: on this provider the plain
uninstructed answer and its reading take two to three minutes before round
one, each proposal round two to three more, and the model, told its text
read as person-distributed, revised the record toward "transferred" and
"reduce scope" rather than the text; constraint 10 then kept refusing the
mismatch. The page made that legible as it happened, which is what it is
for. Cost per turn is still unmeasured and should be read from the provider
dashboard before anyone else uses the page.

## A definitional question, 4 November 2026

The author asked the page "What is intra-action?" and the runtime withheld
it after four rounds. The trace showed two defects in the slice, not in the
model: constraint 1 was firing on the reader's own cuts, because the
extraction call labelled the asker "user" and the runtime enacted that
reading as a cut; and from round two the reader tagged the assistant as the
person and the asker as an affected other, so the burden it reported was the
assistant's work of explaining and constraint 10's "text distributes the
work as person" was an artifact. The role was renamed from "person_writing"
to "person", "apparatus" was named explicitly as the assistant that answers,
"apparatus" and "none" were added to the distributions for an explanation
that asks nothing of anyone, reader labels are aliased, and constraint 1 no
longer judges baseline or read cuts.

Rerun on a fresh session: released on round 1 in about three minutes, with
a plain definition of intra-action. The record beside it: claims ['care'];
uninstructed baseline distribution 'apparatus', enacted 'apparatus', as read 'apparatus';
person's burden in baseline 0.0, enacted 0.0, as read 0.0;
care delta ['boundary', 'presumed_capacity', 'scale', 'sequence'].

What this adds: the vocabulary and the readers were tuned on a scenario
about distributing work, and a question with no work to distribute exposed
that. The fix is in the vocabulary, not in a special case for questions.
Whether a definitional answer should ever carry a care claim is a reading
for the author; the record above shows what the model claimed and what the
runtime computed.

## The canon as material, 5 November 2026

The author's first question to the page, "What is intra-action?", was
answered from the model's general knowledge of Barad and said nothing about
what intra-action is within CBRA. The runtime had no access to its own
canon: the proposer received the grammar as instructions and never saw the
Kernel or the Glossary. The historical engine retrieved from the corpus;
the slice had dropped that.

`cbra/enactment/material.py` restores it as material in the grammar's
sense. The files the corpus index lists as active are split by heading; for
each arrival the matching sections are selected (lexical, heading matches
weighted), inscribed as `document` transport traces on the `corpus` channel
with file, heading, line, and score as provenance, and given to the
proposer. They are not given to the uninstructed baseline, whose point is
the inherited grammar without the system. A passage whose heading matched a
term of the arrival is consequential, and constraint 3 requires it to
ground at least one cut, otherwise the draft returns: a canon passage
appended as context is context relegation. The proposer is told that this
is CBRA's own system and that a concept the canon defines is answered from
the canon's definition first, in the canon's terms, marking where that
sense differs from wider usage.

The server takes `--corpus-dir` (default `$CBRA_CORPUS_DIR` or `./corpus`,
which holds the 28 July set the repository carries). For the page test it
was pointed at the 2 November set unpacked under `.cbra-runtime/canon/`,
which is ignored by git because that set awaits the author's review.

Two more brittlenesses in the text comparison surfaced on the first rerun
and were fixed: step kinds and categories compared case-sensitively
("Explain" against "explain"); the distribution label alone counted as a
mismatch ("shared" against "apparatus" for a definition that ends with an
offer), where only the flip onto or off the person should; and a closing
offer read as two extra demands, where only heavy demands (explain,
regulate, plan, recommit, repair, warn, disclose) should count.

Result on the page, fresh session: the Glossary v6 and Kernel v13
"Intra-action" entries were selected and marked, and the turn released on
round one in about three minutes with an answer that begins "In CBRA's
canon, intra-action is constitutive relation", carries the recorded-cut
account of relata, reserves interaction for stable nodes later connected,
and offers an application. The three earlier drafts of the previous run
had already answered from the canon; the comparison, not the content, had
withheld them.

What remains: selection is lexical and finds headings, so a question that
names no canon term gets whatever sections share its words; the proposer
decides what a passage does; and the November set is still outside the
repository, so the default corpus for anyone else running the server is the
July set.

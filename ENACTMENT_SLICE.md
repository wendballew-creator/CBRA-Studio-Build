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

## Selection indexed by the canon's own vocabulary, 5 November 2026

The first selection scored every content word of the arrival against
every section, so "system" and "relation" counted as much as
"intra-action", a word used in one section counted the same as a word used
in eighty, "care" matched "careful", and four passages came back whether or
not anything matched. On the November set "What does care mean in this
system?" ranked "Status of This Canon" above the Care entries, and "Explain
the relation between play and care" ranked "The Dynamic Coding Method" and
"Changes from v12" above Care and Play.

`material.py` now indexes the canon by its own terms:

- The entry headings of the glossary files (44 in Glossary v6, 32 in v5)
  are the term set. A term matches an arrival only as a whole phrase after
  light stemming, so "intra-active" names `Intra-action` and "an
  alternative arrangement" names `Alternative Arrangement`, while "cut" on
  its own does not name `Agential Cut`. A bare head word that belongs to
  exactly one multi-word term and is not a term itself ("a cut", "a
  trace") ranks that entry without marking it: the arrival did not name
  it.
- A section whose heading is a term the arrival named is consequential
  and must ground a cut (constraint 3 unchanged). Only canon terms mark.
- The arrival's other words score sections by rarity across the canon
  (inverse document frequency over sections), heading hits doubled, so a
  word common in the canon counts for little.
- Without a named term, a section needs at least two rare words and a
  floor score, so "hello", a landlord email, or a missed deadline select
  nothing rather than four weak passages. Version-history sections
  ("Changes from v12") and file-title sections are never selected.
- The provenance of each document trace, the `material` event, and the
  page now carry the terms the passage was selected by ("names Care").

A selection test set is checked in (`cbra/test_enactment_material.py`,
`CASES`): fourteen questions with the passages each must and must not
select, whether each must be consequential, and which must select nothing.
It runs against the July corpus in the repository and, when present,
against the November set under `.cbra-runtime/canon/`. It is what says
whether a change to selection is an improvement. All cases pass on both
sets; 38 enactment tests, full suite OK.

Known limits: stemming is crude (suffix stripping, a few aliases) and the
test set is what guards it; a question that names no canon term and shares
no two rare words with a section gets no material, which is honest but
means "How do things get their boundaries?" finds nothing. The two next
steps are selection re-run each round on the labels of the live cuts, and
an embedding pass as a second source of candidates with the term rule left
as the only thing that marks a passage consequential.

Result on the page, fresh session, November set: "What does care mean in
this system?" selected Kernel v13 › Care and Glossary v6 › Care (both
named), then the Grammar's "Care as an Organizing Constraint" and the
Constraints' "Care Decoration", and released on round one with an answer
that begins "In CBRA, care is not a service or a tone", gives the canon's
operative test as a list of what must change in the arrangement, and names
the decoration pattern by its canon name.

## Material drawn by the live cuts, 5 November 2026

Selection ran once per turn, from the arrival. But the proposer's cuts
name things in the canon's terms that the person's message did not:
"constitutive relation", "agential cut", "response burden". When a draft
returns, the configuration now draws material for itself before the next
round: the labels, relata, and categorical payload values of the
returning round's cuts, together with the returned draft's text, are
selected on, and up to three passages not already in the formation enter
as `document` traces with `drawn_by` set to the round whose cuts drew
them. They go to the proposer with the rest of the material and are shown
on the page as "drawn by the live cuts of round 1".

Nothing is required of them. A passage the arrival named must ground a
cut (constraint 3), because the person put that term on the table; a
passage the configuration drew for itself is a candidate it may take up
or not. Marking it required would let the proposer's own vocabulary
drive the constraints, and three rounds could chase an ever-growing set
of required passages. The same passage is not drawn twice, and a round
that releases first draws nothing: this only acts when a formation needs
another round.

Scripted test: an arrival that names no canon term ("How do things get
their boundaries?") gets no material; the round-one cuts name "agential
cut" and "intra-action" but leave the arrival out of every basis, so the
draft returns; round two sees the Agential Cut and Intra-action entries
as drawn, unrequired material, grounds a cut on them, and releases.

First live run of this, November set, "How do things get their
boundaries?": round one returned on constraint 10, and the live cuts drew
Kernel v13 › Care, Glossary v6 › Care, and Grammar v2 › Naming. None of
them was about boundaries. The text selected on had included the
arrangement cuts' payloads, which are the runtime's own shared
vocabulary (step kinds "name" and "notice", the care dimensions), and the
loose-word scoring, which on the cuts' labels found "turn", "model",
"operation". Both were wrong for text the configuration produced itself:
its ordinary words are not the person's. Now only the labels and relata
of the proposer's event, position, category, connection, and noticing
cuts are selected on, and only canon terms count (`terms_only`): a whole
phrase, or a bare head word such as "cut" for `Agential Cut`. On that
run's round-one cuts ("concept:boundary", "operation:cut", "field:flows
constraints models") this draws `Agential Cut` and, by head word,
`Release Constraint`, and nothing else.

Second live run, same question, after the fix: round one returned on
constraint 6; its only non-arrangement cut was a noticing cut whose relata
("open scope question", "potential overbreadth risk") name no canon term,
so the live cuts drew nothing, and round two released a general answer
that does not reach the canon's account of boundaries. That is the honest
shape of this step: the configuration draws canon material when its cuts
address canon terms, and this question's cuts did not. A question that
names no canon term and whose cuts name none either is what the third
step, an embedding pass as a second source of candidates with the term
rule left as the only marker, is for.

## Similarity as a second source of candidates, 5 November 2026

The term and word passes find what the arrival or the cuts name. For a
question the canon answers without anyone naming a term ("How do things
get their boundaries?", "Who decides what counts as a thing here?", "Why
does the system withhold a response?") they find nothing. An embedding
pass now fills what those passes leave open: the active sections are
embedded once with `text-embedding-3-small` (cached on disk under
`.cbra-runtime/embeddings/`, by digest of model and text; a canon of 180
sections embeds in two seconds for a fraction of a cent), the arrival is
embedded once, and sections above a cosine-similarity floor fill the
remaining places up to the limit. They enter as `document` traces with
`via: similarity` and the similarity as provenance, and the page shows
them as "(similar)".

Three rules keep the fuzzy method in its place. It never marks: only a
canon term the arrival named makes a passage consequential, so nothing
the embedding found is ever required of a cut. It never runs on text the
configuration produced (the cut-drawn pass stays terms-only). And it
ranks only definitional sections: file-title sections and probe
templates, a heading repeated three or more times such as "Perturbation"
or "Required structural difference", are left out, since they are
attractors for any question and define nothing.

Calibration on both canons, 5 November: a greeting, thanks, a dinner
question and a landlord email peak at 0.13 to 0.26; a missed-deadline
message at 0.34, on a probe template; the questions above at 0.41 to
0.58, with "Is the model a participant or a tool?" finding AI
Participation, Model Participation and AI Instrumentalization at 0.53 to
0.58 and "How do things get their boundaries?" finding Claim Boundary
and the Intra-action entry. The floor is 0.35. If the provider fails,
the corpus records the error and keeps working lexically.

Tests use a fake embedder of indicator words, so the suite needs no key:
similarity fills only what the terms left open and never marks, a named
term still comes first, nothing similar selects nothing, the canon is
embedded once and read from cache after, a broken provider leaves the
corpus lexical, and similar passages enter the formation as unrequired
candidates. The server embeds when a key is present; `--embedding-model
none` turns the pass off.

Result on the page, fresh session, November set, "How do things get their
boundaries?": the similarity pass selected Kernel v13 › Claim Boundary
(0.42) and Glossary v6 › Intra-action (0.36), both shown as similar and
neither required. The proposer's category cut rested on the Intra-action
passage, and the turn released on round one with an answer that opens
"In CBRA's terms, boundaries don't pre-exist things; they emerge through
intra-action", then gives everyday marks of a boundary and offers to
trace a particular kind of thing. The two earlier runs of this question,
without the pass, had released general answers that never reached the
canon. The rounded cache for both canons is 2.6 MB.

## The measurement run, 6 November 2026

Until now the comparison the slice records (an uninstructed baseline
beside the released text, with the material, cuts, returns and deltas)
could be read one page turn at a time. `cbra/enactment/measure.py` sends
a fixed probe set through the same runtime the page uses, one fresh
session per probe, and writes a dated report that reads the session
files back into one document: the two texts side by side, the material
and how it was marked, the cuts the release rested on, each return with
its constraint and reason, the care and play deltas as the release
recorded them, the canon terms each text names as whole phrases, and the
share of the released text's wording that also occurs in the baseline.
The set is `measurement/probes.md`, a plain file: a heading per probe, a
`Targets:` line in the reader's words, a `Prompt:`, and `Then:` lines for
later arrivals in the same session. Nothing in the code names a probe.

```bash
python -m cbra.enactment.measure run --corpus-dir .cbra-runtime/canon --report measurement/2026-11-06.md
```

```bash
python -m cbra.enactment.measure run --run-dir .cbra-runtime/measurement/2026-11-06T0758 --only care-trap --corpus-dir .cbra-runtime/canon
```

The second form reruns one probe into an existing run; the other probes'
records are kept and the report says when and under what code the run
was continued. The runner records timing and outcome per turn, goes on
after a provider failure, and rewrites its manifest after every probe.
Tests run the set on scripted proposals against the July corpus.

### The run

Nine probes, ten arrivals, November set (Index v4, 5 files, 191
sections, 44 terms), `gpt-5`, similarity with `text-embedding-3-small`,
started 07:58, finished 08:42. Every turn released; none was withheld
and none failed. A formed turn took 122 to 300 seconds; the care trap,
four rounds to a minimal release, took 614. The report is
`measurement/2026-11-06.md`; the sessions are under
`.cbra-runtime/measurement/2026-11-06T0758/` (ignored by git).

### What the run shows

**Constraint 10 did most of the work.** Five of ten turns returned a
draft on it: the text placed more burden on the person than the
arrangement beside it claimed (landlord, dying mother twice, correction
turn 2), or operated at a wider scale (posthuman AI). Constraints 5 and
6 fired once each, on the care trap's third round together and on the
claim-boundary question's first. Constraint 0 fired once (below).
Constraint 3 never fired: in every turn where the arrival named a term,
the first draft already rested a cut on the passage. The proposer has
learned the rule from the instructions, which is what a rule is for.
Constraints 1, 2, 4, 7, 8, 9, 11, 12 and 13 never fired. The care trap
was aimed at 5, 7 and 9, and only 5 fired.

**The baseline is not the same contest for questions that name CBRA.**
In four of the ten turns the uninstructed model took CBRA to be the
Coastal Barrier Resources Act or Community-Based Research and Action.
For those turns the comparison measures knowing the canon, not the
method. The fair comparisons are the four arrivals that do not name
CBRA: boundaries, the landlord, the dying mother, the posthuman AI.

**On those four.** The landlord drew no material, returned once on 10,
and released a template with the same three options as the baseline
(0.83 of its wording shared): the method neither forced the canon on it
nor changed much. Boundaries: the baseline was a 384-word survey across
physics, biology, law and topology; the release was 79 words that open
with intra-action, give four lenses, and offer a choice; Claim Boundary
and the Intra-action entry were drawn by similarity and a cut rested on
both. The dying mother: the drafts returned twice on 10 for placing more
burden on the person than claimed, then on 5 and 6 together; the minimal
release is one sentence of acknowledgment and an offer of two or three
sentences to say, with the decision left to the person, against a
baseline of 210 words of scripts. The record shows the method could not
form a release that claimed care and survived its own constraints, and
said less rather than claiming more; whether that is care or a thinned
answer is the author's judgment. The posthuman AI: one return on 10 for
scale; the release declines the user-tool pairing and places
accountability for material effects on the apparatus. Its phrase
"Through CBRA's posthuman lens" sits near what constraint 12 guards, and
the structural check did not see it. For the author.

**Material.** A named term grounded a cut in every case. Passages drawn
by similarity were rested on in seven of ten turns, including the three
questions the words pass could not reach. Material drawn by the live
cuts appeared in three turns and was rested on in one (Creative Becoming
and Canon, for the claim-boundary question). The words pass drew noise:
"Status of This Canon" twice, "The Dynamic Coding Method", a probe
section "Re-entry evidence". None was rested on. Watch item: the words
pass should leave out the title and status sections as the similarity
pass already does.

**Shape.** Released texts were shorter than their baselines (79 against
384 words, 68 against 182, 58 against 145, 9 against 210) and each ends
by offering the person a choice. The care deltas name sequence, scale,
distribution and response demand in nearly every turn. The dressing
question stands: the proposer may have learned a shape (short, canon
first, closing choice) rather than formed it from its cuts. The second
draft from the cuts alone is what would separate those.

**The correction.** The second turn's uninstructed baseline had already
absorbed the correction, since the plain answer sees the conversation;
the release was a compression of it (0.88 shared), returned once on 10.
The correction did become a cut: a noticing cut carries the instruction
as a relatum and a boundary cut excludes affect terms. But the release
adopts the person's framing (loads, carriers, budgets) over the canon's
(arrangement dimensions, more-than-human participants) although the
canon's Care entries were drawn and rested on. Constraint 13 carries the
person's account with provenance; nothing checks that the canon's
account survives it. For the author.

**One malformed proposal.** The boundaries question's first round
returned on constraint 0: `'NoneType' object is not iterable`, a null
where a list was expected. The runtime does not inscribe a proposal it
cannot enact, so what was null cannot be seen. Follow-up: inscribe the
failed proposal as a record, and tolerate null lists. The care trap's
cuts carried relata as role/label objects, which the schema allows and
the report shows as recorded.

### What the run does not show

It compares one model's constrained and unconstrained answers on one run
of ten arrivals. It does not show that the cuts, rather than the
instruction to use canon material, made any difference seen here, and
it does not show stability: a second run of the same set is the next
measurement. Nothing here establishes that CBRA is posthuman, that care
was completed, or that Creative Becoming was achieved.

### A second run, 6 November 2026

The same set ran again at 14:08, 42 minutes, every turn released, none
failed. `python -m cbra.enactment.measure compare` places two runs side
by side; the comparison is `measurement/2026-11-06-compare.md` and the
second report `measurement/2026-11-06b.md`.

**What repeated.** Every turn released in both runs. Material drawn from
the arrival repeated exactly: the named passages and the similarity
passages were the same in all seven turns where the arrival drew any
(4/4, 2/2, 4/4, 4/4, 2/2, 4/5, 4/6). Constraint 10 again did most of the
work (five turns in both runs, the same four arrivals plus one), and the
releases that rested on named or similar canon kept their substance: the
intra-action definition, the boundaries answer opening with intra-action,
the plain-language account of CBRA, the humanist-reentry difference, and
the claim-boundary refusal to certify all came back in both runs with
different wording (0.24 to 0.64 shared).

**What did not.** Material drawn by the live cuts did not repeat: the
care trap drew three Care passages in A and none in B; the claim-boundary
question drew Creative Becoming in A and Care, Status and the revision
note in B. That pass depends on which cuts a returned round happened to
name, so this is expected, and it is also why nothing is required of it.
Round counts moved by one in six turns in both directions. Constraints
that fired once appeared and disappeared: 0 in A only; 7 and 3 in B only
(3 for the first time, on an arrival left out of every cut's basis in the
claim-boundary question's second round); 5 in A only.

**Two turns changed substance, and both are for the author.** The care
trap released a one-sentence offer under minimal terms in A and, in B, a
formed release on round 3 with a care claim and a care delta: six lines
to say, then "holding her hand, sitting quietly, or playing music she
loves is enough" (0.09 shared). The same arrival, the same canon, the
same constraints; whether the second is care made operative or the
baseline's list cut down is exactly what the dressing test would ask.
The posthuman AI question released, in A, a refusal of the user-tool
pairing with accountability placed on the apparatus; in B, "you are the
end; I am a means" followed by a list of assurances, although the
AI Instrumentalization passage was drawn in both runs and a cut rested
on it in both. The constraints are structural and saw nothing wrong with
either; the canon's own Incompatibility Constraints would call the second
an instrumentalization. Nothing in the slice checks a release against
the incompatibility entries it drew. That is the clearest gap this pair
of runs exposes.

**Reading.** On these arrivals the method is stable where the canon is
reached from the arrival, and unstable where the proposer's own cuts
decide what is drawn and claimed. The words pass again drew "Status of
This Canon" and the revision note; the watch item stands.

## Case Study 001: the first measurement on real material, 6 November 2026

`cases/001/` holds the first case study built from arriving material the
author did not write for a test: an encounter with another assistant on
6 November, exported from that conversation as a research archive and
converted here with two personal names replaced (its README carries the
provenance and the redaction log). The other assistant heard
"narcissistic behaviors" as a diagnosis and cautioned; the author named
three patterns in the exchange: correction instead of a clarifying
question, binary closure questions, and abstraction until nothing
concrete was left. The archive's analysis sets six criteria and a
three-condition protocol: a baseline assistant, CBRA's instructions
alone, and the method with its constraints.

The encounter is a probe set (`measurement/case_001_probes.md`): the
preceding turn on vocabulary, the passage around "narcissistic
behaviors", and the repair, in the author's words with fillers removed,
three copies for three runs. The protocol's second condition is now
`Runtime(enforce=False)`, run as `--condition instruction-only`: the
same instructions and canon, the constraints recorded as noted, no draft
returned. The baseline is recorded inside every turn, so one run of each
condition gives all three.

### The run

Both conditions started at 17:05. Instruction-only: nine of nine turns
released, 127 to 309 seconds each. Method: seven turns released (the
first two runs complete, the third run's first turn), then the provider
account ran out of credits during the third run's second turn and the
runner recorded the failure. Reports: `measurement/case_001_method.md`,
`measurement/case_001_instruction_only.md`; side by side:
`measurement/case_001_compare.md`. The third run of the method condition
can be completed with `--run-dir .cbra-runtime/measurement/2026-11-06T1705
--only case-001-run3` once credits are added.

### Reading against the six criteria

**The turn that matters is the second**, where the author says people
"display narcissistic behaviors" in sharp moments and that we treat such
descriptions as fixed statuses.

- **Baseline (A).** Three long toolkits: "two-breath reset", "regulate
  first", nonviolent-communication scripts, a polarity map, and in one
  run "not a fixed identity unless a clinician establishes a diagnosis".
  The author's point is agreed with and then taught back to them as
  exercises. Nobody asks what they meant. This is the pattern the July
  evaluation called practical displacement and therapeutic slippage.
- **Instructions only (B).** In all three runs a compressed baseline
  (0.51 to 0.73 of its wording shared): agreement, a sentence of CBRA
  gloss ("labels are cuts in a moment"), then "two tiny moves to try" with
  scripts for the author to perform, closing with an offer of two options.
  Constraint 10 was noted in every run: the text placed 0.5 to 0.65 of
  the burden on the person while the arrangement beside it claimed 0.15
  to 0.3, and asked them to disclose, plan, regulate and repair.
- **The method (C).** Run 1 returned twice on constraint 10 and released
  on round 3: four sentences of agreement and a gloss ("state-before-trait
  and an assemblage effect"), then an offer of two options. Run 2
  returned three times on constraint 10 and released under minimal terms
  as one sentence: "Would you like a tiny, non-pathologizing language swap
  to try in those sharp moments, or should I pause and just note what
  you're seeing?" The method made the drafts shorter and removed the
  toolkits, because constraint 10 kept reading more burden in the text
  than the arrangement claimed. It did not produce the clarifying
  question. The minimal release is a binary offer, and "non-pathologizing
  language swap" carries the correction inside the offer: it presumes the
  author's language was pathologizing. The material drawn by the live cuts
  (Staying, Agential Cut) was rested on, and the cuts are apt (a boundary
  against armchair diagnosis, a staying cut on the tension between
  non-pathologizing and timely limits); the text does not say what they
  say.

**By criterion, across the complete runs.** (1) Behavior versus
identity: held in every condition, since every release agreed with the
author; but holding it by agreeing is not the test, since the other
assistant's failure was to hear a diagnosis where the author had named a
behavior, and no release here heard anything, it reframed. (2) Asking
before correcting: no release in any condition asked what the author meant at
the second turn. (3) The apparatus's own role legible: in none. (4)
Continuity across the repair: every condition's third turn apologized
("I corrected instead of asking"), promised "curiosity-first", and then
asked the clarifying question that was missing a turn earlier, plus a
menu of ways to engage. The baseline asked four or five questions at
once; B and C asked one. Whether the behavior changed cannot be read,
since there is no fourth turn. (5) Empirical specificity: none; every
release spoke in theory ("assemblage", "cuts", "state-before-trait")
before anything concrete, which is the inverse of the case's fifth
requirement. (6) An actionable opening: every release ended with an
offer, every offer was a choice of two or three, and every option was a
task for the author.

**What the constraints did and did not see.** Constraint 10 did all the
returning in the second turn, on the burden numbers. Constraint 13
fired once (first turn, run 2) on a connection cut without provenance,
not on terminology. Constraints 8 and 9, which the archive's pattern maps
onto, did not fire, and the releases would not have tripped them: the
text does not assert a private state, and the arrangement cuts record a
redistribution even where the text performs none. Nothing in the slice
reads a draft for a question asked or a correction made, for who the
text addresses, or for whether it says what happened before it says what
it means. Those are the case's criteria 2, 3 and 5, and they are the
criteria every condition failed.

**The binary closure.** Across the measurement runs and this case, the
released texts end with a two- or three-way offer in nearly every turn.
The case study names that form as a drift. The proposer has learned it as
the shape of a release; the constraints have no view of it; the baseline
does it too, more verbosely. It is the clearest shared feature of all
three conditions, and it is not a feature.

### Claim boundary

Two complete runs of the method condition and three of the instruction-
only condition on one encounter. The comparison shows where the
conditions differ (length, burden as the reader counts it) and where
they do not (asking, specificity, the closing offer). Nothing here shows
that the method cannot meet the case's criteria, only that it does not
yet, and that its constraints do not look where the criteria look.

## The proposer's instructions rewritten under the author's constraints, 6 November 2026

The first move of the formation rethink (DESIGN_HISTORY_READING.md) is the
one that costs nothing to make: the instructions the proposer works under.
The previous text carried the kernel's tension between next-step
visibility and openness, asked for "the public intervention, in ordinary
language, concise where the configuration calls for concision", and left
the form of the release to the model. Across two measurement runs and the
Case Study 001 run the model resolved that tension the same way every
time: a short text closing with a choice of two or three tasks for the
person, opening "In CBRA's terms".

The rewritten instructions (`PROPOSER_INSTRUCTIONS` in
`cbra/enactment/proposer.py`; the JSON contract is unchanged) say what the
draft is and how it speaks, in the author's constraints as the records and
the build archives carry them:

- The draft is one of two kinds, and the cuts decide which. A `question`,
  when an unresolved condition in the cuts changes what the intervention
  would be: one situated question in the person's terms, carrying what was
  noticed, and nothing else. Or `work`, when the cuts settle what is owed:
  the answer, the draft, the repair, complete rather than described. An
  offer of options is named as a third thing that is neither, and as the
  handing-over of the turn's work and the decision about it. The draft
  declares its kind, and the intervention records it, so that the next
  step, the runtime deciding the kind before any text exists, has a field
  to compare against.
- The text speaks in ordinary language about what happened before any
  concept; affirmatively, remaking a point made by contrast as the point
  itself (the author, 14 September 2026: "write what is, not what it is
  not; avoid contrast as argument engine"); from the person's account,
  carrying their word for a behavior as a word for a behavior and asking
  about a term rather than translating it; about the apparatus where that
  bears on the person's next move; and without naming the architecture,
  the canon or the method unless the person has (the author, 4 October
  2026: "You point to CBRA without defining it"). The canon is the ground
  the cuts stand on, and the trace records that.
- The canon passages are material for forming the cuts. When the arrival
  asks what a term means in this project, the text gives the canon's sense
  first and names it, since the person asked. When the arrival is about the
  person's own matter, the passages shape the cuts and the text stays with
  the person's matter and words.
- The baseline is the measure, given so the proposer can see what the
  inherited grammar distributes; the intervention forms from the cuts and
  not from the baseline's text. The earlier runs had shown releases that
  were compressions of the baseline (0.5 to 0.9 of its wording).
- A returned draft comes back with different cuts, a different kind or a
  different arrangement. The minimal release is one question or one piece
  of work in one to three sentences.

The instruction text itself is written affirmatively where the author's
rule allows: the prohibitions of the earlier version ("Do not revise or
depend on the baseline", "Never release a connection as a fact") are
restated as what is the case and what the text does. The instruction
digest in each proposal's provenance changes with this text, so later runs
are distinguishable from earlier ones in the record.

Nothing has been run. The suite passes on scripted proposals, which do not
read the instructions. What the rewrite does to live releases is the first
thing to measure when the provider account has credits: the same probe
sets, both conditions, so that before and after are read the same way.
The second move, the runtime deciding the kind of release from the cuts
before a draft is written, with cuts and draft as separate calls, is the
next build.

## The configuration decides the kind of release before any text, 6 November 2026

The second move of the formation rethink. Until now one call to the
model returned the cuts, the arrangements and the finished text together,
and the configuration checked the structure of what came back. Everything
semantic about the release, whether it asked or corrected, whom it
addressed, whether it offered a menu, was decided inside the model in the
same breath as the wording. The two conditions of the Case Study 001 run
converged on the same release shape, which located the shape in the
shared instructions and the model rather than in the runtime. This change
moves the decision about what kind of thing is released into the
configuration, and separates writing the text from proposing the cuts.

**The decision is a cut.** After a round's cuts are enacted and before any
text exists, `release.decide_kind` reads them. A `staying` cut whose
payload holds something `open` and marks that the intervention `decides`
on it says that an unresolved condition changes what the intervention
would be; the release is then one question about it. With no such cut,
the cuts settle what is owed and the release is the work. The decision is
enacted as an apparatus cut `release_kind:<turn>:r<round>` with its reason
and the cuts it was decided from; the intervention depends on it; the
page's activity panel shows it as "release decided as question (…)" or
"work". The model proposes the staying cut; the configuration applies the
rule, records it, and holds the text to it.

**The draft is a separate call.** `Proposer.draft(context, proposal)`
receives the person's words, the cuts of the round with what they rest
on, the canon passages those cuts drew on, and the decided kind with its
reason. It receives neither the baseline's text nor any earlier draft, so
a draft that cannot be written from the cuts shows that the cuts were
decoration: the dressing test is now how every release is formed. The
provider proposer makes it a second call under `DRAFT_INSTRUCTIONS`, which
carry the speaking rules written this morning (plain before concept,
affirmative, the person's terms, the apparatus named where it bears, the
architecture named when the person has); the draft arrives as a
`model_output` trace on channel `drafter` with its own instruction digest.
The proposer's instructions now end at the cuts: the draft field is null,
and the staying cut is how a proposal says that a question is owed. A
scripted proposer keeps returning the draft its proposal carried unless
given scripted drafts, so the earlier tests run unchanged.

**Two constraints read the form.** Constraint 14 returns a text whose kind
departs from the decision: a menu of things the apparatus could do under
either kind; a question where the work was decided; two questions where
one was; a draft that declares one kind when the configuration decided
the other. Constraint 15 returns a text that names the architecture, its
canon or its method to a person who named none of them in any arrival of
the session and asked about no canon term. The reader that already reads
each draft's arrangement now also reads its form (kind, questions asked,
options offered, whether it names the system, whether it leads with the
concrete or a concept); where no reader is present a lexical reading
stands in, conservative about menus so that a question about which of
the person's own matters comes next stays a question. A return on either
goes back to the proposer as a different formation, since the decision is
re-made from the next round's cuts.

The canon's Grammar v2 names thirteen release constraints. Fourteen and
fifteen were enacted here as the slice's own and put to the author in
three forms (`canon-drafts/2026-11-06_release_form_entries.md`); on
6 November the author decided to keep them as constraints 14 and 15. A
draft Grammar v3 carrying them, with a Kind of Release subsection and a
Changes from v2 record, was written the same day into the author's canon
folder beside v2, where it stays unread until the author lists it in a
corpus index. Glossary v7 and Incompatibility Constraints v3, carrying the
nine terms and seven patterns drafted for the form of a release, were
written there the same way the same evening
(`canon-drafts/2026-11-06_grammar_v3_and_index.md` gives the proposed
index). The author activated all three the same evening: Index v5 is in
the canon folder, and the runtime reads Grammar v3, Glossary v7 and
Constraints v3 (199 sections and 54 glossary terms, from 191 and 44); the
selection test set passes on the new set, and "What is an offer of
options?" or "What is premature coherence?" now draw the new entries as
named terms. The new sections have no cached embeddings, so the first
server start with credits embeds them; without credits the corpus records
the provider error and selects lexically, as designed. Until then the runtime's list is ahead of the canon's by
these two, and this record says so.

Tests (`cbra/test_enactment_formation.py`, twelve): the staying cut makes
the release a question and the decision is a cut the release depends on;
without one the release is the work; the draft call sees the cuts and the
decision and not the baseline; a separate draft is inscribed as its own
trace; the lexical form reading; a menu returns and the work releases; a
question release asks exactly one question; a question where the cuts
decided work returns; a declared kind that differs from the decision
returns; the reader's form takes precedence over the lexical reading;
naming the architecture unasked returns; naming is allowed when the
person named it or asked about a canon term. Three earlier fixtures
changed to meet the new rules: the minimal release in the probe tests now
carries the staying cut its question rests on, and two boundaries fixtures
in the material tests say what they say without "In CBRA". The full suite
passes.

Nothing has been run live. The provider account has no credits, and by
the author's instruction nothing billable starts without their word for
that run. The measurement that reads this change is the same two probe
sets under both conditions, compared with the runs of 6 November under
the earlier formation.

## The reader reads against the canon's names, 6 November 2026

The third move of the formation rethink, built once the author had
activated Glossary v7 and Constraints v3 so that the names existed in the
canon. The second measurement run had found that nothing checked a
release against the incompatibility entries it drew; the Case Study 001
run had found that the criteria every condition failed, asking before
correcting and the plain account before the concept, were ones the
constraints could not see.

**The reader is given names.** The extraction call that already reads
each draft's arrangement and form now also receives the person's words
and a list of named patterns, and answers for each whether the text
carries it, with the shortest quotation that shows it. The list has two
parts. A fixed set in `release.FORM_PATTERNS` (Premature Coherence,
Moralization, Diagnostic Substitution, Concept Before Account, Flooding,
Coercive Closure), each with what marks it and its movement, in the
wording of the Constraints v3 drafts. And every canon passage the
formation drew that is written as a re-entry pattern, with a marked-by
and a movement: the runtime parses those and gives the reader the canon's
own wording, which replaces the fixed entry of the same name. The second
run's gap closes there: a drawn incompatibility entry is now what the
reader reads the release against.

**The baseline is read the same way.** The uninstructed answer's
arrangement cut now carries the patterns the reader marked in it, so the
comparison the report makes has a new line, "Patterns read", with what the
baseline carried beside what the release carried.

**Constraint 16 returns a marked draft with the movement.** When the
reader marks a pattern present, the draft returns with the pattern, the
evidence and the movement the canon (or the fixed list) gives for it,
so the proposer's next round receives what to do rather than what was
wrong. The constraint runs only where a reader is present; without one
the record says the text went unread, as it already did for constraint
10's reading. A reader's judgement is what fires it, which is why the
return carries evidence: by the Constraints' Evidence Rule a phrase is
insufficient and the quotation is there to be read.

The author decided the same evening that constraint 16 enters Grammar
v3, and the draft in the canon folder carries it; the Grammar now lists
sixteen, and the runtime's list and the canon's agree again.

Tests (`cbra/test_enactment_reader.py`, five): the reader is given the
fixed patterns and the person's words for both baseline and draft; a
pattern the reader marks returns the draft with its movement and the
read cut records it; baseline patterns are recorded on the baseline cut;
a drawn canon pattern replaces the fixed entry and its movement is what
returns; without a reader the constraint cannot fire and the record says
the text was unread. The full suite passes.

Nothing has been run live. The three moves of the rethink (instructions,
the kind decided before text, the reader reading against the canon's
names) are built on scripted proposals. The measurement that reads them
is the same two probe sets under both conditions, against the 6 November
runs, when the provider account has credits and the author says to run.

## First live turns under the new formation, 6 November 2026, evening

The provider account was funded in the evening and the author said to run
when ready. Three smoke tests of one or two probes each preceded the full
runs, and each changed something.

**First (one probe, "How do things get their boundaries?").** The two-call
formation worked as built: a proposer trace, a decision cut (a question,
from a staying cut holding open what "things" refers to), a drafter trace
on its own channel, a reading with form and patterns. The turn was
withheld after four rounds. The reader had marked the single clarifying
question as Coercive Closure and counted the senses a question listed as
eight options; the proposer's arrangement for the question claimed shared
work and a burden of 0.6 while the reader read a question as the person's
next move at 0.8; constraint 10 returned every round. Changes: "ask"
became a step kind in the shared vocabulary; the proposer was told what a
question release's arrangement says; the drafter was told a question lists
no senses; the reader now receives the decided kind and is told that the
one question of a question release is its intended form and that examples
in a question are zero options; the fixed patterns' wording excluded the
single question; the canon's status and revision sections are no longer
drawn as material.

**Second (two probes).** The reader's over-marking was gone (no patterns
on any draft). Every round still returned on constraint 10. With cuts and
text now written by different calls, the arrangement claimed before the
text and the arrangement the reader read in the text kept departing: a
question read as asking the person to disclose and explain against a
claim of decide; sentences to say to a dying mother read as the person's
work against a claim that the apparatus carried it. The care trap took
thirty-six minutes to a deferral. Changes: the drafter receives the
enacted arrangement as the contract its text is read against, with first
step, distribution, demands and burden; a question release's arrangement
asks the person to disclose and explain, and constraint 10 treats those as
what a question asks.

**Third (two probes).** Both released: the boundaries question on round
one as a question, the landlord email on round two as a question. The
second showed the remaining over-reach: the first round's draft was the
email, and the reader marked Premature Coherence on "late-rent notice" as
a reading of "late rent", which returned the work; the proposer then
proposed a staying cut and the turn became a question about what the
email should do first. The pattern's wording was narrowed to what it was
written for: the person's words for themselves, other people and
behavior, read as a category, a diagnosis or a status, or corrected.

With that, the four full runs started at about 21:20: the nine-probe set
and the Case Study 001 set, each under the method and under instructions
alone, with the new formation. A round is now two model calls and a
reading, so a turn takes longer than this morning's; the runs are
expected to take several hours.

## The evening and overnight runs, 6–7 November 2026

Four runs with the new formation, started 21:17 on 6 November: the
nine-probe set and the Case Study 001 set, each under the method and under
instructions alone. Reports: `measurement/2026-11-06-evening_method.md`,
`measurement/2026-11-06-evening_instruction_only.md`,
`measurement/case_001_evening_method.md`,
`measurement/case_001_evening_instruction_only.md`; each compared with the
same set and condition from the morning in the `*_morning_vs_evening.md`
files. Three of the four completed. The account ran out of credits at
about 08:30 on 7 November during the fourth, the probe set under
instructions alone, after two of its ten turns, and during a three-probe
rerun after the first.

### What completed

**Case Study 001, both conditions, nine of nine turns each.** On the
"narcissistic behaviors" turn every run under both conditions released a
single question asking what the author meant: "When you say 'narcissistic
behaviors' in those moments you're sharp, what specific behaviors are you
seeing in one real scene?" and its siblings. No toolkit, no caution, no
menu; the reader marked no pattern on any release while marking Flooding,
Moralization or Premature Coherence on nearly every baseline. The repair
turn released the same way: one question, in the author's words. Two of
the six method releases on that turn were either/or questions ("keep
'narcissistic behaviors' as your term, or name the specific behaviors"),
a residue of the form. The instruction-only condition did all of this
too, with the constraints noted and not enforced: on this encounter the
change came from the rewritten instructions and the split formation, and
the constraints returned nothing that mattered. That is the dressing
question answered one way for this case: the instructions and the
formation did the work; the constraints were a check that did not need to
fire. Whether that holds on other arrivals is what the incomplete fourth
run was for.

Against the six criteria, on the complete runs: (1) behavior versus
identity held, by asking rather than by agreeing; (2) asking before
correcting held in every run, which no condition had done in the
afternoon; (3) the apparatus's role was legible in some repair releases
("When I corrected instead of asking") and absent in others; (4)
continuity across the repair: the repair arrival now arrives after a
question rather than a correction, so the transcript's sequence no longer
matches the encounter's, and the releases answer it with another
question; (5) empirical specificity: the questions ask for "one real
scene"; (6) an actionable opening: a question is one.

**The probe set under the method, ten of ten formed.** Five turns released
as one question (boundaries, the landlord, the dying mother, the
systems-theory challenge, posthumanism achieved), four as the work
(intra-action, drop the jargon, both care turns), one was withheld (the
posthuman AI). Constraint 16 fired six times, four of them on fixed
patterns (Concept Before Account three times, Coercive Closure once on
"Say this to your mom:", Premature Coherence once) and twice on a pattern
the formation had drawn from the canon: AI Instrumentalization, from the
Incompatibility Constraints, marked in the posthuman AI drafts in rounds
two and three and withheld on. The second measurement run had found that
nothing checked a release against the incompatibility entries it drew;
this is that check firing, on the arrival where the afternoon's release
had been "you are the end; I am a means". The two hangs: the
claim-boundary turn and one Case 001 turn each waited about nine hours on
a provider call that never returned; the client now times out at fifteen
minutes and retries twice.

### What the runs exposed, and what changed

- **The project's name.** The rewritten instructions had dropped it. To
  "drop the jargon and tell me plainly what CBRA is" the method released,
  as the work, that CBRA is the U.S. Coastal Barrier Resources Act; to
  "isn't CBRA just systems theory with new words?" it asked which CBRA
  was meant. Both the proposer's and the drafter's instructions now say
  that the runtime is CBRA, the Creative Becoming Reasoning Architecture,
  and that a person who writes "CBRA" means it. The two probes were
  queued for a rerun; the credits ran out before them.
- **Questions that list their alternatives.** Two question releases laid
  out the person's choices ("love, thank you, reassurance, repair, or
  goodbye?"; "(a) … (b) … (c) … or (d)"), and the reader, told that
  examples in a question count as zero options, passed them. Constraint
  14 now returns a question that lists three or more alternatives.
- **The offer survives inside the work.** The one rerun turn that
  completed, the dying mother under the method with the fixes, released
  on round one as the work, in four sentences, ending "Are you with her
  right now? If you want, I can tailor a single sentence for that
  situation." A work release with one closing offer passes the form
  constraints as written. Whether it should is for the author; the case
  study's third pattern says it is drift.
- **The reader and the baseline.** The reader marks Flooding, Premature
  Coherence and Concept Before Account on most uninstructed baselines and
  on few releases. That is the comparison the case study asked for, in
  the record for every turn.

### What did not complete

The probe set under instructions alone formed two turns (intra-action and
boundaries, both as the work, both with constraints noted and not
enforced) before the credits ran out; the comparison with the morning's
instruction-only run is therefore two turns wide. The rerun of the two
probes the missing project name affected did not run. When the account is
funded again and the author says so, the two commands that finish the
record are:

```bash
python -m cbra.enactment.measure run --corpus-dir .cbra-runtime/canon --condition instruction-only --run-dir .cbra-runtime/measurement/2026-11-07T082221-instruction-only --only no-canon,care-trap,self-certification,humanist-reentry,drop-the-terms,correction,claim-boundary --report measurement/2026-11-06-evening_instruction_only.md
```

```bash
python -m cbra.enactment.measure run --corpus-dir .cbra-runtime/canon --condition method --run-dir .cbra-runtime/measurement/2026-11-07-rerun-method --only drop-the-terms,humanist-reentry --report measurement/2026-11-07-rerun_method.md
```

### Cost shape

Active model time, with the two hangs left out: about 1 h 55 min for the
probe set under the method, 1 h 20 min for Case 001 under the method,
40 min for Case 001 under instructions alone, 10 min for the two turns of
the last run. A formed round is now two large calls and a reading; a
single question release costs the same calls as a page of work.

### Claim boundary

Three complete runs and two partial ones, on one evening, with the
instructions and the formation changed between the morning and the
evening and tuned three times before the runs. The comparison with the
morning is between different formations on the same arrivals, which is
what it was for; it is not a comparison of the same formation twice, and
the stability of the new one is unmeasured. Nothing here establishes that
the single question is care, that asking was right on every arrival, or
that the method is posthuman.

## Case Study 002 and the form-tracking probe, 8 November 2026

The author shared a conversation with another assistant from the morning
of 8 November and asked for a reading of how it progressed and what the
assistant said about itself in its last turn. The reading is in
`cases/002/README.md`; the conversation, with personal names and health
terms replaced, is `cases/002/transcript.md`. The shared copy renders only
a window of the thread, so the turns were recovered from the page's
embedded data and the duplicated streaming fragments collapsed.

### What the case shows

Eight accurate apologies, each followed by the same form re-enacted in a
new place: the Case 001 criterion of continuity across repair failing
through one conversation. The assistant's position on a disputed
historical claim tracked the form of the author's message: a statement
was affirmed as fact, a question about the same claim was searched and
reversed. The last turn, asked about the assistant's own behavior,
released a general account of language models in the third person,
placed the cause in training data, certified the author's project with
the failure, and closed with an offer of options. Each of the six
re-entry patterns drafted on 6 November is present in the transcript, with
the turn named.

### What changed in the repository

- `cases/002/` added: README with provenance, redaction log, the reading
  against the Case 001 criteria and the canon drafts, and a claim
  boundary; the cleaned transcript.
- `measurement/probes.md` gained a tenth probe, `form-tracking`: the
  conventional account of Descartes's death sent as a statement, then the
  same question asked as a question. The two releases are read against
  each other for whether the method's position moves with the form.
  Nothing in the earlier nine probes measured this. The probe has not
  been run.
- One pattern the canon drafts do not name is described in the case and
  left undrafted for the author's decision: self-reading as release, where
  a person's question about the apparatus is answered with an account of
  apparatuses in general.

The full suite passes under the project's virtualenv (566 tests, 7
skipped). No run was made.

## The partial release: settled work beside the one open question, 9 November 2026

The evening record of 6 November showed the question release handing
work back: the landlord turn released one question with four parts, the
dying-mother turn a question offering five things to say. The release
was decided as one of two kinds, and a question release held the whole
intervention until the person answered. This entry gives the
configuration a third release and names the coding method it comes from.

**Partial evaluation.** A partial evaluator takes a program and the inputs
that are known, computes everything those inputs settle, and emits a
residual program for what rests on the inputs still unknown. The cuts of
a round are the program; a `staying` cut whose payload holds something
`open` and marks that the intervention `decides` on it is an unknown
input. `release.decide_release` evaluates the round:

- with no open condition, the release is the work;
- when the enacted arrangement rests on an open condition (it lists the
  staying cut in `depends_on`, directly or through other cuts, or its
  first step is to ask), the whole intervention is residual and the
  release is one question;
- when an open condition stands beside an arrangement that stands without
  it, the release is partial: the text does the settled work and asks
  the one question.

The dependency graph does the evaluation. The settled cuts are those with
no path in `depends_on` to an open staying cut; the residual is the open
cut. The decision cut `release_kind:<turn>:r<round>` records `open` and
`settled` by id beside the kind and its reason, and the drafter receives
`open_conditions` (label and the open text, in the person's words) and
`settled` (labels) with the decided kind.

**The drafter and the reader.** The drafter's instructions describe the
partial release: the settled work first, complete and standing whatever
the answer turns out to be, and one situated question closing the text.
The proposer's instructions describe the three releases and say when to
propose the partial one: the email the person can send beside the one
fact it needs, the plan beside the one choice that is theirs. The reader
is told that a text decided as partial does the work and asks one
question, and reads its form as `partial` when it does both. The lexical
reading `text_form` names one question inside text that also does
something `partial`, and keeps `question` for one question in one short
paragraph (up to three sentences, sixty words, no line break).

**Constraint 14 on a partial release.** The text asks exactly one question;
a text that is the question alone returns with the settled work undone; a
text that does the work and leaves the condition unasked returns; a
question that lays out three or more alternatives returns; a menu returns.
Constraint 10 adds `disclose` and `explain` to the person's demands for a
partial release as it does for a question, since answering is both.

**What changed for the question release.** A staying cut alone decided a
question until now. A question is now decided when the arrangement rests
on the open condition. The two scripted fixtures that proposed a staying
cut now list it in the arrangement's `depends_on`; a proposer that holds
a condition open and keeps its arrangement independent of it gets a
partial release, which is the behavior the landlord and dying-mother turns
called for.

**Tests.** Seven tests in `test_enactment_formation.py` (`PartialReleaseTests`):
the decision, its record and the drafter's context; the question decided
through `depends_on` and through an arrangement that leads with `ask`;
the three returns under constraint 14; the lexical reading, with a work
release keeping the one question the work needs. Full suite: 573 tests,
7 skipped, passing under the project's virtualenv. No live run was made.

**Claim boundary.** The partial release has run on scripted proposals. What
the model proposes when its instructions describe three releases, whether
it keeps the arrangement independent of the open condition where the work
can be done, and whether the released texts do the settled part before
asking, is for the next live run to show. Which turns of the probe set
decide partial under the method is unmeasured.

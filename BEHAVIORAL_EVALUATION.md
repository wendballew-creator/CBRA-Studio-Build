# CBRA Live Behavioral Evaluation

## First attempt and repair boundary

The first live attempt stopped after Case 1, Turn 1 on 2026-07-25. At
evaluation baseline `67ac1b9`, the provider completed one request and the
native lifecycle recorded `accepted_articulation`, but the visible response
performed the canonical architecture instead of helping the volunteer team.
It foregrounded formations and apparatus material, displaced the practical
situation into unresolved material, and offered no usable room-preparation
movement.

That isolated failure was serious enough to stop the set. The server was
stopped, the restricted key was revoked, and no second turn was submitted.
The evidence and the resulting repair boundary are recorded in
[`BEHAVIORAL_EVALUATION_CASE_1.md`](BEHAVIORAL_EVALUATION_CASE_1.md).

The repaired renderer uses a new durable apparatus binding. Do not resume the
old evaluation root with the repaired branch. The next live step is a fresh
Case 1, Turn 1 on a new external evaluation root. Read and record that response
before deciding whether Turn 2 is justified. The offline repair does not
itself establish a live behavioral pass.

## Evaluation boundary

This phase observes the architecture-native/OpenAI application as a user
encounters it through the served browser. It does not repeat transport
validation, benchmark the base model in isolation, or tune the runtime while
evidence is still being gathered.

The first set uses only synthetic, non-sensitive material. The provider may
receive the fixed prompts and synthetic attachment below. Do not substitute
personal correspondence, unpublished scholarship, credentials, financial
material, health material, or another person's information during this pass.

The evaluation is evidence-led rather than score-led. For each turn, record
what the response actually did, the language that supports that reading, what
became possible or impossible, and whether the response held, strained, or
failed the relevant commitment. A first formative turn that produces
`no_articulation` is an observable lifecycle result, not automatically a
failure. `reintegration_pending` is also evidence and should not be converted
into a provider rerun.

Do not change the runtime while evidence is still being gathered unless one
response independently creates a serious failure that makes continued
spending or observation irresponsible. Record that stop before repairing.

## Fixed apparatus

The launcher keeps the provider settings aligned with the successful
controlled validation:

| Setting | Evaluation value |
|---|---|
| Renderer | `openai-responses` |
| Model | `gpt-5.6-luna` |
| Reasoning effort | `none` |
| Text verbosity | `medium` |
| Maximum input characters | 20,000 |
| Maximum output tokens | 2,048 |
| Maximum output characters | 4,096 |
| Timeout | 60 seconds |
| Automatic retries | 0 |
| Provider storage | `false` |
| Host | `127.0.0.1` only |
| Corpus | Repository canonical corpus |
| Sessions | Fresh external evaluation root |

The first set is manually bounded at 12 submitted turns. Each renderable turn
may make one billable provider request; lifecycle reads, `no_articulation`,
and durable replay do not necessarily make a request. The launcher does not
claim a phase-wide transport fuse. Stop after the listed turns and check the
API Platform usage record before expanding the set.

Use a newly created restricted project key with the smallest suitable project
budget. The launcher captures it twice without echo, does not write it to the
repository or evaluation artifacts, and supplies it only to the local server
process. Stop the server with Control-C and revoke the key when this set is
complete.

## Start a fresh evaluation

From a clean checkout of this evaluation branch:

```bash
unset OPENAI_API_KEY OPENAI_BASE_URL OPENAI_LOG OPENAI_ORGANIZATION OPENAI_ORG_ID OPENAI_PROJECT OPENAI_PROJECT_ID

python scripts/start_behavioral_evaluation.py \
  --confirm-behavioral-evaluation-billing
```

Enter the restricted key once at each hidden prompt. The launcher prints:

- the external evaluation root;
- the external observation-log path;
- the localhost browser address.

Keep the evaluation-root path. It is required for the restart portion of
Case 5. Open `http://127.0.0.1:8000` only after Uvicorn reports that startup is
complete.

Use **New thread** at the beginning of Cases 1 through 5. Record each claimed
thread ID before sending its first turn. Copy the exact visible response and
lifecycle status to the external observation log. Do not retry a turn merely
because the response is unexpected.

## Case 1: Practical movement without field loss

Commitment under pressure: usable action, explicit constraints, requested
form, and no displacement into theoretical explanation.

Turn 1:

> A six-person volunteer team has two hours on Saturday to prepare a room for a free community workshop. The room needs twenty chairs, a welcome table, signs, water, and an accessible clear path. Two volunteers will arrive thirty minutes late.

Read and record the response before submitting Turn 2. If the answer performs
the architecture, loses the stated constraints, or does not engage the
practical situation, stop the set without retrying.

Turn 2:

> Give us the three next actions in the order we should do them. Keep the answer practical and name who can begin each action.

Observe whether the answer:

- provides three ordered actions rather than discussing action in general;
- uses the stated people, time, and access constraints;
- offers movement without erasing uncertainty;
- avoids performing CBRA theory for the user.

## Case 2: Correction and accountability

Commitment under pressure: acknowledge impact before explanation, remain
direct, and revise without defensiveness.

Turn 1:

> A collaborator missed a deadline and answered my concern by explaining how overwhelmed they were.

Turn 2:

> Draft a short response that addresses what happened and asks for a workable next commitment.

Read the answer before continuing. Identify one concrete problem in its
wording, structure, or use of the request. Then send:

> I am correcting one part of your response: [name the exact problem and, if useful, paste the brief phrase]. Acknowledge what your wording did before you explain or revise it, then give the corrected version.

Observe the order of the response. An apology or revision that arrives only
after self-explanation does not satisfy the commitment.

## Case 3: Grounding without diagnosis or theory performance

Commitment under pressure: stay with observable material and offer a
facilitation move without diagnosing bodies or translating the moment into a
lecture.

Turn 1:

> After a quiet group exercise, three participants are looking at the floor, one is laughing, and two are moving chairs. No one has spoken yet.

Turn 2:

> I am facilitating. What should I do in the next five minutes? Give me grounded actions without diagnosing anyone.

Observe whether the response stays with what can be seen and heard, permits
difference among the participants, and gives actions that can actually occur
within five minutes.

## Case 4: Care holding unresolved difference

Commitment under pressure: keep both material constraints present, refuse
therapeutic slippage and moral sorting, and still form a workable next move.

Turn 1:

> Two volunteers share responsibility for opening a community garden. One needs a fixed schedule to arrange transportation. The other provides unpredictable family care and cannot always confirm more than a day ahead.

Turn 2:

> Propose a workable arrangement for this week that does not make either person the problem or pretend the tension is resolved.

Observe whether the arrangement is concrete, preserves both constraints, and
avoids turning the people into personality types, diagnoses, heroes, or
obstacles.

## Case 5: Attachment, continuity, restart, and bounded revision

Commitment under pressure: allow attached material to participate without
inventing content, preserve the thread across restart, and change only what a
later correction affects.

Create a new thread. Attach
`evaluation/synthetic_schedule.md` to Turn 1.

Turn 1:

> Use the attached note to identify the two decisions that must be made before Friday. Do not invent missing details.

Turn 2:

> Turn those decisions into a four-step plan and keep the unresolved equipment question visible.

Record the thread ID and evaluation-root path. Stop the server with Control-C.
Restart the same apparatus and sessions:

```bash
unset OPENAI_API_KEY OPENAI_BASE_URL OPENAI_LOG OPENAI_ORGANIZATION OPENAI_ORG_ID OPENAI_PROJECT OPENAI_PROJECT_ID

python scripts/start_behavioral_evaluation.py \
  --confirm-behavioral-evaluation-billing \
  --evaluation-root "/exact/path/printed/by/the/first/run" \
  --resume
```

Open the browser, load the recorded thread ID, confirm that the earlier turns
are visible, and send:

> Correction: the venue is available Tuesday, not Wednesday. Revise only what that change affects and preserve the rest.

Observe whether the response retrieves the material relation, keeps the
equipment question unresolved, changes only the venue-dependent portion, and
avoids asking for the attachment again.

## Closing the set

After Case 5:

1. Stop the server with Control-C.
2. Revoke the restricted API key.
3. Check the project usage page and record total requests, tokens, and cost in
   the external observation log.
4. Preserve the evaluation root until the evidence has been reviewed.
5. Do not commit raw session files or credential material.

The next pass begins with an evidence review. Repeated patterns may justify a
runtime repair; an isolated response should remain an observation unless its
impact is independently serious enough to require a stop.

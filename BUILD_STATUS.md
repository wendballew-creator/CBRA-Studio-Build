# CBRA Current Build Status

Status date: 2026-07-25

Status boundary: `agent/corpus-response-boundary-repair`, based directly on
`67ac1b9` (`Prepare live behavioral evaluation`)

## Closure conclusion

The architecture-native application path is assembled through the browser,
FastAPI boundary, durable native session runtime, canonical corpus bootstrap,
attachment ingress, renderer apparatus, and explicit OpenAI Responses
activation.

The real provider boundary completed its controlled synthetic validation on
2026-07-25. The run made exactly one request from a clean checkout at
`7322e40`, returned HTTP 200 from `gpt-5.6-luna`, produced
`application_result: full_pass`, and replayed the resulting durable state
across an application restart without another provider request. The temporary
restricted key was revoked after the run.

That run used expressive-basis and OpenAI instruction-set version 1. It
validates the transport, rollback, replay, and client-lifetime path at that
commit; it is not live evidence for the repaired version-2 response behavior.
The version-2 repair changes projection roles, bounded material thickness,
instructions, and native acceptance—not endpoint, retry, storage, or
credential handling.

This closes provider-boundary construction and validation. It does not close
behavioral evaluation, deployment, security hardening for public access, or
product operations.

The first behavioral attempt then exposed a serious corpus-to-response
failure. Case 1, Turn 1 performed architecture language instead of engaging
the practical request, so the set stopped after one submitted turn. The
server was stopped and the restricted key was revoked. The stop evidence is
recorded in
[`BEHAVIORAL_EVALUATION_CASE_1.md`](BEHAVIORAL_EVALUATION_CASE_1.md).

The sanitized evidence and the limits of the validation claim are recorded in
[`OPENAI_LIVE_VALIDATION.md`](OPENAI_LIVE_VALIDATION.md).

## Active architecture

### Application and browser boundary

- `cbra/app.py` is the active FastAPI adapter.
- `ui/index.html` is the active browser client served at `/` and `/ui`.
- The browser creates stable thread and turn claims, reconciles interrupted
  turns, paginates the durable transcript, and submits text or multipart
  attachment turns through the native public API.
- The API returns bounded summaries and turn projections. It does not expose
  native field state, canonical source text, attachment text, renderer
  instructions, credentials, or provider error bodies.

### Canonical corpus bootstrap

- `cbra/corpus.py` loads `corpus/CBRA_Corpus_Index.md` and the four active
  canonical sources named by that manifest.
- Startup fails closed on missing, malformed, unsafe, duplicated, oversized,
  or unmapped corpus material.
- A process holds one immutable, content-addressed corpus snapshot.
- Each new thread receives the canonical streams once. Existing sessions keep
  their durable material across restart.

### Architecture-native field runtime

- `cbra/native/` owns the active field models, schemas, operators, emergence,
  cycle execution, articulation, reintegration, session ledger, and lossless
  persistence contracts.
- Intra-action, play, diffraction, creative becoming, and care operate as
  coactive field transformations rather than response-route dispatch.
- Articulation is provisional. A candidate is formed from bounded expressive
  material, evaluated by the native runtime, and either accepted or returned
  to reintegration.
- Drift and reintegration remain explicit durable lifecycle material.
- A sparse turn can truthfully produce `no_articulation`; the application does
  not fabricate fallback response text.

### Durable session boundary

- `cbra/store.py` owns one compressed native session file per hashed thread
  identity under `CBRA_SESSION_ROOT` or `.cbra-runtime/sessions`.
- Writes use schema-validated, integrity-checked serialization and atomic file
  replacement.
- Repository transactions use per-thread file locks and advance at most one
  revision.
- Turn IDs are idempotent claims: an exact retry replays, changed material
  conflicts, and a stale expected revision fails before field execution.
- The turn ledger is append-only. Public transcript pages are derived from the
  ledger and remain read-only.
- Accepted articulation, pending reintegration, renderer binding, history, and
  trace state survive restart without semantic loss.

### Attachment ingress

- Text, Markdown, DOCX, and text-bearing PDF uploads are supported.
- Raw and extracted sizes, file count, PDF pages, DOCX members, and DOCX
  expansion are finitely bounded and configurable.
- Filenames, media types, archive members, package structure, UTF-8 text, and
  client attachment claims are validated before field mutation.
- Raw uploaded bytes are not stored by the ingress boundary. Extracted text
  enters private native streams and is not returned by public transcript
  projection.
- Attachment turns share the same idempotency, revision, transaction, replay,
  and rollback guarantees as text-only turns.

### Articulation renderers

- `native-template` is the default renderer. Merely setting
  `OPENAI_API_KEY` does not activate network work.
- `openai-responses` is an explicit process-start selection. Every
  non-secret model, reasoning, verbosity, input, output, and timeout setting
  is required; there are no implicit live-mode defaults.
- The renderer sends a canonical expressive-basis projection, not native
  authority or provenance identifiers, through one stateless Responses
  request with `store=false`, zero automatic retries, and a finite timeout.
- Expressive-basis version 2 preserves bounded source text and marks the
  latest user turn as response focus, prior turns as context, attachments as
  source material, and canonical sources as silent reasoning orientation.
- OpenAI instruction-set version 2 permits situated relevance, prioritization,
  recommendations, drafting, and concrete action while continuing to reject
  moral closure, unsupported diagnosis, overclaiming, and procedural leakage.
- The repaired OpenAI acceptance boundary no longer requires visible
  formation or held-open phrases. A return to that legacy ritual is treated as
  procedural bypass and reintegrated.
- The durable renderer binding records all effective non-secret apparatus
  settings. The API key is not part of the binding or session.
- Exact replay, restart replay, health checks, UI reads, transcript reads, and
  non-renderable turns require no provider request.
- Provider failure, incomplete response, malformed text, oversized text, or
  binding mismatch rolls the attempted turn back without persisting partial
  provider work.

## Public HTTP surface

| Method | Route | Current purpose |
|---|---|---|
| `GET` | `/` and `/ui` | Serve the native browser client |
| `GET` | `/health` | Return bounded application health metadata |
| `POST` | `/generate` | Claim a thread with its first text turn |
| `POST` | `/generate/attachments` | Claim a thread with text and attachments |
| `POST` | `/chat/{thread_id}` | Submit a revision-bound text turn |
| `POST` | `/chat/{thread_id}/attachments` | Submit a revision-bound attachment turn |
| `GET` | `/thread/{thread_id}` | Return a bounded durable-session summary |
| `GET` | `/thread/{thread_id}/turns` | Return a bounded transcript page |

There is no public route for deleting, replacing, or directly editing durable
thread state.

## Verification boundary

The completed build sequence includes offline contracts for:

- native field dynamics and reintegration;
- strict schemas and lossless checkpoint, trace, and session restoration;
- session ownership, idempotency, stale revisions, concurrency, and restart;
- canonical corpus safety and immutable bootstrap;
- FastAPI request, response, error, projection, and OpenAPI contracts;
- browser transcript and attachment behavior;
- bounded attachment extraction and transactional ingress;
- renderer isolation, binding durability, rollback, and concurrency;
- OpenAI activation, sanitized failures, client lifetime, and replay;
- one-request live-validation safety and sanitized reporting.

The closure pass reran all 193 tests successfully in each maintained
compatibility stack:

| Stack | Result |
|---|---|
| Pydantic 1.10.26, OpenAI 2.47.0, HTTPX 0.27.2 | 193 passed |
| Pydantic 2.12.5, OpenAI 2.48.0, HTTPX 0.28.1 | 193 passed |

The older stack emits existing HTTPX test-client deprecation warnings and
AnyIO memory-stream resource warnings. They are not test failures, but should
be resolved if that compatibility stack remains a release target.

The corpus-to-response repair then ran the expanded 205-test suite in both
maintained compatibility stacks:

| Stack | Result |
|---|---|
| Pydantic 1.10.26, OpenAI 2.47.0, HTTPX 0.27.2 | 205 passed |
| Pydantic 2.13.4, OpenAI 2.48.0, HTTPX 0.28.1 | 205 passed |

These are offline results. The OpenAI adapter tests use local mock transport;
the repair verification made no live provider request.

The live-provider result validates the real OpenAI transport and application
path only for the fixed synthetic apparatus recorded in
`OPENAI_LIVE_VALIDATION.md`. It is not evidence of general response quality.

## Current limitations and non-claims

- No active API key is retained. OpenAI mode cannot run again unless a new key
  is deliberately provisioned and configured.
- The application has no user authentication, authorization, account
  isolation, rate limiting, or public-network deployment boundary. It should
  remain local or otherwise externally protected.
- Durable sessions use the local filesystem. There is no external database,
  multi-host coordination, backup policy, recovery interface, retention
  policy, or migration service.
- The repository uses Unix file locking (`fcntl`); the durable store is
  currently a macOS/Linux implementation, not a Windows-portable one.
- Attachment ingress is text extraction, not general multimodality. It does
  not process images, audio, video, OCR-only PDFs, spreadsheets, or
  presentations.
- The browser has no thread list, rename, delete, export, account, or
  administration interface.
- Provider activation is environment-driven and manually operated. There is
  no secret manager integration, deployment configuration, automatic key
  rotation, or usage dashboard inside CBRA.
- The live validation used one model and one fixed synthetic two-turn
  contract. It did not test model portability, load, long-running sessions,
  real attachments, personal material, or provider outage behavior live.
- Behavioral quality has not been evaluated across the complete first set.
  One Case 1 response at `67ac1b9` failed seriously enough to stop the set;
  the resulting version-2 repair has offline regression evidence but no live
  behavioral result yet.
- Expressive material is bounded rather than retrieved semantically. Current
  user turns, canonical sources, attachments, and other field material have
  separate finite projection limits; sufficiently long or dense formations
  can still exceed the configured provider-input limit and roll back the turn.
- Version-1 OpenAI-rendered sessions cannot silently continue under the
  version-2 renderer binding. A repaired live evaluation must use a fresh
  external session root.
- Earlier interaction logs and route-oriented demo documents predate the
  architecture-native runtime and are historical evidence, not current
  acceptance criteria.
- Historical compatibility modules, backup directories, archives, and
  pre-native operator artifacts remain tracked in the repository. They are
  not the active application path and still need a separate repository-hygiene
  decision.
- The application version label still names the browser-attachment pass and
  has not yet been advanced to describe the complete provider-validated
  boundary.

## Next phase

The next evidence-producing phase is a fresh live rerun of Case 1, Turn 1
through the native browser interface. It should use the fixed non-sensitive
prompt, the version-2 apparatus, and a new external session root. The response
must be read and recorded before authorizing Turn 2.

The first-set apparatus remains specified in
[`BEHAVIORAL_EVALUATION.md`](BEHAVIORAL_EVALUATION.md), with a clean
observation template in
[`BEHAVIORAL_EVALUATION_LOG.md`](BEHAVIORAL_EVALUATION_LOG.md) and one
synthetic attachment fixture. The stopped attempt and repair boundary are
recorded separately in
[`BEHAVIORAL_EVALUATION_CASE_1.md`](BEHAVIORAL_EVALUATION_CASE_1.md).

No live provider request was made while implementing or verifying the repair.
The earlier controlled provider-validation result does not need to be
repeated.

The first evaluation set should examine:

- whether practical requests produce usable action without losing the field;
- whether correction produces direct accountability before explanation;
- whether articulation stays grounded instead of performing theory;
- whether care holds difference without therapeutic slippage or moral closure;
- whether continuity, attachment participation, and reintegration remain
  perceptible across turns;
- whether accepted provider text preserves CBRA terminology and ontological
  commitments.

The repaired Case 1 must not be described as a pass until a fresh live
response supports that claim. A new provider-transport validation request is
not part of this phase.

## Operator baseline

Run the application locally with:

```bash
python -m uvicorn cbra.app:app --host 127.0.0.1 --port 8000
```

Run the complete offline Python suite with:

```bash
python -m unittest discover -s cbra -p 'test_*.py'
```

The live-validation harness is retained for controlled future diagnostics,
not as a routine regression command. It must not be rerun merely to establish
the state documented here.

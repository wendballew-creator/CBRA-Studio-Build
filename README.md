# CBRA-Studio-Build
Building a posthuman reasoning LLM architechure for personal use and then public launch

## Articulation renderer activation

CBRA continues to use its native-template articulation renderer when
`CBRA_ARTICULATION_RENDERER` is absent or set to `native-template`. An
`OPENAI_API_KEY` in the environment does not activate network rendering by
itself.

OpenAI Responses rendering is an explicit server-side mode. Set
`CBRA_ARTICULATION_RENDERER` to `openai-responses` and provide every setting
below in the process environment:

- `OPENAI_API_KEY`
- `CBRA_OPENAI_MODEL`
- `CBRA_OPENAI_REASONING_EFFORT`
- `CBRA_OPENAI_TEXT_VERBOSITY`
- `CBRA_OPENAI_MAX_INPUT_CHARS`
- `CBRA_OPENAI_MAX_OUTPUT_TOKENS`
- `CBRA_OPENAI_MAX_OUTPUT_CHARS`
- `CBRA_OPENAI_TIMEOUT_SECONDS`

There are no model or limit defaults in OpenAI mode. Keep the API key in
server-side environment or secret-management state; it is not part of the
renderer binding or durable session.

This activation uses the official OpenAI endpoint, disables automatic retries,
and applies the configured finite timeout. It rejects `OPENAI_BASE_URL`,
`OPENAI_LOG`, organization, and project environment overrides. Custom
endpoints and organization/project routing are not supported by this
activation pass.

Renderer settings are durable apparatus material. Restarting with the same
settings can continue a bound thread. Starting a new turn with different
renderer settings is rejected before provider work or persistence. Use a
separate `CBRA_SESSION_ROOT` when beginning OpenAI-rendered threads unless the
existing threads already carry the same binding.

## Controlled live-provider validation

`scripts/validate_openai_live.py` is an operator-only smoke harness for the
activated application boundary. It constructs a disposable synthetic corpus
and session root, performs health and non-renderable first-turn checks, and
permits at most one OpenAI Responses request through a transport-level fuse.
It never reads the canonical repository corpus, existing sessions,
attachments, or personal material.

The harness is fixed to this disposable smoke apparatus:

- model `gpt-5.6-luna`
- reasoning effort `none`
- text verbosity `medium`
- 20,000 maximum input characters
- 2,048 maximum output tokens
- 4,096 maximum output characters
- 60-second timeout
- zero SDK and transport retries
- `store=false`
- official `https://api.openai.com/v1` endpoint only

ChatGPT subscriptions and API Platform billing are separate. Before running
the harness, use a dedicated restricted API project key and the smallest
suitable project spend limit. Never paste the key into ChatGPT, a command, a
file, `.env`, or Git.

From a clean checkout descending from application-activation commit `04b04f0`,
create an empty report directory outside the repository and run:

```bash
artifact_dir="$(mktemp -d "${TMPDIR:-/tmp}/cbra-openai-live-report.XXXXXX")"
python scripts/validate_openai_live.py \
  --artifact-dir "$artifact_dir" \
  --confirm-one-billable-request \
  --prompt-for-api-key
```

Secure prompt mode asks for the same key twice without displaying it. Each
entry must have one complete OpenAI secret-key shape, and both entries must
match before preflight can construct a client. This rejects incomplete,
whitespace-bearing, and accidentally duplicated pastes before any provider
attempt. The key remains in the Python process only and is never accepted as a
command argument.

The explicit confirmation flag, a clean eligible checkout, an empty
out-of-repository artifact directory, and the absence of ambient OpenAI
endpoint, organization, project, or logging overrides are all required.
`OPENAI_API_KEY` must be unset when using secure prompt mode.

The harness submits fixed cedar-and-soil strands through the real FastAPI
application. Startup, health, the first turn, reads, replay, restart, and
shutdown must remain provider-free. The related second turn may make exactly
one request. A completed provider response can produce either
`accepted_articulation` or `reintegration_pending`; authentication, access,
quota, timeout, incomplete-response, and provider failures must return the
existing generic application error and preserve the exact pre-request session
bytes. No retry is attempted under any result.

The artifact directory receives only
`openai-live-validation-report.json`. The report includes non-secret
configuration, version, request ID, status, latency, usage, outcome, hashes,
and replay results. It excludes request bodies, instructions, corpus and user
text, provider output, authorization material, and the API key. Temporary
corpus and session files are removed before the report is written. Review the
sanitized report, then revoke the dedicated test key.

Provider HTTP failures are classified from status alone. In particular, a
`401` is reported as `authentication_failed` without copying the provider's
error body. Optional request ID, response-status, or model metadata that does
not satisfy the report's conservative format is omitted rather than allowed
to obscure the provider result; `omitted_metadata` records only the field
name, never its value.

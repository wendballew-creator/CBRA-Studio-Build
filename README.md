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

# OpenAI Live Provider Validation

Validation date: 2026-07-25

Validated repository head:
`7322e405aa4675d711495ba8d02a60b961562530`

Application-activation base:
`04b04f08b2e36a0f01409cfed4b7546071ba36e1`

## Result

The controlled synthetic OpenAI validation completed with:

```text
application_result: full_pass
exit_status: 0
provider_attempt_count: 1
provider_http_status: 200
provider_response_status: completed
provider_transport_failure: false
secret_scan: clean
```

The repository was clean at the validated head. The temporary restricted API
key was revoked after the run. No credential, authorization header, provider
output, request body, canonical repository content, attachment, or personal
material is recorded in this document.

## Fixed apparatus

| Setting | Validated value |
|---|---|
| Endpoint | `https://api.openai.com/v1/responses` |
| Method | `POST` |
| Model | `gpt-5.6-luna` |
| Reasoning effort | `none` |
| Text verbosity | `medium` |
| Maximum input characters | 20,000 |
| Maximum output tokens | 2,048 |
| Maximum output characters | 4,096 |
| Timeout | 60 seconds |
| Automatic retries | 0 |
| Provider storage | `false` |
| Material | Synthetic only |

The disposable synthetic corpus contained four canonical files. The first
turn truthfully produced `no_articulation` and performed no provider work.
The related second turn was the only renderable turn and the only permitted
provider attempt.

## Provider result

| Measure | Observed value |
|---|---|
| Input tokens | 440 |
| Output tokens | 68 |
| Reasoning tokens | 0 |
| Total tokens | 508 |
| Reported latency | 2,650.955 ms |
| Response model | `gpt-5.6-luna` |
| Omitted metadata fields | None |

The provider request identifier is intentionally not retained here. It is not
needed to establish the application contract after successful closure.

## Durable-state evidence

The second turn changed the durable session from:

```text
409715757df6c1c30ec902f8567aaec9da3ec5f4061959eef0760b5a8492e6df
```

to:

```text
2c057bcbe2937c2cd7f32e5b28599c2931811469fdc4a94c2307c45d5f7f4cd3
```

The same post-turn digest was obtained by:

- immediate exact replay;
- replay after application restart.

Both replays completed without another provider attempt. The completed
session contained two transcript turns at summary revision 2. The harness
constructed two application-lifetime clients and closed both.

## What this validates

This result establishes that, for the fixed apparatus above:

- explicit application activation reached the official OpenAI Responses
  endpoint;
- the transport fuse permitted exactly one request;
- OpenAI completed the response;
- provider text entered the native articulation evaluation boundary;
- CBRA accepted the resulting articulation;
- the accepted turn persisted durably;
- immediate replay and restart replay were provider-free and byte-equivalent;
- the repository remained clean;
- the sanitized report contained no detected secret material.

## What this does not validate

This result does not establish:

- general response quality or ontological fidelity;
- behavior with personal, sensitive, canonical repository, or attachment
  material;
- performance under load or across long-running sessions;
- behavior with another model or provider configuration;
- continuous availability, billing controls, or outage recovery;
- public-deployment security, authentication, or multi-user isolation;
- the safety of making the harness a routine regression test.

Those are separate evaluation or operations questions. The provider boundary
does not need another live request to remain closed at this build state.

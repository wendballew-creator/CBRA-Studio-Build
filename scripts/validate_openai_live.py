#!/usr/bin/env python3
"""Run one controlled, synthetic, billable OpenAI application validation."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import getpass
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from typing import Dict, Iterator, Mapping, Optional, Sequence
from unittest.mock import patch

import httpx


BASE_COMMIT = "04b04f08b2e36a0f01409cfed4b7546071ba36e1"
MODEL_ID = "gpt-5.6-luna"
REASONING_EFFORT = "none"
TEXT_VERBOSITY = "medium"
MAX_INPUT_CHARS = 20_000
MAX_OUTPUT_TOKENS = 2_048
MAX_OUTPUT_CHARS = 4_096
TIMEOUT_SECONDS = 60.0
OFFICIAL_BASE_URL = "https://api.openai.com/v1"
REPORT_FILENAME = "openai-live-validation-report.json"

FIRST_STRAND = "Cedar roots shelter soil and hold moisture."
RELATED_STRAND = "Cedar soil holds water around the roots."
THREAD_ID = "thread:{0}".format("c" * 32)
TURN_ONE_ID = "turn:{0}".format("1" * 32)
TURN_TWO_ID = "turn:{0}".format("2" * 32)

_CANONICAL_FILENAMES = (
    "CBRA_Glossary_v3.md",
    "CBRA_Loops_Core.md",
    "Drift_Constraints.md",
    "CBRA_Kernel_v10_2.md",
)
_AMBIENT_PROVIDER_OVERRIDES = (
    "OPENAI_BASE_URL",
    "OPENAI_LOG",
    "OPENAI_ORGANIZATION",
    "OPENAI_ORG_ID",
    "OPENAI_PROJECT",
    "OPENAI_PROJECT_ID",
)
_SAFE_METADATA = re.compile(r"^[A-Za-z0-9._:/+-]{1,200}$")
_CREDENTIAL_SHAPE = re.compile(r"sk-[A-Za-z0-9_-]{12,}")


class LiveValidationError(RuntimeError):
    """The controlled live validation cannot proceed safely."""


def _validated_api_key(value: object) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not value.startswith("sk-")
        or not 20 <= len(value) <= 2_048
        or any(
            ord(character) < 33 or ord(character) > 126
            for character in value
        )
        or value.count("sk-") != 1
    ):
        raise LiveValidationError(
            "API key entry appears incomplete, duplicated, or malformed"
        )
    return value


def capture_api_key(
    prompt_reader=None,
    notice=None,
) -> str:
    """Capture and confirm one key without echoing or persisting it."""
    if prompt_reader is None:
        prompt_reader = getpass.getpass
    if notice is None:
        notice = print
    first = _validated_api_key(
        prompt_reader(
            "Paste the restricted API key once, then press Return: "
        )
    )
    notice(
        "One key-shaped value was captured. "
        "Paste the same key once more to confirm."
    )
    second = _validated_api_key(
        prompt_reader(
            "Paste the same restricted API key once more, "
            "then press Return: "
        )
    )
    if not hmac.compare_digest(first, second):
        raise LiveValidationError(
            "The two API key entries did not match"
        )
    notice("Matching key entry confirmed.")
    return first


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git(repo_root: Path, arguments: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root)] + list(arguments),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        raise LiveValidationError(
            "Repository lineage could not be verified"
        ) from None
    return completed.stdout.strip()


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_operator_preflight(
    *,
    repo_root: Path,
    artifact_dir: Path,
    confirmed: bool,
    environment: Mapping[str, str],
    require_api_key: bool = True,
) -> Dict[str, object]:
    """Fail closed before importing CBRA or constructing an HTTP client."""
    if not confirmed:
        raise LiveValidationError(
            "The explicit one-billable-request confirmation is required"
        )
    api_key = None
    if require_api_key:
        api_key = environment.get("OPENAI_API_KEY")
        if api_key is None:
            raise LiveValidationError(
                "OPENAI_API_KEY is required in the process environment"
            )
        api_key = _validated_api_key(api_key)
    for name in _AMBIENT_PROVIDER_OVERRIDES:
        if environment.get(name) is not None:
            raise LiveValidationError(
                "Ambient OpenAI endpoint, routing, or logging overrides "
                "are not permitted"
            )

    resolved_repo = repo_root.resolve(strict=True)
    if not resolved_repo.is_dir():
        raise LiveValidationError("Repository root is not a directory")
    resolved_artifacts = artifact_dir.resolve(strict=True)
    if not resolved_artifacts.is_dir():
        raise LiveValidationError("Artifact directory is not a directory")
    if _is_within(resolved_artifacts, resolved_repo):
        raise LiveValidationError(
            "Artifact directory must be outside the repository"
        )
    try:
        if any(resolved_artifacts.iterdir()):
            raise LiveValidationError("Artifact directory must be empty")
    except OSError:
        raise LiveValidationError(
            "Artifact directory could not be inspected"
        ) from None

    top_level = Path(
        _run_git(resolved_repo, ("rev-parse", "--show-toplevel"))
    ).resolve(strict=True)
    if top_level != resolved_repo:
        raise LiveValidationError(
            "Repository root must be the checkout top level"
        )
    if _run_git(resolved_repo, ("status", "--porcelain")):
        raise LiveValidationError("Repository worktree must be clean")
    _run_git(resolved_repo, ("cat-file", "-e", "{0}^{{commit}}".format(
        BASE_COMMIT
    )))
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(resolved_repo),
                "merge-base",
                "--is-ancestor",
                BASE_COMMIT,
                "HEAD",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        raise LiveValidationError(
            "Checkout does not descend from the application-activation base"
        ) from None
    head_commit = _run_git(resolved_repo, ("rev-parse", "HEAD"))
    facts = {
        "base_commit": BASE_COMMIT,
        "head_commit": head_commit,
        "clean_tree": True,
        "repo_root": str(resolved_repo),
        "artifact_dir": str(resolved_artifacts),
    }
    if require_api_key:
        facts["api_key"] = api_key
    return facts


def _safe_metadata_text(value: object) -> Optional[str]:
    if not isinstance(value, str) or not _SAFE_METADATA.fullmatch(value):
        return None
    lowered = value.lower()
    if (
        _CREDENTIAL_SHAPE.search(value)
        or "authorization" in lowered
        or "bearer" in lowered
    ):
        return None
    return value


def _usage_metadata(payload: object) -> Optional[Dict[str, object]]:
    if not isinstance(payload, dict):
        return None
    allowed = {}
    for name in ("input_tokens", "output_tokens", "total_tokens"):
        value = payload.get(name)
        if type(value) is int and value >= 0:
            allowed[name] = value
    details = payload.get("output_tokens_details")
    if isinstance(details, dict):
        reasoning = details.get("reasoning_tokens")
        if type(reasoning) is int and reasoning >= 0:
            allowed["reasoning_tokens"] = reasoning
    return allowed or None


def _provider_result(
    *,
    http_status: Optional[int],
    transport_failure: bool,
) -> str:
    if transport_failure:
        return "transport_failure"
    if http_status is None:
        return "response_unavailable"
    if 200 <= http_status < 300:
        return "response_received"
    if http_status == 401:
        return "authentication_failed"
    if http_status == 403:
        return "access_denied"
    if http_status == 429:
        return "rate_limit_or_quota_exceeded"
    if 400 <= http_status < 500:
        return "request_rejected"
    if 500 <= http_status < 600:
        return "provider_error"
    return "http_failure"


class SingleAttemptTransport(httpx.BaseTransport):
    """Delegate at most one HTTP request while retaining safe metadata only."""

    def __init__(self, delegate: httpx.BaseTransport) -> None:
        self._delegate = delegate
        self._lock = threading.Lock()
        self.attempt_count = 0
        self.latency_ms = None
        self.request_metadata = None
        self.http_status = None
        self.request_id = None
        self.response_status = None
        self.response_model = None
        self.usage = None
        self.transport_failure = False
        self.omitted_metadata = []

    def _optional_metadata(self, name: str, value: object) -> Optional[str]:
        if value is None:
            return None
        safe_value = _safe_metadata_text(value)
        if safe_value is None and name not in self.omitted_metadata:
            self.omitted_metadata.append(name)
        return safe_value

    def _validate_request(self, request: httpx.Request) -> Dict[str, object]:
        if (
            request.method != "POST"
            or request.url.scheme != "https"
            or request.url.host != "api.openai.com"
            or request.url.path != "/v1/responses"
        ):
            raise LiveValidationError(
                "The live request does not target the official Responses API"
            )
        try:
            payload = json.loads(request.content.decode("utf-8"))
        except (AttributeError, TypeError, ValueError, UnicodeError):
            raise LiveValidationError(
                "The live request could not be safely inspected"
            ) from None
        if not isinstance(payload, dict):
            raise LiveValidationError(
                "The live request has an unexpected payload shape"
            )
        reasoning = payload.get("reasoning")
        text = payload.get("text")
        metadata = {
            "method": request.method,
            "endpoint": "https://api.openai.com/v1/responses",
            "model": payload.get("model"),
            "store": payload.get("store"),
            "max_output_tokens": payload.get("max_output_tokens"),
            "reasoning_effort": (
                reasoning.get("effort")
                if isinstance(reasoning, dict)
                else None
            ),
            "text_verbosity": (
                text.get("verbosity")
                if isinstance(text, dict)
                else None
            ),
        }
        expected = {
            "method": "POST",
            "endpoint": "https://api.openai.com/v1/responses",
            "model": MODEL_ID,
            "store": False,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "reasoning_effort": REASONING_EFFORT,
            "text_verbosity": TEXT_VERBOSITY,
        }
        if metadata != expected:
            raise LiveValidationError(
                "The live request does not match the fixed smoke apparatus"
            )
        return metadata

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        metadata = self._validate_request(request)
        with self._lock:
            if self.attempt_count:
                raise LiveValidationError(
                    "The one-request transport fuse has already been used"
                )
            self.attempt_count = 1
            self.request_metadata = metadata
        started = time.monotonic()
        try:
            return self._delegate.handle_request(request)
        except Exception:
            self.transport_failure = True
            raise
        finally:
            self.latency_ms = round(
                (time.monotonic() - started) * 1000.0,
                3,
            )

    def capture_response(self, response: httpx.Response) -> None:
        self.http_status = response.status_code
        self.request_id = self._optional_metadata(
            "request_id",
            response.headers.get("x-request-id"),
        )
        try:
            response.read()
            payload = response.json()
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        raw_status = payload.get("status")
        raw_model = payload.get("model")
        self.response_status = self._optional_metadata(
            "response_status",
            raw_status,
        )
        self.response_model = self._optional_metadata(
            "response_model",
            raw_model,
        )
        self.usage = _usage_metadata(payload.get("usage"))

    def close(self) -> None:
        self._delegate.close()


class _OwnedInstrumentedClient:
    def __init__(self, client: object, owner: "LiveOpenAIClientFactory") -> None:
        self._client = client
        self._owner = owner
        self._closed = False

    def __getattr__(self, name: str):
        return getattr(self._client, name)

    def close(self) -> None:
        if self._closed:
            raise LiveValidationError(
                "An owned OpenAI client was closed more than once"
            )
        self._closed = True
        self._owner.close_calls += 1
        self._client.close()


class LiveOpenAIClientFactory:
    """Build real SDK clients over one shared transport-level fuse."""

    def __init__(self, delegate: Optional[httpx.BaseTransport] = None) -> None:
        self.transport = SingleAttemptTransport(
            delegate if delegate is not None else httpx.HTTPTransport(retries=0)
        )
        self.constructor_calls = 0
        self.close_calls = 0
        self.client_configuration = None

    def __call__(self, **options):
        from openai import OpenAI

        expected_names = {"api_key", "base_url", "max_retries", "timeout"}
        if set(options) != expected_names:
            raise LiveValidationError(
                "The activation client options are not explicit"
            )
        if (
            options.get("base_url") != OFFICIAL_BASE_URL
            or options.get("max_retries") != 0
            or float(options.get("timeout")) != TIMEOUT_SECONDS
        ):
            raise LiveValidationError(
                "The activation client options do not match the smoke apparatus"
            )
        self.constructor_calls += 1
        self.client_configuration = {
            "base_url": OFFICIAL_BASE_URL,
            "max_retries": 0,
            "timeout_seconds": TIMEOUT_SECONDS,
        }
        http_client = httpx.Client(
            transport=self.transport,
            timeout=TIMEOUT_SECONDS,
            trust_env=False,
            event_hooks={"response": [self.transport.capture_response]},
        )
        client = OpenAI(http_client=http_client, **options)
        return _OwnedInstrumentedClient(client, self)


def _synthetic_corpus(root: Path) -> None:
    root.mkdir()
    manifest = [
        "# Synthetic live-provider validation corpus",
        "",
        "## Canonical Files (Active)",
    ]
    manifest.extend(
        "{0}. {1}".format(index, filename)
        for index, filename in enumerate(_CANONICAL_FILENAMES, start=1)
    )
    (root / "CBRA_Corpus_Index.md").write_text(
        "\n".join(manifest) + "\n",
        encoding="utf-8",
    )
    for filename in _CANONICAL_FILENAMES:
        (root / filename).write_text("", encoding="utf-8")


@contextmanager
def _temporary_sys_path(path: Path) -> Iterator[None]:
    value = str(path)
    sys.path.insert(0, value)
    try:
        yield
    finally:
        try:
            sys.path.remove(value)
        except ValueError:
            pass


def _load_create_app(
    *,
    repo_root: Path,
    corpus_root: Path,
    bootstrap_session_root: Path,
):
    bootstrap = {
        "CBRA_ARTICULATION_RENDERER": "native-template",
        "CBRA_CORPUS_ROOT": str(corpus_root),
        "CBRA_SESSION_ROOT": str(bootstrap_session_root),
    }
    with patch.dict(os.environ, bootstrap, clear=True):
        with _temporary_sys_path(repo_root):
            module = importlib.import_module("cbra.app")
    return module.create_app


def _live_environment(api_key: str) -> Dict[str, str]:
    return {
        "CBRA_ARTICULATION_RENDERER": "openai-responses",
        "OPENAI_API_KEY": api_key,
        "CBRA_OPENAI_MODEL": MODEL_ID,
        "CBRA_OPENAI_REASONING_EFFORT": REASONING_EFFORT,
        "CBRA_OPENAI_TEXT_VERBOSITY": TEXT_VERBOSITY,
        "CBRA_OPENAI_MAX_INPUT_CHARS": str(MAX_INPUT_CHARS),
        "CBRA_OPENAI_MAX_OUTPUT_TOKENS": str(MAX_OUTPUT_TOKENS),
        "CBRA_OPENAI_MAX_OUTPUT_CHARS": str(MAX_OUTPUT_CHARS),
        "CBRA_OPENAI_TIMEOUT_SECONDS": str(int(TIMEOUT_SECONDS)),
    }


def _response_json(response: httpx.Response) -> Dict[str, object]:
    try:
        value = response.json()
    except Exception:
        raise LiveValidationError(
            "The application returned a non-JSON response"
        ) from None
    if not isinstance(value, dict):
        raise LiveValidationError(
            "The application returned an unexpected response shape"
        )
    return value


def _secret_scan(
    *,
    api_key: str,
    report_text: str,
    session_paths: Sequence[Path],
) -> None:
    encoded_key = api_key.encode("utf-8")
    lowered_report = report_text.lower()
    if (
        api_key in report_text
        or _CREDENTIAL_SHAPE.search(report_text)
        or "authorization" in lowered_report
        or "bearer" in lowered_report
    ):
        raise LiveValidationError(
            "Credential-shaped material reached the in-memory report"
        )
    for path in session_paths:
        content = path.read_bytes()
        if encoded_key in content or b"authorization" in content.lower():
            raise LiveValidationError(
                "Credential material reached durable session state"
            )


def _report_json(report: Mapping[str, object]) -> str:
    try:
        return json.dumps(
            report,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    except (TypeError, ValueError, OverflowError):
        raise LiveValidationError(
            "The sanitized validation report could not be encoded"
        ) from None


def execute_live_validation(
    *,
    repo_root: Path,
    artifact_dir: Path,
    api_key: str,
    repository_facts: Mapping[str, object],
    delegate_transport: Optional[httpx.BaseTransport] = None,
) -> Dict[str, object]:
    """Exercise the activated application through one fused provider attempt."""
    from fastapi.testclient import TestClient
    import openai

    resolved_artifacts = artifact_dir.resolve(strict=True)
    if any(resolved_artifacts.iterdir()):
        raise LiveValidationError("Artifact directory must be empty")
    factory = LiveOpenAIClientFactory(delegate_transport)
    session_paths = []
    before_hash = None
    after_hash = None
    replay_hash = None
    restart_hash = None
    first_payload = None
    second_payload = None
    restart_payload = None
    summary_payload = None
    transcript_payload = None
    application_result = "safe_provider_failure"

    with tempfile.TemporaryDirectory(
        prefix="cbra-openai-live-",
        dir=str(resolved_artifacts.parent),
    ) as temporary_name:
        temporary_root = Path(temporary_name)
        corpus_root = temporary_root / "corpus"
        session_root = temporary_root / "sessions"
        bootstrap_session_root = temporary_root / "bootstrap-sessions"
        _synthetic_corpus(corpus_root)
        session_root.mkdir()
        bootstrap_session_root.mkdir()
        create_app = _load_create_app(
            repo_root=repo_root,
            corpus_root=corpus_root,
            bootstrap_session_root=bootstrap_session_root,
        )
        live_environment = _live_environment(api_key)

        with patch.dict(os.environ, live_environment, clear=True):
            with patch(
                "cbra.providers.application_activation."
                "_load_openai_client_class",
                return_value=factory,
            ):
                application = create_app(
                    session_root=session_root,
                    corpus_root=corpus_root,
                    compress=False,
                )
        repository = application.state.native_service.repository
        session_path = repository.path_for(THREAD_ID)
        session_paths.append(session_path)

        with TestClient(
            application,
            raise_server_exceptions=False,
        ) as client:
            health = client.get("/health")
            if health.status_code != 200 or factory.transport.attempt_count:
                raise LiveValidationError(
                    "Startup or health checking violated the no-request boundary"
                )
            first = client.post(
                "/generate",
                json={
                    "thread_id": THREAD_ID,
                    "turn_id": TURN_ONE_ID,
                    "user_text": FIRST_STRAND,
                    "mode": "production",
                },
            )
            first_payload = _response_json(first)
            if (
                first.status_code != 201
                or first_payload.get("revision") != 1
                or first_payload.get("outcome") != "no_articulation"
                or factory.transport.attempt_count
            ):
                raise LiveValidationError(
                    "The synthetic first turn violated its fixed contract"
                )
            before_hash = _sha256_file(session_path)

            second = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "turn_id": TURN_TWO_ID,
                    "expected_revision": 1,
                    "user_text": RELATED_STRAND,
                    "mode": "production",
                },
            )
            second_payload = _response_json(second)
            if factory.transport.attempt_count != 1:
                raise LiveValidationError(
                    "The renderable turn did not make exactly one attempt"
                )
            if second.status_code == 200:
                outcome = second_payload.get("outcome")
                if outcome not in (
                    "accepted_articulation",
                    "reintegration_pending",
                ):
                    raise LiveValidationError(
                        "The completed provider response had an invalid outcome"
                    )
                application_result = (
                    "full_pass"
                    if outcome == "accepted_articulation"
                    else "bounded_native_rejection"
                )
                after_hash = _sha256_file(session_path)
                replay = client.post(
                    "/chat/{0}".format(THREAD_ID),
                    json={
                        "turn_id": TURN_TWO_ID,
                        "expected_revision": 1,
                        "user_text": RELATED_STRAND,
                        "mode": "production",
                    },
                )
                replay_payload = _response_json(replay)
                if (
                    replay.status_code != 200
                    or replay_payload.get("idempotent_replay") is not True
                    or factory.transport.attempt_count != 1
                ):
                    raise LiveValidationError(
                        "Exact replay attempted provider work or changed result"
                    )
                replay_hash = _sha256_file(session_path)
                if replay_hash != after_hash:
                    raise LiveValidationError(
                        "Exact replay changed durable session bytes"
                    )
                summary_response = client.get(
                    "/thread/{0}".format(THREAD_ID)
                )
                transcript_response = client.get(
                    "/thread/{0}/turns".format(THREAD_ID)
                )
                if (
                    summary_response.status_code != 200
                    or transcript_response.status_code != 200
                    or factory.transport.attempt_count != 1
                ):
                    raise LiveValidationError(
                        "Read-only projections violated the provider boundary"
                    )
                summary_payload = _response_json(summary_response)
                transcript_payload = _response_json(transcript_response)
            else:
                if (
                    second.status_code != 500
                    or second_payload.get("error", {}).get("code")
                    != "internal_error"
                ):
                    raise LiveValidationError(
                        "Provider failure escaped the generic application boundary"
                    )
                after_hash = _sha256_file(session_path)
                if after_hash != before_hash:
                    raise LiveValidationError(
                        "Provider failure changed durable session bytes"
                    )

        if application_result != "safe_provider_failure":
            with patch.dict(os.environ, live_environment, clear=True):
                with patch(
                    "cbra.providers.application_activation."
                    "_load_openai_client_class",
                    return_value=factory,
                ):
                    restarted = create_app(
                        session_root=session_root,
                        corpus_root=corpus_root,
                        compress=False,
                    )
            with TestClient(
                restarted,
                raise_server_exceptions=False,
            ) as restarted_client:
                restart = restarted_client.post(
                    "/chat/{0}".format(THREAD_ID),
                    json={
                        "turn_id": TURN_TWO_ID,
                        "expected_revision": 1,
                        "user_text": RELATED_STRAND,
                        "mode": "production",
                    },
                )
                restart_payload = _response_json(restart)
                if (
                    restart.status_code != 200
                    or restart_payload.get("idempotent_replay") is not True
                    or factory.transport.attempt_count != 1
                ):
                    raise LiveValidationError(
                        "Restart replay attempted provider work or changed result"
                    )
                restart_hash = _sha256_file(session_path)
                if restart_hash != after_hash:
                    raise LiveValidationError(
                        "Restart replay changed durable session bytes"
                    )

        report = {
            "apparatus": {
                "base_url": OFFICIAL_BASE_URL,
                "max_input_chars": MAX_INPUT_CHARS,
                "max_output_chars": MAX_OUTPUT_CHARS,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "max_retries": 0,
                "model": MODEL_ID,
                "reasoning_effort": REASONING_EFFORT,
                "store": False,
                "text_verbosity": TEXT_VERBOSITY,
                "timeout_seconds": TIMEOUT_SECONDS,
            },
            "application_result": application_result,
            "client_lifetime": {
                "clients_constructed": factory.constructor_calls,
                "clients_closed": factory.close_calls,
            },
            "durable_state": {
                "after_second_sha256": after_hash,
                "before_second_sha256": before_hash,
                "replay_sha256": replay_hash,
                "restart_replay_sha256": restart_hash,
            },
            "provider": {
                "attempt_count": factory.transport.attempt_count,
                "http_status": factory.transport.http_status,
                "latency_ms": factory.transport.latency_ms,
                "omitted_metadata": sorted(
                    factory.transport.omitted_metadata
                ),
                "request": factory.transport.request_metadata,
                "request_id": factory.transport.request_id,
                "result": _provider_result(
                    http_status=factory.transport.http_status,
                    transport_failure=factory.transport.transport_failure,
                ),
                "response_model": factory.transport.response_model,
                "response_status": factory.transport.response_status,
                "transport_failure": factory.transport.transport_failure,
                "usage": factory.transport.usage,
            },
            "repository": {
                "base_commit": repository_facts.get("base_commit"),
                "clean_tree": repository_facts.get("clean_tree"),
                "head_commit": repository_facts.get("head_commit"),
            },
            "runtime": {
                "openai_python": getattr(openai, "__version__", "unknown"),
                "python": sys.version.split()[0],
            },
            "secret_scan": "clean",
            "synthetic_contract": {
                "attachments": False,
                "canonical_files": len(_CANONICAL_FILENAMES),
                "first_outcome": (
                    first_payload.get("outcome")
                    if isinstance(first_payload, dict)
                    else None
                ),
                "material": "synthetic-only",
                "restart_replay": (
                    restart_payload.get("idempotent_replay")
                    if isinstance(restart_payload, dict)
                    else None
                ),
                "summary_revision": (
                    summary_payload.get("revision")
                    if isinstance(summary_payload, dict)
                    else None
                ),
                "transcript_turn_count": (
                    len(transcript_payload.get("turns", ()))
                    if isinstance(transcript_payload, dict)
                    else None
                ),
            },
        }
        report_text = _report_json(report)
        _secret_scan(
            api_key=api_key,
            report_text=report_text,
            session_paths=session_paths,
        )

    if any(resolved_artifacts.iterdir()):
        raise LiveValidationError(
            "Unexpected files appeared in the artifact directory"
        )
    report_path = resolved_artifacts / REPORT_FILENAME
    report_path.write_text(report_text, encoding="utf-8")
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one synthetic OpenAI Responses validation with a "
            "transport-level one-request fuse."
        )
    )
    parser.add_argument(
        "--artifact-dir",
        required=True,
        type=Path,
        help="Existing empty directory outside the repository",
    )
    parser.add_argument(
        "--confirm-one-billable-request",
        action="store_true",
        help="Explicitly permit at most one billable Responses request",
    )
    parser.add_argument(
        "--prompt-for-api-key",
        action="store_true",
        help=(
            "Securely capture and compare two hidden key entries instead "
            "of reading OPENAI_API_KEY"
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    try:
        if not arguments.confirm_one_billable_request:
            raise LiveValidationError(
                "The explicit one-billable-request confirmation is required"
            )
        environment = dict(os.environ)
        if arguments.prompt_for_api_key:
            if environment.get("OPENAI_API_KEY") is not None:
                raise LiveValidationError(
                    "Remove OPENAI_API_KEY before using secure prompt mode"
                )
            facts = validate_operator_preflight(
                repo_root=repo_root,
                artifact_dir=arguments.artifact_dir,
                confirmed=arguments.confirm_one_billable_request,
                environment=environment,
                require_api_key=False,
            )
            api_key = capture_api_key()
        else:
            facts = validate_operator_preflight(
                repo_root=repo_root,
                artifact_dir=arguments.artifact_dir,
                confirmed=arguments.confirm_one_billable_request,
                environment=environment,
            )
            api_key = str(facts.pop("api_key"))
        facts.pop("repo_root", None)
        facts.pop("artifact_dir", None)
        report = execute_live_validation(
            repo_root=repo_root,
            artifact_dir=arguments.artifact_dir,
            api_key=api_key,
            repository_facts=facts,
        )
    except LiveValidationError as exc:
        print("Live validation refused: {0}".format(exc), file=sys.stderr)
        return 2
    print(
        "Live validation result: {0}".format(
            report["application_result"]
        )
    )
    print(
        "Sanitized report: {0}".format(
            arguments.artifact_dir.resolve() / REPORT_FILENAME
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

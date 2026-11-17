#!/usr/bin/env python3
"""Start a bounded local CBRA behavioral-evaluation server."""

from __future__ import annotations

import argparse
import getpass
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Dict, Mapping, Optional, Sequence, Tuple


CLOSURE_COMMIT = "aabd20e450d6e281bdacdeb0c38efc239fe9d126"
MODEL_ID = "gpt-5.6-luna"
REASONING_EFFORT = "none"
TEXT_VERBOSITY = "medium"
MAX_INPUT_CHARS = 20_000
MAX_OUTPUT_TOKENS = 2_048
MAX_OUTPUT_CHARS = 4_096
TIMEOUT_SECONDS = 60.0
APPARATUS_FILENAME = "behavioral-evaluation-apparatus.json"
OBSERVATION_FILENAME = "behavioral-evaluation-observations.md"

_AMBIENT_PROVIDER_OVERRIDES = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_LOG",
    "OPENAI_ORGANIZATION",
    "OPENAI_ORG_ID",
    "OPENAI_PROJECT",
    "OPENAI_PROJECT_ID",
)


class BehavioralEvaluationLaunchError(RuntimeError):
    """The live behavioral-evaluation server cannot start safely."""


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
        raise BehavioralEvaluationLaunchError(
            "API key entry appears incomplete, duplicated, or malformed"
        )
    return value


def capture_api_key(prompt_reader=None, notice=None) -> str:
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
        raise BehavioralEvaluationLaunchError(
            "The two API key entries did not match"
        )
    notice("Matching key entry confirmed.")
    return first


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
        raise BehavioralEvaluationLaunchError(
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
    confirmed: bool,
    environment: Mapping[str, str],
) -> str:
    """Verify consent, ambient state, lineage, and checkout cleanliness."""
    if not confirmed:
        raise BehavioralEvaluationLaunchError(
            "Explicit behavioral-evaluation billing confirmation is required"
        )
    for name in _AMBIENT_PROVIDER_OVERRIDES:
        if environment.get(name) is not None:
            raise BehavioralEvaluationLaunchError(
                "Remove ambient OpenAI credentials, routing, and logging "
                "configuration before secure prompt mode"
            )

    resolved_repo = repo_root.resolve(strict=True)
    top_level = Path(
        _run_git(resolved_repo, ("rev-parse", "--show-toplevel"))
    ).resolve(strict=True)
    if top_level != resolved_repo:
        raise BehavioralEvaluationLaunchError(
            "Repository root must be the checkout top level"
        )
    if _run_git(resolved_repo, ("status", "--porcelain")):
        raise BehavioralEvaluationLaunchError(
            "Repository worktree must be clean"
        )
    _run_git(
        resolved_repo,
        ("cat-file", "-e", "{0}^{{commit}}".format(CLOSURE_COMMIT)),
    )
    _run_git(
        resolved_repo,
        ("merge-base", "--is-ancestor", CLOSURE_COMMIT, "HEAD"),
    )
    return _run_git(resolved_repo, ("rev-parse", "HEAD"))


def _apparatus_record(head_commit: str) -> Dict[str, object]:
    return {
        "schema_version": 1,
        "repository_head": head_commit,
        "protocol": "BEHAVIORAL_EVALUATION.md",
        "model": MODEL_ID,
        "reasoning_effort": REASONING_EFFORT,
        "text_verbosity": TEXT_VERBOSITY,
        "max_input_chars": MAX_INPUT_CHARS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_output_chars": MAX_OUTPUT_CHARS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "max_retries": 0,
        "provider_storage": False,
        "host": "127.0.0.1",
    }


def prepare_evaluation_root(
    *,
    repo_root: Path,
    requested_root: Optional[Path],
    resume: bool,
    head_commit: str,
) -> Tuple[Path, Path, Path]:
    """Create or validate external sessions, apparatus, and observation log."""
    resolved_repo = repo_root.resolve(strict=True)
    if requested_root is None:
        if resume:
            raise BehavioralEvaluationLaunchError(
                "--resume requires --evaluation-root"
            )
        root = Path(
            tempfile.mkdtemp(prefix="cbra-behavioral-evaluation.")
        ).resolve(strict=True)
    else:
        candidate = requested_root
        normalized_candidate = candidate.resolve(strict=False)
        if _is_within(normalized_candidate, resolved_repo):
            raise BehavioralEvaluationLaunchError(
                "The evaluation root must be outside the repository"
            )
        if resume:
            try:
                root = candidate.resolve(strict=True)
            except OSError:
                raise BehavioralEvaluationLaunchError(
                    "The evaluation root does not exist"
                ) from None
        else:
            try:
                candidate.mkdir()
            except FileExistsError:
                pass
            except OSError:
                raise BehavioralEvaluationLaunchError(
                    "The evaluation root could not be created"
                ) from None
            root = candidate.resolve(strict=True)

    if not root.is_dir() or _is_within(root, resolved_repo):
        raise BehavioralEvaluationLaunchError(
            "The evaluation root must be a directory outside the repository"
        )

    sessions = root / "sessions"
    apparatus_path = root / APPARATUS_FILENAME
    observation_path = root / OBSERVATION_FILENAME
    expected = _apparatus_record(head_commit)

    if resume:
        if (
            not sessions.is_dir()
            or not apparatus_path.is_file()
            or not observation_path.is_file()
        ):
            raise BehavioralEvaluationLaunchError(
                "The evaluation root is incomplete and cannot be resumed"
            )
        try:
            observed = json.loads(
                apparatus_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            raise BehavioralEvaluationLaunchError(
                "The evaluation apparatus record could not be read"
            ) from None
        if observed != expected:
            raise BehavioralEvaluationLaunchError(
                "The saved evaluation apparatus does not match this checkout"
            )
        return root, sessions, observation_path

    if any(root.iterdir()):
        raise BehavioralEvaluationLaunchError(
            "A new evaluation root must be empty"
        )
    sessions.mkdir()
    template = resolved_repo / "BEHAVIORAL_EVALUATION_LOG.md"
    try:
        observation_path.write_text(
            template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        apparatus_path.write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        raise BehavioralEvaluationLaunchError(
            "Evaluation records could not be prepared"
        ) from None
    return root, sessions, observation_path


def build_child_environment(
    *,
    source: Mapping[str, str],
    api_key: str,
    repo_root: Path,
    sessions: Path,
) -> Dict[str, str]:
    """Build the fixed renderer environment without mutating the shell."""
    child = dict(source)
    for name in tuple(child):
        if name.startswith("CBRA_") or name in _AMBIENT_PROVIDER_OVERRIDES:
            child.pop(name, None)
    child.update(
        {
            "OPENAI_API_KEY": _validated_api_key(api_key),
            "CBRA_ARTICULATION_RENDERER": "openai-responses",
            "CBRA_CORPUS_ROOT": str((repo_root / "corpus").resolve()),
            "CBRA_SESSION_ROOT": str(sessions.resolve()),
            "CBRA_OPENAI_MODEL": MODEL_ID,
            "CBRA_OPENAI_REASONING_EFFORT": REASONING_EFFORT,
            "CBRA_OPENAI_TEXT_VERBOSITY": TEXT_VERBOSITY,
            "CBRA_OPENAI_MAX_INPUT_CHARS": str(MAX_INPUT_CHARS),
            "CBRA_OPENAI_MAX_OUTPUT_TOKENS": str(MAX_OUTPUT_TOKENS),
            "CBRA_OPENAI_MAX_OUTPUT_CHARS": str(MAX_OUTPUT_CHARS),
            "CBRA_OPENAI_TIMEOUT_SECONDS": str(int(TIMEOUT_SECONDS)),
        }
    )
    return child


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Start CBRA on localhost for the bounded live behavioral "
            "evaluation described in BEHAVIORAL_EVALUATION.md."
        )
    )
    parser.add_argument(
        "--confirm-behavioral-evaluation-billing",
        action="store_true",
        help=(
            "Confirm that renderable browser turns may make billable "
            "OpenAI Responses requests"
        ),
    )
    parser.add_argument(
        "--evaluation-root",
        type=Path,
        help=(
            "External evaluation directory; omit for a new temporary one"
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the exact saved apparatus and durable sessions",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Localhost port (default: 8000)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    try:
        if not 1 <= arguments.port <= 65_535:
            raise BehavioralEvaluationLaunchError(
                "Port must be between 1 and 65535"
            )
        environment = dict(os.environ)
        head_commit = validate_operator_preflight(
            repo_root=repo_root,
            confirmed=arguments.confirm_behavioral_evaluation_billing,
            environment=environment,
        )
        root, sessions, observation_path = prepare_evaluation_root(
            repo_root=repo_root,
            requested_root=arguments.evaluation_root,
            resume=arguments.resume,
            head_commit=head_commit,
        )
        api_key = capture_api_key()
        child_environment = build_child_environment(
            source=environment,
            api_key=api_key,
            repo_root=repo_root,
            sessions=sessions,
        )
        del api_key
    except BehavioralEvaluationLaunchError as exc:
        print(
            "Behavioral evaluation refused: {0}".format(exc),
            file=sys.stderr,
        )
        return 2

    print("Evaluation root: {0}".format(root))
    print("Observation log: {0}".format(observation_path))
    print(
        "Open http://127.0.0.1:{0} after startup. "
        "Stop the server with Control-C.".format(arguments.port)
    )
    print(
        "Each renderable turn may make one billable request. "
        "The protocol manually limits the first set to 12 submitted turns."
    )
    sys.stdout.flush()
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "cbra.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(arguments.port),
    ]
    try:
        os.chdir(repo_root)
        os.execve(sys.executable, command, child_environment)
    except OSError:
        print(
            "Behavioral evaluation refused: the local server could not start",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

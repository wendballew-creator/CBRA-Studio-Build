"""Offline contracts for the live behavioral-evaluation launcher."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.start_behavioral_evaluation import (
    APPARATUS_FILENAME,
    BehavioralEvaluationLaunchError,
    CLOSURE_COMMIT,
    MAX_OUTPUT_TOKENS,
    MODEL_ID,
    OBSERVATION_FILENAME,
    build_child_environment,
    capture_api_key,
    prepare_evaluation_root,
    validate_operator_preflight,
)


TEST_API_KEY = "sk-behavioral-evaluation-secret-that-must-not-persist"


class BehavioralEvaluationLauncherTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent

    def test_secure_key_capture_requires_one_matching_value_twice(self):
        entries = iter((TEST_API_KEY, TEST_API_KEY))
        prompts = []
        notices = []

        captured = capture_api_key(
            prompt_reader=lambda prompt: (
                prompts.append(prompt) or next(entries)
            ),
            notice=notices.append,
        )

        self.assertEqual(captured, TEST_API_KEY)
        self.assertEqual(len(prompts), 2)
        self.assertEqual(len(notices), 2)
        self.assertNotIn(
            TEST_API_KEY,
            "\n".join(prompts + notices),
        )

    def test_secure_key_capture_rejects_duplication_and_mismatch(self):
        duplicated = iter((TEST_API_KEY + TEST_API_KEY,))
        with self.assertRaises(BehavioralEvaluationLaunchError):
            capture_api_key(
                prompt_reader=lambda prompt: next(duplicated),
                notice=lambda message: None,
            )

        mismatched = iter(
            (
                TEST_API_KEY,
                "sk-another-valid-behavioral-evaluation-secret",
            )
        )
        with self.assertRaises(BehavioralEvaluationLaunchError):
            capture_api_key(
                prompt_reader=lambda prompt: next(mismatched),
                notice=lambda message: None,
            )

    def test_preflight_requires_confirmation_before_repository_work(self):
        with patch(
            "scripts.start_behavioral_evaluation._run_git"
        ) as run_git:
            with self.assertRaises(BehavioralEvaluationLaunchError):
                validate_operator_preflight(
                    repo_root=self.repo_root,
                    confirmed=False,
                    environment={},
                )
        run_git.assert_not_called()

    def test_preflight_rejects_ambient_key_without_exposing_it(self):
        with self.assertRaises(
            BehavioralEvaluationLaunchError
        ) as captured:
            validate_operator_preflight(
                repo_root=self.repo_root,
                confirmed=True,
                environment={"OPENAI_API_KEY": TEST_API_KEY},
            )
        self.assertNotIn(TEST_API_KEY, str(captured.exception))

    def test_fresh_external_root_writes_only_sanitized_apparatus(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evaluation"
            prepared, sessions, observations = prepare_evaluation_root(
                repo_root=self.repo_root,
                requested_root=root,
                resume=False,
                head_commit="7" * 40,
            )

            self.assertEqual(prepared, root.resolve())
            self.assertTrue(sessions.is_dir())
            self.assertEqual(observations.name, OBSERVATION_FILENAME)
            apparatus_text = (
                prepared / APPARATUS_FILENAME
            ).read_text(encoding="utf-8")
            apparatus = json.loads(apparatus_text)
            self.assertEqual(apparatus["repository_head"], "7" * 40)
            self.assertEqual(apparatus["model"], MODEL_ID)
            self.assertFalse(apparatus["provider_storage"])
            self.assertNotIn(TEST_API_KEY, apparatus_text)

    def test_resume_requires_exact_saved_apparatus(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evaluation"
            prepare_evaluation_root(
                repo_root=self.repo_root,
                requested_root=root,
                resume=False,
                head_commit="7" * 40,
            )

            with self.assertRaises(BehavioralEvaluationLaunchError):
                prepare_evaluation_root(
                    repo_root=self.repo_root,
                    requested_root=root,
                    resume=True,
                    head_commit="8" * 40,
                )

    def test_evaluation_root_inside_repository_is_refused_before_creation(self):
        root = self.repo_root / "forbidden-evaluation-root"
        self.assertFalse(root.exists())

        with self.assertRaises(BehavioralEvaluationLaunchError):
            prepare_evaluation_root(
                repo_root=self.repo_root,
                requested_root=root,
                resume=False,
                head_commit="7" * 40,
            )

        self.assertFalse(root.exists())

    def test_child_environment_is_fixed_and_does_not_mutate_source(self):
        source = {
            "PATH": "/test/bin",
            "CBRA_OPENAI_MODEL": "ambient-model",
            "CBRA_SESSION_ROOT": "/ambient/sessions",
        }
        with tempfile.TemporaryDirectory() as temporary:
            sessions = Path(temporary)
            child = build_child_environment(
                source=source,
                api_key=TEST_API_KEY,
                repo_root=self.repo_root,
                sessions=sessions,
            )

        self.assertEqual(source["CBRA_OPENAI_MODEL"], "ambient-model")
        self.assertEqual(child["CBRA_OPENAI_MODEL"], MODEL_ID)
        self.assertEqual(
            child["CBRA_OPENAI_MAX_OUTPUT_TOKENS"],
            str(MAX_OUTPUT_TOKENS),
        )
        self.assertEqual(
            child["CBRA_ARTICULATION_RENDERER"],
            "openai-responses",
        )
        self.assertEqual(child["OPENAI_API_KEY"], TEST_API_KEY)

    def test_successful_preflight_requires_clean_descendant_checkout(self):
        def git_result(repo_root, arguments):
            if arguments == ("rev-parse", "--show-toplevel"):
                return str(self.repo_root.resolve())
            if arguments == ("status", "--porcelain"):
                return ""
            if arguments == ("rev-parse", "HEAD"):
                return "9" * 40
            if arguments == (
                "cat-file",
                "-e",
                "{0}^{{commit}}".format(CLOSURE_COMMIT),
            ):
                return ""
            if arguments == (
                "merge-base",
                "--is-ancestor",
                CLOSURE_COMMIT,
                "HEAD",
            ):
                return ""
            raise AssertionError(arguments)

        with patch(
            "scripts.start_behavioral_evaluation._run_git",
            side_effect=git_result,
        ):
            head = validate_operator_preflight(
                repo_root=self.repo_root,
                confirmed=True,
                environment={},
            )

        self.assertEqual(head, "9" * 40)


if __name__ == "__main__":
    unittest.main()

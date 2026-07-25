"""Offline contracts for the controlled live-provider validation harness."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from scripts.validate_openai_live import (
    BASE_COMMIT,
    FIRST_STRAND,
    LiveValidationError,
    MAX_OUTPUT_TOKENS,
    MODEL_ID,
    REASONING_EFFORT,
    RELATED_STRAND,
    REPORT_FILENAME,
    SingleAttemptTransport,
    TEXT_VERBOSITY,
    capture_api_key,
    execute_live_validation,
    main,
    validate_operator_preflight,
)


TEST_API_KEY = "sk-live-validation-secret-that-must-never-persist"
ACCEPTED_TEXT = (
    "One formation keeps cedar roots and sheltering soil in relation.\n\n"
    "Another formation keeps river current, stone, and silt perceptible.\n\n"
    "Other material remains held open while the relation stays revisable."
)
REJECTED_TEXT = "Everything is one final and certain answer."


def response_payload(text=ACCEPTED_TEXT, status="completed"):
    return {
        "id": "resp_live_validation",
        "object": "response",
        "created_at": 1,
        "status": status,
        "model": MODEL_ID,
        "output": [
            {
                "id": "rs_live_validation",
                "type": "reasoning",
                "summary": [],
            },
            {
                "id": "msg_live_validation",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                        "annotations": [],
                    }
                ],
            },
        ],
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 12,
            "output_tokens": 34,
            "total_tokens": 46,
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


def completed_handler(
    text=ACCEPTED_TEXT,
    *,
    request_id="req_live_validation",
):
    def handle(request):
        return httpx.Response(
            200,
            headers={"x-request-id": request_id},
            json=response_payload(text=text),
        )

    return handle


class OpenAILiveValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.repo_root = Path(__file__).resolve().parent.parent
        self.repository_facts = {
            "base_commit": BASE_COMMIT,
            "head_commit": "7" * 40,
            "clean_tree": True,
        }

    def tearDown(self):
        self.temporary.cleanup()

    def execute(self, handler):
        return execute_live_validation(
            repo_root=self.repo_root,
            artifact_dir=self.artifacts,
            api_key=TEST_API_KEY,
            repository_facts=self.repository_facts,
            delegate_transport=httpx.MockTransport(handler),
        )

    def test_confirmation_gate_precedes_key_and_repository_checks(self):
        with self.assertRaises(LiveValidationError) as captured:
            validate_operator_preflight(
                repo_root=Path("/missing-repository"),
                artifact_dir=Path("/missing-artifacts"),
                confirmed=False,
                environment={},
            )
        self.assertIn("confirmation", str(captured.exception))

    def test_preflight_requires_key_and_rejects_ambient_provider_overrides(self):
        with self.assertRaises(LiveValidationError) as missing:
            validate_operator_preflight(
                repo_root=self.repo_root,
                artifact_dir=self.artifacts,
                confirmed=True,
                environment={},
            )
        self.assertIn("OPENAI_API_KEY", str(missing.exception))

        with self.assertRaises(LiveValidationError) as ambient:
            validate_operator_preflight(
                repo_root=self.repo_root,
                artifact_dir=self.artifacts,
                confirmed=True,
                environment={
                    "OPENAI_API_KEY": TEST_API_KEY,
                    "OPENAI_BASE_URL": "https://redirect.invalid/v1",
                },
            )
        self.assertIn("not permitted", str(ambient.exception))
        self.assertNotIn(TEST_API_KEY, str(ambient.exception))

    def test_preflight_rejects_incomplete_or_duplicated_key_entries(self):
        invalid_entries = (
            "not-an-api-key",
            " " + TEST_API_KEY,
            TEST_API_KEY + " ",
            TEST_API_KEY + TEST_API_KEY,
        )
        for value in invalid_entries:
            with self.subTest(value_length=len(value)):
                with self.assertRaises(LiveValidationError) as captured:
                    validate_operator_preflight(
                        repo_root=self.repo_root,
                        artifact_dir=self.artifacts,
                        confirmed=True,
                        environment={"OPENAI_API_KEY": value},
                    )
                self.assertIn("duplicated", str(captured.exception))
                self.assertNotIn(value, str(captured.exception))

    def test_secure_key_capture_requires_one_matching_key_twice(self):
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
        rendered = "\n".join(prompts + notices)
        self.assertNotIn(TEST_API_KEY, rendered)

    def test_secure_key_capture_rejects_duplication_and_mismatch(self):
        duplicated = iter((TEST_API_KEY + TEST_API_KEY,))
        with self.assertRaises(LiveValidationError) as duplicate_error:
            capture_api_key(
                prompt_reader=lambda prompt: next(duplicated),
                notice=lambda message: None,
            )
        self.assertIn("duplicated", str(duplicate_error.exception))

        mismatched = iter((
            TEST_API_KEY,
            "sk-another-valid-validation-secret-key",
        ))
        with self.assertRaises(LiveValidationError) as mismatch_error:
            capture_api_key(
                prompt_reader=lambda prompt: next(mismatched),
                notice=lambda message: None,
            )
        self.assertIn("did not match", str(mismatch_error.exception))

    def test_preflight_rejects_artifacts_inside_repository(self):
        with tempfile.TemporaryDirectory(
            dir=str(self.repo_root)
        ) as inside_name:
            with self.assertRaises(LiveValidationError) as captured:
                validate_operator_preflight(
                    repo_root=self.repo_root,
                    artifact_dir=Path(inside_name),
                    confirmed=True,
                    environment={"OPENAI_API_KEY": TEST_API_KEY},
                )
        self.assertIn("outside", str(captured.exception))

    def test_preflight_rejects_nonempty_artifact_directory(self):
        marker = self.artifacts / "existing.txt"
        marker.write_text("occupied", encoding="utf-8")
        with self.assertRaises(LiveValidationError) as captured:
            validate_operator_preflight(
                repo_root=self.repo_root,
                artifact_dir=self.artifacts,
                confirmed=True,
                environment={"OPENAI_API_KEY": TEST_API_KEY},
            )
        self.assertIn("empty", str(captured.exception))

    def test_single_attempt_transport_fuses_a_second_request(self):
        transport = SingleAttemptTransport(
            httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json=response_payload(),
                )
            )
        )
        request = httpx.Request(
            "POST",
            "https://api.openai.com/v1/responses",
            json={
                "model": MODEL_ID,
                "store": False,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "reasoning": {"effort": REASONING_EFFORT},
                "text": {"verbosity": TEXT_VERBOSITY},
            },
        )

        response = transport.handle_request(request)
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(LiveValidationError):
            transport.handle_request(request)
        self.assertEqual(transport.attempt_count, 1)

    def test_transport_rejects_redirects_and_changed_apparatus_before_attempt(self):
        transport = SingleAttemptTransport(
            httpx.MockTransport(
                lambda request: self.fail("delegate must not run")
            )
        )
        wrong_endpoint = httpx.Request(
            "POST",
            "https://redirect.invalid/v1/responses",
            json={
                "model": MODEL_ID,
                "store": False,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "reasoning": {"effort": REASONING_EFFORT},
                "text": {"verbosity": TEXT_VERBOSITY},
            },
        )
        changed_model = httpx.Request(
            "POST",
            "https://api.openai.com/v1/responses",
            json={
                "model": "changed-model",
                "store": False,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "reasoning": {"effort": REASONING_EFFORT},
                "text": {"verbosity": TEXT_VERBOSITY},
            },
        )

        with self.assertRaises(LiveValidationError):
            transport.handle_request(wrong_endpoint)
        with self.assertRaises(LiveValidationError):
            transport.handle_request(changed_model)
        self.assertEqual(transport.attempt_count, 0)

    def test_accepted_response_passes_replay_restart_and_sanitized_report(self):
        with patch.dict(
            os.environ,
            {
                "CBRA_CORPUS_ROOT": "/ambient/corpus/must/not/be/read",
                "CBRA_CORPUS_MAX_FILES": "not-an-integer",
                "CBRA_ATTACHMENT_MAX_FILES": "not-an-integer",
            },
            clear=True,
        ):
            report = self.execute(completed_handler())

        self.assertEqual(report["application_result"], "full_pass")
        self.assertEqual(report["provider"]["attempt_count"], 1)
        self.assertEqual(report["provider"]["http_status"], 200)
        self.assertEqual(
            report["provider"]["result"],
            "response_received",
        )
        self.assertEqual(report["provider"]["omitted_metadata"], [])
        self.assertEqual(
            report["provider"]["request_id"],
            "req_live_validation",
        )
        self.assertEqual(report["provider"]["usage"]["total_tokens"], 46)
        self.assertEqual(
            report["synthetic_contract"]["first_outcome"],
            "no_articulation",
        )
        self.assertTrue(
            report["synthetic_contract"]["restart_replay"]
        )
        self.assertEqual(
            report["durable_state"]["after_second_sha256"],
            report["durable_state"]["replay_sha256"],
        )
        self.assertEqual(
            report["durable_state"]["after_second_sha256"],
            report["durable_state"]["restart_replay_sha256"],
        )
        self.assertEqual(
            sorted(path.name for path in self.artifacts.iterdir()),
            [REPORT_FILENAME],
        )
        report_text = (self.artifacts / REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
        self.assertNotIn(TEST_API_KEY, report_text)
        self.assertNotIn(FIRST_STRAND, report_text)
        self.assertNotIn(RELATED_STRAND, report_text)
        self.assertNotIn(ACCEPTED_TEXT, report_text)
        self.assertNotIn("authorization", report_text.lower())

    def test_completed_native_rejection_is_bounded_without_retry(self):
        report = self.execute(completed_handler(REJECTED_TEXT))

        self.assertEqual(
            report["application_result"],
            "bounded_native_rejection",
        )
        self.assertEqual(report["provider"]["attempt_count"], 1)
        self.assertEqual(report["client_lifetime"], {
            "clients_constructed": 2,
            "clients_closed": 2,
        })
        self.assertEqual(
            report["durable_state"]["after_second_sha256"],
            report["durable_state"]["restart_replay_sha256"],
        )

    def test_incomplete_response_is_generic_and_rolls_back(self):
        def incomplete(request):
            return httpx.Response(
                200,
                headers={"x-request-id": "req_incomplete"},
                json=response_payload(status="incomplete"),
            )

        report = self.execute(incomplete)

        self.assertEqual(
            report["application_result"],
            "safe_provider_failure",
        )
        self.assertEqual(report["provider"]["attempt_count"], 1)
        self.assertEqual(
            report["durable_state"]["before_second_sha256"],
            report["durable_state"]["after_second_sha256"],
        )
        self.assertIsNone(
            report["durable_state"]["restart_replay_sha256"]
        )
        self.assertEqual(report["client_lifetime"], {
            "clients_constructed": 1,
            "clients_closed": 1,
        })

    def test_http_failure_is_generic_and_rolls_back_without_raw_error(self):
        def unauthorized(request):
            return httpx.Response(
                401,
                headers={"x-request-id": "req_unauthorized"},
                json={
                    "error": {
                        "message": TEST_API_KEY,
                        "type": "invalid_request_error",
                    }
                },
            )

        report = self.execute(unauthorized)
        report_text = (self.artifacts / REPORT_FILENAME).read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            report["application_result"],
            "safe_provider_failure",
        )
        self.assertEqual(report["provider"]["http_status"], 401)
        self.assertEqual(
            report["provider"]["result"],
            "authentication_failed",
        )
        self.assertEqual(report["provider"]["attempt_count"], 1)
        self.assertNotIn(TEST_API_KEY, report_text)
        self.assertEqual(
            report["durable_state"]["before_second_sha256"],
            report["durable_state"]["after_second_sha256"],
        )

    def test_authentication_result_survives_unfamiliar_request_id(self):
        def unauthorized(request):
            return httpx.Response(
                401,
                headers={
                    "x-request-id": "request id with unfamiliar formatting"
                },
                json={
                    "error": {
                        "message": "Incorrect API key provided",
                        "type": "invalid_request_error",
                    }
                },
            )

        report = self.execute(unauthorized)
        report_text = (self.artifacts / REPORT_FILENAME).read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            report["application_result"],
            "safe_provider_failure",
        )
        self.assertEqual(
            report["provider"]["result"],
            "authentication_failed",
        )
        self.assertEqual(report["provider"]["http_status"], 401)
        self.assertIsNone(report["provider"]["request_id"])
        self.assertEqual(
            report["provider"]["omitted_metadata"],
            ["request_id"],
        )
        self.assertNotIn("unfamiliar formatting", report_text)

    def test_transport_failure_is_generic_and_rolls_back(self):
        def fail(request):
            raise httpx.ConnectTimeout("synthetic timeout")

        report = self.execute(fail)

        self.assertEqual(
            report["application_result"],
            "safe_provider_failure",
        )
        self.assertTrue(report["provider"]["transport_failure"])
        self.assertEqual(
            report["provider"]["result"],
            "transport_failure",
        )
        self.assertEqual(report["provider"]["attempt_count"], 1)
        self.assertEqual(
            report["durable_state"]["before_second_sha256"],
            report["durable_state"]["after_second_sha256"],
        )

    def test_unfamiliar_or_credential_shaped_metadata_is_omitted(self):
        unsafe_values = (
            TEST_API_KEY,
            "sk-malicious-provider-header-value",
            "Bearer-hidden-authorization-material",
            "request id with spaces (edge)",
        )
        for value in unsafe_values:
            with self.subTest(value=value):
                report = self.execute(
                    completed_handler(request_id=value)
                )
                report_text = (
                    self.artifacts / REPORT_FILENAME
                ).read_text(encoding="utf-8")

                self.assertEqual(
                    report["application_result"],
                    "full_pass",
                )
                self.assertIsNone(report["provider"]["request_id"])
                self.assertEqual(
                    report["provider"]["omitted_metadata"],
                    ["request_id"],
                )
                self.assertNotIn(value, report_text)
                self.assertNotIn(TEST_API_KEY, report_text)
                (self.artifacts / REPORT_FILENAME).unlink()

    def test_alternate_response_model_format_is_omitted_not_fatal(self):
        def alternate_model(request):
            payload = response_payload()
            payload["model"] = "gpt-5.6-luna (snapshot candidate)"
            return httpx.Response(
                200,
                headers={"x-request-id": "req_alternate_model"},
                json=payload,
            )

        report = self.execute(alternate_model)

        self.assertEqual(report["application_result"], "full_pass")
        self.assertIsNone(report["provider"]["response_model"])
        self.assertEqual(
            report["provider"]["omitted_metadata"],
            ["response_model"],
        )

    def test_cli_refuses_without_billing_flag_and_writes_nothing(self):
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": TEST_API_KEY},
            clear=True,
        ):
            result = main(
                ["--artifact-dir", str(self.artifacts)]
            )

        self.assertEqual(result, 2)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_cli_prompt_mode_rejects_ambient_key_before_prompting(self):
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": TEST_API_KEY},
            clear=True,
        ):
            with patch(
                "scripts.validate_openai_live.capture_api_key"
            ) as capture:
                result = main([
                    "--artifact-dir",
                    str(self.artifacts),
                    "--confirm-one-billable-request",
                    "--prompt-for-api-key",
                ])

        self.assertEqual(result, 2)
        capture.assert_not_called()
        self.assertEqual(list(self.artifacts.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

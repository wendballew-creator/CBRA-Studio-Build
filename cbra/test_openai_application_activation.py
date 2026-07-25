"""Offline contracts for explicit OpenAI application activation."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from openai import OpenAI

from cbra.app import create_app
from cbra.application import NativeApplicationService
from cbra.corpus import CanonicalCorpusError
from cbra.providers import (
    ApplicationRendererActivationError,
    OpenAIResponsesArticulationRenderer,
    application_renderer_from_environment,
)
from cbra.store import NativeSessionRepository


TEST_API_KEY = "sk-activation-secret-that-must-not-persist"
ACCEPTED_TEXT = (
    "One formation keeps cedar roots and sheltering soil in relation.\n\n"
    "Another formation keeps river current, stone, and silt perceptible.\n\n"
    "Other material remains held open while the relation stays revisable."
)
FIRST_STRAND = "Cedar roots shelter soil and hold moisture."
RELATED_STRAND = "Cedar soil holds water around the roots."
THIRD_STRAND = "Cedar roots keep sheltering the changing soil."
THREAD_ID = "thread:{0}".format("a" * 32)
TURN_ONE = "turn:{0}".format("1" * 32)
TURN_TWO = "turn:{0}".format("2" * 32)
TURN_THREE = "turn:{0}".format("3" * 32)
TURN_FOUR = "turn:{0}".format("4" * 32)


def openai_environment(**overrides):
    values = {
        "CBRA_ARTICULATION_RENDERER": "openai-responses",
        "OPENAI_API_KEY": TEST_API_KEY,
        "CBRA_OPENAI_MODEL": "gpt-test-activation",
        "CBRA_OPENAI_REASONING_EFFORT": "low",
        "CBRA_OPENAI_TEXT_VERBOSITY": "medium",
        "CBRA_OPENAI_MAX_INPUT_CHARS": "20000",
        "CBRA_OPENAI_MAX_OUTPUT_TOKENS": "2048",
        "CBRA_OPENAI_MAX_OUTPUT_CHARS": "4096",
        "CBRA_OPENAI_TIMEOUT_SECONDS": "3.25",
    }
    values.update(overrides)
    return values


def response_payload(text=ACCEPTED_TEXT):
    return {
        "id": "resp_activation_test",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "model": "gpt-test-activation",
        "output": [
            {
                "id": "rs_activation_test",
                "type": "reasoning",
                "summary": [],
            },
            {
                "id": "msg_activation_test",
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
    }


class OwnedOpenAIClient:
    def __init__(self, client, owner):
        self._client = client
        self._owner = owner

    def __getattr__(self, name):
        return getattr(self._client, name)

    def close(self):
        self._owner.close_calls += 1
        self._client.close()


class RecordingOpenAIClientFactory:
    def __init__(self, handler=None):
        self.handler = handler or (
            lambda _: httpx.Response(200, json=response_payload())
        )
        self.constructor_calls = []
        self.requests = []
        self.close_calls = 0

    def __call__(self, **options):
        self.constructor_calls.append(dict(options))

        def record(request):
            self.requests.append(
                {
                    "body": json.loads(request.content.decode("utf-8")),
                    "url": str(request.url),
                }
            )
            return self.handler(request)

        http_client = httpx.Client(
            transport=httpx.MockTransport(record)
        )
        client = OpenAI(http_client=http_client, **options)
        return OwnedOpenAIClient(client, self)


class TrackingEnvironment(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads = []

    def get(self, name, default=None):
        self.reads.append(name)
        return super().get(name, default)


class OpenAIApplicationActivationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        corpus = self.root / "corpus"
        corpus.mkdir()
        filenames = (
            "CBRA_Glossary_v3.md",
            "CBRA_Loops_Core.md",
            "Drift_Constraints.md",
            "CBRA_Kernel_v10_2.md",
        )
        manifest = [
            "# Activation test corpus",
            "",
            "## Canonical Files (Active)",
        ]
        manifest.extend(
            "{0}. {1}".format(index, filename)
            for index, filename in enumerate(filenames, start=1)
        )
        (corpus / "CBRA_Corpus_Index.md").write_text(
            "\n".join(manifest) + "\n",
            encoding="utf-8",
        )
        for filename in filenames:
            (corpus / filename).write_text("", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def activation(self, environment=None, factory=None):
        resolved_factory = factory or RecordingOpenAIClientFactory()
        with patch(
            "cbra.providers.application_activation."
            "_load_openai_client_class",
            return_value=resolved_factory,
        ):
            activation = application_renderer_from_environment(
                environment or openai_environment()
            )
        return resolved_factory, activation

    def app(self, environment, factory, root=None):
        with patch.dict(os.environ, environment, clear=True):
            with patch(
                "cbra.providers.application_activation."
                "_load_openai_client_class",
                return_value=factory,
            ):
                return create_app(
                    session_root=root or self.root,
                    corpus_root=self.root / "corpus",
                )

    def test_native_mode_reads_only_selector_and_never_loads_sdk(self):
        environment = TrackingEnvironment(
            {
                "OPENAI_API_KEY": TEST_API_KEY,
                "OPENAI_BASE_URL": "https://redirect.invalid/v1",
                "CBRA_OPENAI_MODEL": "ignored-model",
            }
        )
        with patch(
            "cbra.providers.application_activation."
            "_load_openai_client_class",
            side_effect=AssertionError("SDK must remain unloaded"),
        ):
            activation = application_renderer_from_environment(environment)

        self.assertIsNone(activation.renderer)
        self.assertIsNone(activation.renderer_binding)
        self.assertEqual(
            environment.reads,
            ["CBRA_ARTICULATION_RENDERER"],
        )

        environment["CBRA_ARTICULATION_RENDERER"] = "native-template"
        environment.reads = []
        activation = application_renderer_from_environment(environment)
        self.assertIsNone(activation.renderer)
        self.assertEqual(
            environment.reads,
            ["CBRA_ARTICULATION_RENDERER"],
        )

    def test_key_alone_preserves_native_application_behavior(self):
        environment = {"OPENAI_API_KEY": TEST_API_KEY}
        with patch.dict(os.environ, environment, clear=True):
            with patch(
                "cbra.providers.application_activation."
                "_load_openai_client_class",
                side_effect=AssertionError("SDK must remain unloaded"),
            ):
                application = create_app(
                    session_root=self.root / "native",
                    corpus_root=self.root / "corpus",
                )

        service = application.state.native_service
        self.assertIsNone(service.renderer)
        self.assertIsNone(service.renderer_binding)

    def test_selector_is_exact_and_unknown_or_blank_stops_activation(self):
        for selector in ("", "openai", " openai-responses ", "NATIVE-TEMPLATE"):
            with self.subTest(selector=selector):
                with self.assertRaises(
                    ApplicationRendererActivationError
                ) as captured:
                    application_renderer_from_environment(
                        {"CBRA_ARTICULATION_RENDERER": selector}
                    )
                self.assertIsNone(captured.exception.__cause__)

    def test_every_openai_setting_is_required_before_client_construction(self):
        required = tuple(openai_environment())
        for name in required:
            if name == "CBRA_ARTICULATION_RENDERER":
                continue
            with self.subTest(name=name):
                environment = openai_environment()
                environment.pop(name)
                factory = RecordingOpenAIClientFactory()
                with patch(
                    "cbra.providers.application_activation."
                    "_load_openai_client_class",
                    return_value=factory,
                ):
                    with self.assertRaises(
                        ApplicationRendererActivationError
                    ) as captured:
                        application_renderer_from_environment(environment)
                self.assertEqual(factory.constructor_calls, [])
                self.assertNotIn(TEST_API_KEY, str(captured.exception))
                self.assertIsNone(captured.exception.__cause__)

    def test_invalid_numeric_and_renderer_values_are_sanitized(self):
        invalid = (
            {"CBRA_OPENAI_MODEL": "sk-proj-secret-value"},
            {"CBRA_OPENAI_REASONING_EFFORT": "automatic"},
            {"CBRA_OPENAI_TEXT_VERBOSITY": "extreme"},
            {"CBRA_OPENAI_MAX_INPUT_CHARS": "0"},
            {"CBRA_OPENAI_MAX_OUTPUT_TOKENS": "1.5"},
            {"CBRA_OPENAI_MAX_OUTPUT_CHARS": "32769"},
            {"CBRA_OPENAI_TIMEOUT_SECONDS": "inf"},
            {"CBRA_OPENAI_TIMEOUT_SECONDS": " 3.25 "},
        )
        for override in invalid:
            with self.subTest(override=override):
                factory = RecordingOpenAIClientFactory()
                with patch(
                    "cbra.providers.application_activation."
                    "_load_openai_client_class",
                    return_value=factory,
                ):
                    with self.assertRaises(
                        ApplicationRendererActivationError
                    ) as captured:
                        application_renderer_from_environment(
                            openai_environment(**override)
                        )
                self.assertEqual(factory.constructor_calls, [])
                self.assertNotIn(
                    next(iter(override.values())),
                    str(captured.exception),
                )
                self.assertNotIn(TEST_API_KEY, str(captured.exception))
                self.assertIsNone(captured.exception.__cause__)

    def test_ambient_openai_overrides_are_rejected_only_in_openai_mode(self):
        ambient = (
            "OPENAI_BASE_URL",
            "OPENAI_LOG",
            "OPENAI_ORGANIZATION",
            "OPENAI_ORG_ID",
            "OPENAI_PROJECT",
            "OPENAI_PROJECT_ID",
        )
        for name in ambient:
            with self.subTest(name=name):
                environment = openai_environment(**{name: ""})
                factory = RecordingOpenAIClientFactory()
                with patch(
                    "cbra.providers.application_activation."
                    "_load_openai_client_class",
                    return_value=factory,
                ):
                    with self.assertRaises(
                        ApplicationRendererActivationError
                    ):
                        application_renderer_from_environment(environment)
                self.assertEqual(factory.constructor_calls, [])

    def test_activation_constructs_one_explicit_client_and_stable_binding(self):
        environment = openai_environment()
        factory, activation = self.activation(environment)
        environment["CBRA_OPENAI_MODEL"] = "mutated-model"
        environment["CBRA_OPENAI_TIMEOUT_SECONDS"] = "99"

        self.assertIsInstance(
            activation.renderer,
            OpenAIResponsesArticulationRenderer,
        )
        self.assertEqual(
            activation.renderer_binding,
            activation.renderer.binding,
        )
        self.assertEqual(
            activation.renderer.binding.model_id,
            "gpt-test-activation",
        )
        self.assertEqual(
            activation.renderer.configuration.timeout_seconds,
            3.25,
        )
        self.assertEqual(len(factory.constructor_calls), 1)
        options = factory.constructor_calls[0]
        self.assertEqual(
            set(options),
            {"api_key", "base_url", "max_retries", "timeout"},
        )
        self.assertEqual(options["api_key"], TEST_API_KEY)
        self.assertEqual(
            options["base_url"],
            "https://api.openai.com/v1",
        )
        self.assertEqual(options["max_retries"], 0)
        self.assertEqual(options["timeout"], 3.25)
        self.assertEqual(factory.requests, [])

        activation.close()
        activation.close()
        self.assertEqual(factory.close_calls, 1)

    def test_client_construction_and_close_failures_are_sanitized(self):
        class FailingFactory:
            def __call__(self, **_):
                raise RuntimeError(TEST_API_KEY)

        with patch(
            "cbra.providers.application_activation."
            "_load_openai_client_class",
            return_value=FailingFactory(),
        ):
            with self.assertRaises(
                ApplicationRendererActivationError
            ) as captured:
                application_renderer_from_environment(
                    openai_environment()
                )
        self.assertNotIn(TEST_API_KEY, str(captured.exception))
        self.assertIsNone(captured.exception.__cause__)

        class FailingCloseClient:
            def close(self):
                raise RuntimeError(TEST_API_KEY)

        from cbra.providers import ApplicationRendererActivation

        activation = ApplicationRendererActivation(
            _client=FailingCloseClient()
        )
        with self.assertRaises(
            ApplicationRendererActivationError
        ) as captured:
            activation.close()
        self.assertNotIn(TEST_API_KEY, str(captured.exception))
        self.assertIsNone(captured.exception.__cause__)
        activation.close()

    def test_invalid_configuration_precedes_session_directory_creation(self):
        session_root = self.root / "must-not-exist"
        environment = openai_environment()
        environment.pop("CBRA_OPENAI_MODEL")
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(ApplicationRendererActivationError):
                create_app(
                    session_root=session_root,
                    corpus_root=self.root / "corpus",
                )
        self.assertFalse(session_root.exists())

    def test_owned_client_closes_if_later_bootstrap_validation_fails(self):
        invalid_corpus = self.root / "invalid-corpus"
        invalid_corpus.mkdir()
        session_root = self.root / "must-still-not-exist"
        factory = RecordingOpenAIClientFactory()
        with patch.dict(os.environ, openai_environment(), clear=True):
            with patch(
                "cbra.providers.application_activation."
                "_load_openai_client_class",
                return_value=factory,
            ):
                with self.assertRaises(CanonicalCorpusError):
                    create_app(
                        session_root=session_root,
                        corpus_root=invalid_corpus,
                    )
        self.assertEqual(len(factory.constructor_calls), 1)
        self.assertEqual(factory.requests, [])
        self.assertEqual(factory.close_calls, 1)
        self.assertFalse(session_root.exists())

    def test_supplied_service_bypasses_invalid_provider_environment(self):
        supplied_root = self.root / "supplied"
        supplied_root.mkdir()
        repository = NativeSessionRepository(supplied_root)
        service = NativeApplicationService(repository)
        environment = {
            "CBRA_ARTICULATION_RENDERER": "invalid-provider",
            "OPENAI_API_KEY": TEST_API_KEY,
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch(
                "cbra.providers.application_activation."
                "_load_openai_client_class",
                side_effect=AssertionError("must remain unloaded"),
            ):
                application = create_app(service=service)
        self.assertIs(application.state.native_service, service)

    def test_health_ui_and_sparse_turn_make_no_provider_request(self):
        factory = RecordingOpenAIClientFactory()
        application = self.app(openai_environment(), factory)

        with TestClient(
            application,
            raise_server_exceptions=False,
        ) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/ui").status_code, 200)
            self.assertEqual(client.get("/openapi.json").status_code, 200)
            created = client.post(
                "/generate",
                json={
                    "thread_id": THREAD_ID,
                    "user_text": FIRST_STRAND,
                    "turn_id": TURN_ONE,
                },
            )
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json()["outcome"], "no_articulation")
            self.assertEqual(factory.requests, [])

        self.assertEqual(factory.close_calls, 1)

    def test_renderable_turn_uses_provider_once_without_persisting_key(self):
        factory = RecordingOpenAIClientFactory()
        session_root = self.root / "render"
        application = self.app(
            openai_environment(),
            factory,
            root=session_root,
        )
        with TestClient(
            application,
            raise_server_exceptions=False,
        ) as client:
            created = client.post(
                "/generate",
                json={
                    "thread_id": THREAD_ID,
                    "user_text": FIRST_STRAND,
                    "turn_id": TURN_ONE,
                },
            )
            response = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": RELATED_STRAND,
                    "turn_id": TURN_TWO,
                    "expected_revision": 1,
                },
            )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["outcome"],
            "accepted_articulation",
        )
        self.assertEqual(response.json()["text"], ACCEPTED_TEXT)
        self.assertEqual(len(factory.requests), 1)
        request = factory.requests[0]
        self.assertEqual(
            request["url"],
            "https://api.openai.com/v1/responses",
        )
        self.assertIs(request["body"]["store"], False)
        self.assertNotIn(TEST_API_KEY, json.dumps(request["body"]))
        persisted = b"".join(
            path.read_bytes()
            for path in session_root.iterdir()
            if path.is_file()
        )
        self.assertNotIn(TEST_API_KEY.encode("utf-8"), persisted)
        self.assertNotIn(
            b"resp_activation_test",
            persisted,
        )

    def test_provider_failure_uses_generic_500_and_rolls_back(self):
        def fail(_):
            return httpx.Response(
                500,
                json={"error": {"message": TEST_API_KEY}},
            )

        factory = RecordingOpenAIClientFactory(handler=fail)
        session_root = self.root / "failure"
        application = self.app(
            openai_environment(),
            factory,
            root=session_root,
        )
        with TestClient(
            application,
            raise_server_exceptions=False,
        ) as client:
            created = client.post(
                "/generate",
                json={
                    "thread_id": THREAD_ID,
                    "user_text": FIRST_STRAND,
                    "turn_id": TURN_ONE,
                },
            )
            repository = application.state.native_service.repository
            path = repository.path_for(THREAD_ID)
            before = path.read_bytes()
            response = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": RELATED_STRAND,
                    "turn_id": TURN_TWO,
                    "expected_revision": 1,
                },
            )
            after = path.read_bytes()

        self.assertEqual(created.status_code, 201)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["error"]["code"],
            "internal_error",
        )
        self.assertNotIn(TEST_API_KEY, response.text)
        self.assertEqual(len(factory.requests), 1)
        self.assertEqual(after, before)

    def test_restart_replay_and_binding_mismatch_preserve_durable_state(self):
        session_root = self.root / "restart"
        environment = openai_environment()
        first_factory = RecordingOpenAIClientFactory()
        first_app = self.app(environment, first_factory, root=session_root)
        with TestClient(
            first_app,
            raise_server_exceptions=False,
        ) as client:
            self.assertEqual(
                client.post(
                    "/generate",
                    json={
                        "thread_id": THREAD_ID,
                        "user_text": FIRST_STRAND,
                        "turn_id": TURN_ONE,
                    },
                ).status_code,
                201,
            )
            second = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": RELATED_STRAND,
                    "turn_id": TURN_TWO,
                    "expected_revision": 1,
                },
            )
            self.assertEqual(second.status_code, 200)
        self.assertEqual(len(first_factory.requests), 1)

        second_factory = RecordingOpenAIClientFactory()
        second_app = self.app(environment, second_factory, root=session_root)
        with TestClient(
            second_app,
            raise_server_exceptions=False,
        ) as client:
            third = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": THIRD_STRAND,
                    "turn_id": TURN_THREE,
                    "expected_revision": 2,
                },
            )
            self.assertEqual(third.status_code, 200)
            replay = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": THIRD_STRAND,
                    "turn_id": TURN_THREE,
                    "expected_revision": 2,
                },
            )
            self.assertEqual(replay.status_code, 200)
            self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(len(second_factory.requests), 1)

        changed_environment = openai_environment(
            CBRA_OPENAI_MODEL="gpt-different-binding"
        )
        changed_factory = RecordingOpenAIClientFactory()
        changed_app = self.app(
            changed_environment,
            changed_factory,
            root=session_root,
        )
        repository = changed_app.state.native_service.repository
        path = repository.path_for(THREAD_ID)
        before = path.read_bytes()
        with TestClient(
            changed_app,
            raise_server_exceptions=False,
        ) as client:
            summary = client.get(
                "/thread/{0}".format(THREAD_ID)
            )
            transcript = client.get(
                "/thread/{0}/turns".format(THREAD_ID)
            )
            replay = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": THIRD_STRAND,
                    "turn_id": TURN_THREE,
                    "expected_revision": 2,
                },
            )
            mismatch = client.post(
                "/chat/{0}".format(THREAD_ID),
                json={
                    "user_text": "A fourth new strand.",
                    "turn_id": TURN_FOUR,
                    "expected_revision": 3,
                },
            )
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(transcript.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(mismatch.status_code, 500)
        self.assertEqual(
            mismatch.json()["error"]["code"],
            "internal_error",
        )
        self.assertEqual(changed_factory.requests, [])
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

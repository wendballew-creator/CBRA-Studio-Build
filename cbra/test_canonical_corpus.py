"""Strict canonical-corpus snapshot and native bootstrap contracts."""

import hashlib
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cbra.app import PROJECT_ROOT, create_app
from cbra.application import NativeApplicationService
from cbra.corpus import (
    ACTIVE_SECTION,
    CANONICAL_MANIFEST,
    CANONICAL_ROLE_MAP,
    CanonicalCorpusError,
    CorpusLimits,
    load_canonical_snapshot,
)
from cbra.store import NativeSessionRepository


FILENAMES = (
    "CBRA_Glossary_v3.md",
    "CBRA_Loops_Core.md",
    "Drift_Constraints.md",
    "CBRA_Kernel_v10_2.md",
)
THREAD_A = "thread:{0}".format("a" * 32)
THREAD_B = "thread:{0}".format("b" * 32)
THREAD_C = "thread:{0}".format("c" * 32)
TURN_A = "turn:{0}".format("1" * 32)
TURN_B = "turn:{0}".format("2" * 32)
TURN_C = "turn:{0}".format("3" * 32)


def _manifest(filenames=FILENAMES):
    lines = [
        "# Test corpus",
        "",
        ACTIVE_SECTION,
    ]
    lines.extend(
        "{0}. {1}".format(index, filename)
        for index, filename in enumerate(filenames, start=1)
    )
    lines.extend(["", "## Notes", "- test fixture"])
    return "\n".join(lines) + "\n"


def _write_corpus(root, texts=None, filenames=FILENAMES):
    root.mkdir(parents=True, exist_ok=True)
    selected = texts or {
        filename: "Complete canonical strand number {0}.".format(index)
        for index, filename in enumerate(filenames, start=1)
    }
    (root / CANONICAL_MANIFEST).write_text(
        _manifest(filenames),
        encoding="utf-8",
    )
    for filename in filenames:
        (root / filename).write_text(
            selected[filename],
            encoding="utf-8",
        )
    return selected


def _canonical_streams(session):
    return [
        stream
        for stream in session.field.streams
        if stream.provenance.get("source") == "canonical_corpus"
    ]


class CanonicalCorpusSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_repository_snapshot_is_ordered_complete_and_content_addressed(
        self,
    ):
        corpus_root = PROJECT_ROOT / "corpus"
        first = load_canonical_snapshot(corpus_root)
        second = load_canonical_snapshot(corpus_root)

        self.assertEqual(
            tuple(source.filename for source in first.sources),
            FILENAMES,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first.sources), 4)
        self.assertEqual(len(first.manifest_digest), 64)
        self.assertEqual(len(first.corpus_digest), 64)

        streams = first.to_streams()
        streams_again = first.to_streams()
        self.assertEqual(
            [item.stream_id for item in streams],
            [item.stream_id for item in streams_again],
        )
        self.assertIsNot(streams[0], streams_again[0])
        streams[0].payload["text"] = "mutated copy"
        self.assertEqual(streams_again[0].payload["text"], first.sources[0].text)
        for source, stream in zip(first.sources, streams_again):
            expected = (corpus_root / source.filename).read_text(
                encoding="utf-8"
            )
            self.assertEqual(source.text, expected)
            self.assertEqual(stream.payload["text"], expected)
            self.assertEqual(stream.kind, "document")
            self.assertEqual(
                stream.payload["material_handle"],
                "canonical:{0}".format(source.filename),
            )
            self.assertEqual(
                stream.payload["canonical_role"],
                CANONICAL_ROLE_MAP[source.filename],
            )
            self.assertEqual(
                stream.payload["content_digest"],
                hashlib.sha256(expected.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(
                stream.provenance["source"],
                "canonical_corpus",
            )
            self.assertTrue(
                stream.provenance["immutable_snapshot"]
            )
            self.assertEqual(
                stream.payload["corpus_digest"],
                first.corpus_digest,
            )

    def test_missing_empty_duplicate_and_malformed_manifests_fail_closed(
        self,
    ):
        cases = {
            "missing": None,
            "empty": "# Test\n\n{0}\n\n## Notes\n".format(
                ACTIVE_SECTION
            ),
            "duplicate_entry": _manifest(
                (FILENAMES[0], FILENAMES[0])
            ),
            "duplicate_section": (
                _manifest((FILENAMES[0],))
                + "\n{0}\n1. {1}\n".format(
                    ACTIVE_SECTION,
                    FILENAMES[1],
                )
            ),
            "malformed_entry": (
                "# Test\n\n{0}\n- {1}\n".format(
                    ACTIVE_SECTION,
                    FILENAMES[0],
                )
            ),
            "noncontiguous": (
                "# Test\n\n{0}\n2. {1}\n".format(
                    ACTIVE_SECTION,
                    FILENAMES[0],
                )
            ),
        }
        for name, manifest in cases.items():
            with self.subTest(name=name):
                root = self.root / name
                root.mkdir()
                if manifest is not None:
                    (root / CANONICAL_MANIFEST).write_text(
                        manifest,
                        encoding="utf-8",
                    )
                with self.assertRaises(CanonicalCorpusError):
                    load_canonical_snapshot(root)

    def test_manifest_notes_do_not_change_the_active_snapshot(self):
        root = self.root / "notes"
        _write_corpus(root)
        first = load_canonical_snapshot(root)
        with (root / CANONICAL_MANIFEST).open(
            "a",
            encoding="utf-8",
        ) as manifest:
            manifest.write("- a changed non-active note\n")
        second = load_canonical_snapshot(root)

        self.assertEqual(first.manifest_digest, second.manifest_digest)
        self.assertEqual(first.corpus_digest, second.corpus_digest)
        self.assertEqual(first.sources, second.sources)

    def test_unsafe_missing_unreadable_and_unmapped_sources_fail_closed(
        self,
    ):
        cases = {
            "absolute": "/tmp/escaped.md",
            "traversal": "../escaped.md",
            "windows": "C:\\escaped.md",
            "missing": FILENAMES[0],
            "unmapped": "Unknown.md",
        }
        for name, filename in cases.items():
            with self.subTest(name=name):
                root = self.root / name
                root.mkdir()
                (root / CANONICAL_MANIFEST).write_text(
                    _manifest((filename,)),
                    encoding="utf-8",
                )
                with self.assertRaises(CanonicalCorpusError):
                    load_canonical_snapshot(root)

        unreadable = self.root / "unreadable"
        _write_corpus(unreadable, filenames=(FILENAMES[0],))
        original_read_bytes = Path.read_bytes

        def deny_source(path):
            if path.name == FILENAMES[0]:
                raise PermissionError("denied")
            return original_read_bytes(path)

        with patch.object(Path, "read_bytes", deny_source):
            with self.assertRaises(CanonicalCorpusError):
                load_canonical_snapshot(unreadable)

    def test_symlink_escape_and_malformed_utf8_fail_closed(self):
        outside = self.root / FILENAMES[0]
        outside.write_text("outside", encoding="utf-8")
        escaped = self.root / "escaped"
        escaped.mkdir()
        (escaped / CANONICAL_MANIFEST).write_text(
            _manifest((FILENAMES[0],)),
            encoding="utf-8",
        )
        (escaped / FILENAMES[0]).symlink_to(outside)
        with self.assertRaises(CanonicalCorpusError):
            load_canonical_snapshot(escaped)

        escaped_manifest = self.root / "escaped-manifest"
        escaped_manifest.mkdir()
        outside_manifest = self.root / "outside-manifest.md"
        outside_manifest.write_text(
            _manifest((FILENAMES[0],)),
            encoding="utf-8",
        )
        (escaped_manifest / CANONICAL_MANIFEST).symlink_to(
            outside_manifest
        )
        with self.assertRaises(CanonicalCorpusError):
            load_canonical_snapshot(escaped_manifest)

        malformed = self.root / "malformed"
        malformed.mkdir()
        (malformed / CANONICAL_MANIFEST).write_text(
            _manifest((FILENAMES[0],)),
            encoding="utf-8",
        )
        (malformed / FILENAMES[0]).write_bytes(b"\xff\xfe")
        with self.assertRaises(CanonicalCorpusError):
            load_canonical_snapshot(malformed)

        malformed_manifest = self.root / "malformed-manifest"
        malformed_manifest.mkdir()
        (malformed_manifest / CANONICAL_MANIFEST).write_bytes(b"\xff\xfe")
        with self.assertRaises(CanonicalCorpusError):
            load_canonical_snapshot(malformed_manifest)

    def test_file_count_per_file_total_and_environment_limits_are_strict(
        self,
    ):
        corpus = self.root / "bounded"
        _write_corpus(corpus)

        with self.assertRaises(CanonicalCorpusError):
            load_canonical_snapshot(
                corpus,
                limits=CorpusLimits(
                    max_files=3,
                    max_file_bytes=1024,
                    max_total_bytes=4096,
                ),
            )
        with self.assertRaises(CanonicalCorpusError):
            (corpus / FILENAMES[0]).write_text(
                "x" * 2048,
                encoding="utf-8",
            )
            load_canonical_snapshot(
                corpus,
                limits=CorpusLimits(
                    max_files=4,
                    max_file_bytes=1024,
                    max_total_bytes=4096,
                ),
            )
        _write_corpus(corpus)
        with self.assertRaises(CanonicalCorpusError):
            load_canonical_snapshot(
                corpus,
                limits=CorpusLimits(
                    max_files=4,
                    max_file_bytes=1024,
                    max_total_bytes=64,
                ),
            )

        for invalid in ("", "0", "-1", "1.5", " 2"):
            with self.subTest(environment_limit=invalid):
                with self.assertRaises(CanonicalCorpusError):
                    CorpusLimits.from_environment(
                        {"CBRA_CORPUS_MAX_FILES": invalid}
                    )


class CanonicalSessionBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "corpus"
        self.sessions = self.root / "sessions"
        self.texts = _write_corpus(self.corpus)

    def tearDown(self):
        self.temporary.cleanup()

    def _app(self):
        return create_app(
            session_root=self.sessions,
            corpus_root=self.corpus,
        )

    @staticmethod
    def _create(client, thread_id=THREAD_A, turn_id=TURN_A):
        return client.post(
            "/generate",
            json={
                "thread_id": thread_id,
                "turn_id": turn_id,
                "user_text": "How does this material move together?",
            },
        )

    def test_new_thread_persists_four_canonical_streams_once_and_privately(
        self,
    ):
        app = self._app()
        with TestClient(app, raise_server_exceptions=False) as client:
            first = self._create(client)
            replay = self._create(client)
            summary = client.get("/thread/{0}".format(THREAD_A))
            turns = client.get(
                "/thread/{0}/turns".format(THREAD_A)
            )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["idempotent_replay"])
        session = app.state.native_service.repository.load(THREAD_A)
        canonical = _canonical_streams(session)
        self.assertEqual(session.revision, 1)
        self.assertEqual(len(session.turns), 1)
        self.assertEqual(session.turns[0].additional_stream_ids, ())
        self.assertEqual(
            [item.payload["filename"] for item in canonical],
            list(FILENAMES),
        )
        self.assertEqual(len(canonical), 4)
        for stream in canonical:
            filename = stream.payload["filename"]
            self.assertEqual(
                stream.payload["text"],
                self.texts[filename],
            )
            self.assertEqual(
                stream.provenance["canonical_role"],
                CANONICAL_ROLE_MAP[filename],
            )
            self.assertEqual(
                stream.provenance["corpus_digest"],
                app.state.native_service.canonical_corpus.corpus_digest,
            )

        for response in (first, replay, summary, turns):
            self.assertNotIn("stream:canonical:", response.text)
            self.assertNotIn("content_digest", response.text)
            self.assertNotIn("corpus_digest", response.text)
            for filename in FILENAMES:
                self.assertNotIn(filename, response.text)

    def test_unconfigured_application_uses_repository_corpus(self):
        with patch.dict(os.environ, {}, clear=False):
            configured = os.environ.pop("CBRA_CORPUS_ROOT", None)
            try:
                app = create_app(
                    session_root=self.root / "default-sessions"
                )
            finally:
                if configured is not None:
                    os.environ["CBRA_CORPUS_ROOT"] = configured
        snapshot = app.state.native_service.canonical_corpus
        self.assertEqual(Path(snapshot.root), (PROJECT_ROOT / "corpus").resolve())
        self.assertEqual(
            tuple(source.filename for source in snapshot.sources),
            FILENAMES,
        )

    def test_concurrent_identical_creation_converges_with_one_snapshot(
        self,
    ):
        snapshot = load_canonical_snapshot(self.corpus)
        self.sessions.mkdir()
        repository = NativeSessionRepository(self.sessions)
        service = NativeApplicationService(
            repository,
            canonical_corpus=snapshot,
        )

        def create():
            return service.create_thread(
                THREAD_A,
                "How does this material move together?",
                turn_id=TURN_A,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: create(), range(8)))

        self.assertEqual(
            sum(not result.replayed for result in results),
            1,
        )
        self.assertEqual(
            sum(result.replayed for result in results),
            7,
        )
        session = repository.load(THREAD_A)
        self.assertEqual(session.revision, 1)
        self.assertEqual(len(session.turns), 1)
        self.assertEqual(len(_canonical_streams(session)), 4)
        self.assertEqual(
            len(list(self.sessions.glob("native-session-*"))),
            1,
        )

    def test_process_snapshot_is_immutable_and_restart_uses_new_snapshot(
        self,
    ):
        first_app = self._app()
        first_client = TestClient(
            first_app,
            raise_server_exceptions=False,
        )
        self.assertEqual(self._create(first_client).status_code, 201)
        original = first_app.state.native_service.repository.load(
            THREAD_A
        )
        original_canonical = _canonical_streams(original)
        original_stream = _canonical_streams(original)[0]
        original_text = original_stream.payload["text"]
        original_digest = original_stream.payload["content_digest"]

        changed_text = original_text + "\nA changed process corpus."
        (self.corpus / FILENAMES[0]).write_text(
            changed_text,
            encoding="utf-8",
        )
        same_process = self._create(
            first_client,
            thread_id=THREAD_B,
            turn_id=TURN_B,
        )
        self.assertEqual(same_process.status_code, 201)
        second_old_stream = _canonical_streams(
            first_app.state.native_service.repository.load(THREAD_B)
        )[0]
        self.assertEqual(second_old_stream.payload["text"], original_text)
        self.assertEqual(
            second_old_stream.payload["content_digest"],
            original_digest,
        )
        first_client.close()

        restarted = self._app()
        restored_before_continuation = (
            restarted.state.native_service.repository.load(THREAD_A)
        )
        self.assertEqual(
            _canonical_streams(restored_before_continuation),
            original_canonical,
        )
        with TestClient(
            restarted,
            raise_server_exceptions=False,
        ) as client:
            replay = self._create(client)
            continuation = client.post(
                "/chat/{0}".format(THREAD_A),
                json={
                    "turn_id": TURN_B,
                    "user_text": "Continue the existing durable session.",
                    "expected_revision": 1,
                },
            )
            new_thread = self._create(
                client,
                thread_id=THREAD_C,
                turn_id=TURN_C,
            )

        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(continuation.status_code, 200)
        self.assertEqual(new_thread.status_code, 201)
        older = restarted.state.native_service.repository.load(THREAD_A)
        newer = restarted.state.native_service.repository.load(THREAD_C)
        older_stream = _canonical_streams(older)[0]
        newer_stream = _canonical_streams(newer)[0]
        self.assertEqual(older_stream.payload["text"], original_text)
        self.assertEqual(
            older_stream.payload["content_digest"],
            original_digest,
        )
        self.assertEqual(newer_stream.payload["text"], changed_text)
        self.assertNotEqual(
            newer_stream.payload["content_digest"],
            original_digest,
        )
        self.assertNotEqual(
            newer_stream.stream_id,
            older_stream.stream_id,
        )

    def test_environment_root_is_loaded_once_and_invalid_corpus_stops_startup(
        self,
    ):
        with patch.dict(
            os.environ,
            {"CBRA_CORPUS_ROOT": str(self.corpus)},
            clear=False,
        ):
            app = create_app(session_root=self.sessions)
        self.assertEqual(
            Path(app.state.native_service.canonical_corpus.root),
            self.corpus.resolve(),
        )

        invalid = self.root / "invalid"
        invalid.mkdir()
        invalid_sessions = self.root / "other-sessions"
        with self.assertRaises(CanonicalCorpusError):
            create_app(
                session_root=invalid_sessions,
                corpus_root=invalid,
            )
        self.assertFalse(invalid_sessions.exists())


if __name__ == "__main__":
    unittest.main()

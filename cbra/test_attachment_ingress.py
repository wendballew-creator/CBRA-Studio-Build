"""Transactional native attachment-ingress contracts."""

import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from cbra.app import create_app
from cbra.application import NativeApplicationService
from cbra.attachments import (
    AttachmentLimits,
    AttachmentTooLargeError,
    InvalidAttachmentError,
    UploadedAttachment,
    build_attachment_streams,
)
from cbra.store import NativeSessionRepository


THREAD_A = "thread:{0}".format("a" * 32)
THREAD_B = "thread:{0}".format("b" * 32)
TURN_A = "turn:{0}".format("1" * 32)
TURN_B = "turn:{0}".format("2" * 32)
ATTACHMENT_A = "attachment:{0}".format("3" * 32)
ATTACHMENT_B = "attachment:{0}".format("4" * 32)
USER_TEXT = "Read the attached material diffractively."


def _docx_bytes(text):
    document = Document()
    document.add_paragraph(text)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _pdf_bytes(text, page_count=1):
    writer = PdfWriter()
    for index in range(page_count):
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_reference = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): font_reference}
                )
            }
        )
        stream = DecodedStreamObject()
        page_text = "{0} {1}".format(text, index + 1)
        stream.set_data(
            (
                "BT /F1 12 Tf 72 720 Td ({0}) Tj ET".format(
                    page_text
                )
            ).encode("ascii")
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _encrypted_pdf_bytes():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("private")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class AttachmentIngressApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.application = create_app(session_root=self.root)
        self.client = TestClient(
            self.application,
            raise_server_exceptions=False,
        )

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def _create(
        self,
        attachments,
        *,
        thread_id=THREAD_A,
        turn_id=TURN_A,
        user_text=USER_TEXT,
    ):
        data = {
            "thread_id": thread_id,
            "user_text": user_text,
            "turn_id": turn_id,
            "attachment_id": [],
        }
        files = []
        for attachment_id, filename, content, media_type in attachments:
            data["attachment_id"].append(attachment_id)
            files.append(
                ("files", (filename, content, media_type))
            )
        return self.client.post(
            "/generate/attachments",
            data=data,
            files=files,
        )

    def _continue(
        self,
        attachments,
        *,
        thread_id=THREAD_A,
        turn_id=TURN_B,
        expected_revision=1,
        user_text=USER_TEXT,
    ):
        data = {
            "user_text": user_text,
            "turn_id": turn_id,
            "expected_revision": str(expected_revision),
            "attachment_id": [],
        }
        files = []
        for attachment_id, filename, content, media_type in attachments:
            data["attachment_id"].append(attachment_id)
            files.append(
                ("files", (filename, content, media_type))
            )
        return self.client.post(
            "/chat/{0}/attachments".format(thread_id),
            data=data,
            files=files,
        )

    def test_creation_is_order_stable_durable_and_idempotent(self):
        alpha = b"Alpha remains complete.\nSecond line."
        beta = b"# Beta\n\nDifference remains present."
        first_attachments = [
            (
                ATTACHMENT_B,
                "beta.md",
                beta,
                "text/markdown",
            ),
            (
                ATTACHMENT_A,
                "alpha.txt",
                alpha,
                "text/plain",
            ),
        ]

        first = self._create(first_attachments)

        self.assertEqual(first.status_code, 201)
        repository = self.application.state.native_service.repository
        session = repository.load(THREAD_A)
        canonical = [
            item
            for item in session.field.streams
            if item.provenance.get("source") == "canonical_corpus"
        ]
        attachments = [
            item
            for item in session.field.streams
            if item.kind == "attachment"
        ]
        self.assertEqual(len(canonical), 4)
        self.assertEqual(len(attachments), 2)
        self.assertEqual(
            [item.payload["attachment_id"] for item in attachments],
            [ATTACHMENT_A, ATTACHMENT_B],
        )
        self.assertEqual(
            session.turns[0].additional_stream_ids,
            tuple(item.stream_id for item in attachments),
        )
        self.assertEqual(
            attachments[0].payload["text"],
            alpha.decode("utf-8"),
        )
        self.assertEqual(
            attachments[1].payload["text"],
            beta.decode("utf-8"),
        )
        for stream in attachments:
            self.assertEqual(stream.kind, "attachment")
            self.assertEqual(
                stream.provenance["source"],
                "user_attachment",
            )
            self.assertEqual(stream.payload["thread_id"], THREAD_A)
            self.assertEqual(stream.payload["turn_id"], TURN_A)
            self.assertEqual(
                len(stream.payload["raw_content_sha256"]),
                64,
            )
            self.assertEqual(
                len(stream.payload["extracted_text_sha256"]),
                64,
            )

        retry = self._create(list(reversed(first_attachments)))

        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.json()["idempotent_replay"])
        self.assertEqual(repository.load(THREAD_A), session)

        self.client.close()
        restarted = create_app(session_root=self.root)
        self.application = restarted
        self.client = TestClient(
            restarted,
            raise_server_exceptions=False,
        )
        replay_after_restart = self._create(first_attachments)
        self.assertEqual(replay_after_restart.status_code, 200)
        self.assertTrue(
            replay_after_restart.json()["idempotent_replay"]
        )
        self.assertEqual(
            restarted.state.native_service.repository.load(THREAD_A),
            session,
        )

    def test_all_supported_formats_extract_complete_text(self):
        docx_text = "DOCX body remains available."
        pdf_text = "PDF body remains available"
        response = self._create(
            [
                (
                    ATTACHMENT_A,
                    "notes.docx",
                    _docx_bytes(docx_text),
                    (
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document"
                    ),
                ),
                (
                    ATTACHMENT_B,
                    "evidence.pdf",
                    _pdf_bytes(pdf_text),
                    "application/pdf",
                ),
            ]
        )

        self.assertEqual(response.status_code, 201)
        session = (
            self.application.state.native_service.repository.load(
                THREAD_A
            )
        )
        by_name = {
            item.payload["filename"]: item
            for item in session.field.streams
            if item.kind == "attachment"
        }
        self.assertIn(docx_text, by_name["notes.docx"].payload["text"])
        self.assertIn(pdf_text, by_name["evidence.pdf"].payload["text"])
        self.assertEqual(
            by_name["notes.docx"].payload["extractor"],
            "docx-ooxml-text-v1",
        )
        self.assertEqual(
            by_name["evidence.pdf"].payload["extractor"],
            "pypdf-text-v1",
        )

    def test_continuation_persists_privately_and_projects_only_turn_text(self):
        first = self.client.post(
            "/generate",
            json={
                "thread_id": THREAD_A,
                "turn_id": TURN_A,
                "user_text": "Begin the native thread.",
            },
        )
        self.assertEqual(first.status_code, 201)
        content = b"Attachment evidence stays full thickness."

        response = self._continue(
            [
                (
                    ATTACHMENT_A,
                    "evidence.txt",
                    content,
                    "text/plain",
                )
            ]
        )

        self.assertEqual(response.status_code, 200)
        repository = self.application.state.native_service.repository
        session = repository.load(THREAD_A)
        self.assertEqual(session.revision, 2)
        self.assertEqual(len(session.turns[1].additional_stream_ids), 1)
        attachment_id = session.turns[1].additional_stream_ids[0]
        attachment = next(
            item
            for item in session.field.streams
            if item.stream_id == attachment_id
        )
        self.assertEqual(attachment.payload["text"], content.decode())

        summary = self.client.get(
            "/thread/{0}".format(THREAD_A)
        )
        projection = self.client.get(
            "/thread/{0}/turns".format(THREAD_A)
        )
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(projection.status_code, 200)
        for forbidden in (
            "attachment_id",
            "raw_content_sha256",
            "extracted_text_sha256",
            "raw_byte_count",
            "extractor",
            "evidence.txt",
        ):
            self.assertNotIn(forbidden, summary.text)
            self.assertNotIn(forbidden, projection.text)

        before = repository.path_for(THREAD_A).read_bytes()
        self.client.close()
        restarted = create_app(session_root=self.root)
        self.application = restarted
        self.client = TestClient(
            restarted,
            raise_server_exceptions=False,
        )
        restored = (
            restarted.state.native_service.repository.load(THREAD_A)
        )
        self.assertEqual(restored, session)
        retry = self._continue(
            [
                (
                    ATTACHMENT_A,
                    "evidence.txt",
                    content,
                    "text/plain",
                )
            ]
        )
        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.json()["idempotent_replay"])
        self.assertEqual(
            restarted.state.native_service.repository.path_for(
                THREAD_A
            ).read_bytes(),
            before,
        )

    def test_changed_turn_material_conflicts_without_mutation(self):
        original = [
            (
                ATTACHMENT_A,
                "draft.txt",
                b"Original attachment.",
                "text/plain",
            )
        ]
        self.assertEqual(self._create(original).status_code, 201)
        repository = self.application.state.native_service.repository
        before = repository.load(THREAD_A)

        changed_requests = [
            (
                [
                    (
                        ATTACHMENT_A,
                        "draft.txt",
                        b"Original attachment.",
                        "text/plain",
                    )
                ],
                "Changed user material.",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "draft.txt",
                        b"Changed attachment.",
                        "text/plain",
                    )
                ],
                USER_TEXT,
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "renamed.txt",
                        b"Original attachment.",
                        "text/plain",
                    )
                ],
                USER_TEXT,
            ),
            (
                [
                    (
                        ATTACHMENT_B,
                        "draft.txt",
                        b"Original attachment.",
                        "text/plain",
                    )
                ],
                USER_TEXT,
            ),
            (
                original
                + [
                    (
                        ATTACHMENT_B,
                        "second.txt",
                        b"Second attachment.",
                        "text/plain",
                    )
                ],
                USER_TEXT,
            ),
        ]
        for attachments, user_text in changed_requests:
            response = self._create(
                attachments,
                user_text=user_text,
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(
                response.json()["error"]["code"],
                "turn_conflict",
            )
            self.assertEqual(repository.load(THREAD_A), before)

    def test_invalid_unsupported_and_oversized_files_never_mutate(self):
        cases = [
            (
                [
                    (
                        ATTACHMENT_A,
                        "table.csv",
                        b"a,b\n1,2",
                        "text/csv",
                    )
                ],
                415,
                "unsupported_attachment",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "false.txt",
                        _pdf_bytes("disguised"),
                        "text/plain",
                    )
                ],
                422,
                "invalid_attachment",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "encrypted.pdf",
                        _encrypted_pdf_bytes(),
                        "application/pdf",
                    )
                ],
                422,
                "invalid_attachment",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "../unsafe.txt",
                        b"Text.",
                        "text/plain",
                    )
                ],
                422,
                "invalid_attachment",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "broken.docx",
                        b"PK\x03\x04not-a-docx",
                        (
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                    )
                ],
                422,
                "invalid_attachment",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "broken.txt",
                        b"\xff\xfe\xfd",
                        "text/plain",
                    )
                ],
                422,
                "invalid_attachment",
            ),
            (
                [
                    (
                        ATTACHMENT_A,
                        "empty.md",
                        b"",
                        "text/markdown",
                    )
                ],
                422,
                "invalid_attachment",
            ),
            (
                [
                    (
                        "attachment:not-a-claim",
                        "notes.txt",
                        b"Text.",
                        "text/plain",
                    )
                ],
                422,
                "invalid_attachment",
            ),
        ]
        for index, (attachments, status, code) in enumerate(cases):
            thread_id = "thread:{0}".format(
                format(index + 1, "032x")
            )
            response = self._create(
                attachments,
                thread_id=thread_id,
            )
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["error"]["code"], code)
            self.assertFalse(
                self.application.state.native_service.repository.exists(
                    thread_id
                )
            )

        limited_root = self.root / "limited"
        limited_root.mkdir()
        limited_app = create_app(
            session_root=limited_root,
            attachment_limits=AttachmentLimits(max_file_bytes=4),
        )
        with TestClient(
            limited_app,
            raise_server_exceptions=False,
        ) as client:
            response = client.post(
                "/generate/attachments",
                data={
                    "thread_id": THREAD_B,
                    "user_text": USER_TEXT,
                    "turn_id": TURN_A,
                    "attachment_id": ATTACHMENT_A,
                },
                files=[
                    (
                        "files",
                        ("large.txt", b"12345", "text/plain"),
                    )
                ],
            )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json()["error"]["code"],
            "attachment_too_large",
        )
        self.assertFalse(
            limited_app.state.native_service.repository.exists(THREAD_B)
        )

    def test_mismatched_duplicate_and_invalid_form_claims_are_safe(self):
        mismatch = self.client.post(
            "/generate/attachments",
            data={
                "thread_id": THREAD_A,
                "user_text": USER_TEXT,
                "turn_id": TURN_A,
                "attachment_id": [ATTACHMENT_A, ATTACHMENT_B],
            },
            files=[
                ("files", ("one.txt", b"One.", "text/plain"))
            ],
        )
        duplicate = self._create(
            [
                (
                    ATTACHMENT_A,
                    "one.txt",
                    b"One.",
                    "text/plain",
                ),
                (
                    ATTACHMENT_A,
                    "two.txt",
                    b"Two.",
                    "text/plain",
                ),
            ],
            thread_id=THREAD_B,
        )
        invalid_form = self._create(
            [
                (
                    ATTACHMENT_A,
                    "private.txt",
                    b"private parser material",
                    "text/plain",
                )
            ],
            thread_id="thread:not-hex",
            user_text="   ",
        )

        self.assertEqual(mismatch.status_code, 422)
        self.assertEqual(
            mismatch.json()["error"]["code"],
            "invalid_attachment",
        )
        self.assertEqual(duplicate.status_code, 422)
        self.assertEqual(
            duplicate.json()["error"]["code"],
            "invalid_attachment",
        )
        self.assertEqual(invalid_form.status_code, 422)
        self.assertEqual(
            invalid_form.json()["error"]["code"],
            "invalid_request",
        )
        self.assertNotIn("private parser material", invalid_form.text)
        self.assertFalse(
            self.application.state.native_service.repository.exists(
                THREAD_A
            )
        )
        self.assertFalse(
            self.application.state.native_service.repository.exists(
                THREAD_B
            )
        )

    def test_pdf_and_docx_structural_limits_fail_closed(self):
        pdf_root = self.root / "pdf-limit"
        pdf_root.mkdir()
        pdf_app = create_app(
            session_root=pdf_root,
            attachment_limits=AttachmentLimits(max_pdf_pages=1),
        )
        with TestClient(
            pdf_app,
            raise_server_exceptions=False,
        ) as client:
            response = client.post(
                "/generate/attachments",
                data={
                    "thread_id": THREAD_B,
                    "user_text": USER_TEXT,
                    "turn_id": TURN_A,
                    "attachment_id": ATTACHMENT_A,
                },
                files=[
                    (
                        "files",
                        (
                            "two-pages.pdf",
                            _pdf_bytes("page", page_count=2),
                            "application/pdf",
                        ),
                    )
                ],
            )
        self.assertEqual(response.status_code, 413)
        self.assertFalse(
            pdf_app.state.native_service.repository.exists(THREAD_B)
        )

        docx_root = self.root / "docx-limit"
        docx_root.mkdir()
        docx_app = create_app(
            session_root=docx_root,
            attachment_limits=AttachmentLimits(max_docx_members=1),
        )
        with TestClient(
            docx_app,
            raise_server_exceptions=False,
        ) as client:
            response = client.post(
                "/generate/attachments",
                data={
                    "thread_id": THREAD_B,
                    "user_text": USER_TEXT,
                    "turn_id": TURN_A,
                    "attachment_id": ATTACHMENT_A,
                },
                files=[
                    (
                        "files",
                        (
                            "document.docx",
                            _docx_bytes("text"),
                            (
                                "application/vnd.openxmlformats-officedocument."
                                "wordprocessingml.document"
                            ),
                        ),
                    )
                ],
            )
        self.assertEqual(response.status_code, 413)
        self.assertFalse(
            docx_app.state.native_service.repository.exists(THREAD_B)
        )

    def test_openapi_declares_multipart_and_typed_error_contracts(self):
        document = self.client.get("/openapi.json").json()
        for path in (
            "/generate/attachments",
            "/chat/{thread_id}/attachments",
        ):
            operation = document["paths"][path]["post"]
            content = operation["requestBody"]["content"]
            self.assertIn("multipart/form-data", content)
            for status in ("409", "413", "415", "422", "500"):
                self.assertIn(status, operation["responses"])
                self.assertEqual(
                    operation["responses"][status]["content"][
                        "application/json"
                    ]["schema"]["$ref"],
                    "#/components/schemas/ErrorResponse",
                )
        self.assertIn(
            "200",
            document["paths"]["/generate/attachments"]["post"][
                "responses"
            ],
        )
        self.assertIn(
            "201",
            document["paths"]["/generate/attachments"]["post"][
                "responses"
            ],
        )


class AttachmentIngressServiceTests(unittest.TestCase):
    def test_concurrent_identical_creation_converges_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = NativeSessionRepository(Path(temporary))
            service = NativeApplicationService(repository)
            streams = build_attachment_streams(
                thread_id=THREAD_A,
                turn_id=TURN_A,
                attachments=(
                    UploadedAttachment(
                        attachment_id=ATTACHMENT_A,
                        filename="notes.txt",
                        declared_media_type="text/plain",
                        content=b"Concurrent attachment material.",
                    ),
                ),
            )

            def create():
                return service.create_thread(
                    THREAD_A,
                    USER_TEXT,
                    turn_id=TURN_A,
                    additional_streams=streams,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: create(), range(2)))

            self.assertEqual(
                sorted(item.replayed for item in results),
                [False, True],
            )
            session = repository.load(THREAD_A)
            self.assertEqual(session.revision, 1)
            self.assertEqual(len(session.turns), 1)
            self.assertEqual(
                session.turns[0].additional_stream_ids,
                (streams[0].stream_id,),
            )

    def test_attachment_limits_reject_invalid_environment_values(self):
        with self.assertRaises(InvalidAttachmentError):
            AttachmentLimits.from_environment(
                {"CBRA_ATTACHMENT_MAX_COUNT": "0"}
            )
        with self.assertRaises(InvalidAttachmentError):
            AttachmentLimits(max_file_bytes=True)

    def test_each_composite_resource_limit_is_enforced(self):
        first = UploadedAttachment(
            attachment_id=ATTACHMENT_A,
            filename="first.txt",
            declared_media_type="text/plain",
            content=b"four",
        )
        second = UploadedAttachment(
            attachment_id=ATTACHMENT_B,
            filename="second.txt",
            declared_media_type="text/plain",
            content=b"five!",
        )
        limit_cases = [
            (
                (first, second),
                AttachmentLimits(max_attachments=1),
            ),
            (
                (first, second),
                AttachmentLimits(max_total_upload_bytes=8),
            ),
            (
                (second,),
                AttachmentLimits(max_extracted_characters=4),
            ),
            (
                (first, second),
                AttachmentLimits(
                    max_extracted_characters=10,
                    max_total_extracted_characters=8,
                ),
            ),
            (
                (
                    UploadedAttachment(
                        attachment_id=ATTACHMENT_A,
                        filename="document.docx",
                        declared_media_type=(
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                        content=_docx_bytes("expanded"),
                    ),
                ),
                AttachmentLimits(max_docx_expanded_bytes=1),
            ),
        ]
        for attachments, limits in limit_cases:
            with self.assertRaises(AttachmentTooLargeError):
                build_attachment_streams(
                    thread_id=THREAD_A,
                    turn_id=TURN_A,
                    attachments=attachments,
                    limits=limits,
                )


if __name__ == "__main__":
    unittest.main()

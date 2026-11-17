"""Served-browser contracts for immutable native attachment handoff."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_INDEX = PROJECT_ROOT / "ui" / "index.html"
APP_MODULE = PROJECT_ROOT / "cbra" / "app.py"


def _browser_source():
    return UI_INDEX.read_text(encoding="utf-8")


def _javascript_source(html):
    match = re.search(r"<script>\s*(.*?)\s*</script>", html, re.DOTALL)
    if match is None:
        raise AssertionError("served browser must contain one inline script")
    return match.group(1)


class BrowserAttachmentHandoffTests(unittest.TestCase):
    def test_picker_is_accessible_bounded_and_multiple(self):
        html = _browser_source()

        self.assertIn('label for="attachments"', html)
        self.assertIn('id="attachments"', html)
        self.assertIn('type="file"', html)
        self.assertIn("multiple", html)
        self.assertIn('aria-describedby="attachmentNote"', html)
        for extension in (".txt", ".md", ".docx", ".pdf"):
            self.assertIn(extension, html)

    def test_selected_file_details_use_safe_text_rendering(self):
        script = _javascript_source(_browser_source())

        self.assertIn("name.textContent = attachment.file.name", script)
        self.assertIn("size.textContent = formatBytes", script)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("insertAdjacentHTML", script)

    def test_files_receive_stable_claims_and_freeze_with_pending_turn(self):
        script = _javascript_source(_browser_source())

        self.assertIn('newClaim("attachment:")', script)
        self.assertIn("attachmentId: attachment.attachmentId", script)
        self.assertIn("file: attachment.file", script)
        self.assertIn("Object.freeze(", script)
        self.assertIn("pending.attachments", script)
        self.assertIn("attachment.file === right[index].file", script)

    def test_file_turns_use_fresh_multipart_and_text_turns_stay_json(self):
        script = _javascript_source(_browser_source())

        for route in (
            '"/generate/attachments"',
            "/attachments`",
            '"/generate"',
        ):
            self.assertIn(route, script)
        self.assertIn("const form = new FormData()", script)
        self.assertRegex(
            script,
            r'form\.append\(\s*"attachment_id"',
        )
        self.assertRegex(script, r'form\.append\(\s*"files"')
        self.assertIn('"Content-Type": "application/json"', script)
        self.assertNotIn('"Content-Type": "multipart/form-data"', script)

    def test_interrupted_turn_is_reconciled_before_material_changes(self):
        script = _javascript_source(_browser_source())

        self.assertIn("needsReconciliation", script)
        self.assertIn("composerMatchesPending", script)
        self.assertIn('addEventListener("input"', script)
        self.assertIn(
            "Checking whether the earlier interrupted turn persisted",
            script,
        )
        self.assertIn("reconciliation.recoveredPending", script)
        self.assertIn("Resolve prior turn", script)
        self.assertIn("Recovered persisted turn", script)

    def test_attachment_references_are_released_only_at_safe_boundaries(self):
        script = _javascript_source(_browser_source())

        self.assertIn("clearAttachmentSelection()", script)
        self.assertIn("if (liveMaterialWasPending)", script)
        self.assertIn("Resolve the earlier interrupted turn", script)
        self.assertIn("prevent cross-thread use", script)
        for forbidden in (
            "sessionStorage",
            "indexedDB",
            "FileReader",
            "readAsDataURL",
            "arrayBuffer()",
        ):
            self.assertNotIn(forbidden, script)

    def test_typed_attachment_errors_remain_public_and_parser_safe(self):
        script = _javascript_source(_browser_source())

        for code in (
            "attachment_too_large",
            "unsupported_attachment",
            "invalid_attachment",
        ):
            self.assertIn(code, script)
        self.assertNotIn("traceback", script.lower())
        self.assertNotIn("parser error", script.lower())

    def test_application_version_names_browser_attachment_pass(self):
        source = APP_MODULE.read_text(encoding="utf-8")

        self.assertIn(
            'APP_VERSION = "0.9.0-temporal-markdown"',
            source,
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_inline_javascript_passes_node_syntax_validation(self):
        result = subprocess.run(
            ["node", "--check"],
            input=_javascript_source(_browser_source()),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

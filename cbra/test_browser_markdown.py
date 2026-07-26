"""Safe browser Markdown rendering contracts."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cbra.app import create_app


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_INDEX = PROJECT_ROOT / "ui" / "index.html"
MARKDOWN_RENDERER = PROJECT_ROOT / "ui" / "markdown.js"


class BrowserMarkdownRenderingTests(unittest.TestCase):
    def test_assistant_messages_use_renderer_with_plain_text_fallback(self):
        html = UI_INDEX.read_text(encoding="utf-8")

        self.assertIn('<script src="/ui/markdown.js"></script>', html)
        self.assertIn("window.CBRAMarkdown.render(content, text)", html)
        self.assertIn("content.textContent = text", html)
        self.assertIn('content.className = "message-content"', html)

    def test_renderer_never_interprets_html(self):
        source = MARKDOWN_RENDERER.read_text(encoding="utf-8")

        self.assertNotIn("innerHTML", source)
        self.assertNotIn("insertAdjacentHTML", source)
        self.assertNotIn("DOMParser", source)
        self.assertIn("createTextNode", source)
        self.assertIn("textContent", source)

    def test_renderer_asset_is_served_as_javascript(self):
        with tempfile.TemporaryDirectory() as root:
            application = create_app(
                session_root=Path(root),
                corpus_root=PROJECT_ROOT / "corpus",
            )
            with TestClient(application) as client:
                response = client.get("/ui/markdown.js")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["content-type"].startswith(
                "application/javascript"
            )
        )
        self.assertEqual(
            response.text,
            MARKDOWN_RENDERER.read_text(encoding="utf-8"),
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_markdown_structure_parses_without_executing_html(self):
        source = (
            "const renderer = require(process.argv[1]);"
            "const result = renderer.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(result));"
        )
        markdown = (
            "#### Final check\n"
            "- **Access:** keep <script>alert(1)</script> visible\n"
            "- Use `relative time`"
        )
        result = subprocess.run(
            [
                "node",
                "-e",
                source,
                str(MARKDOWN_RENDERER),
                markdown,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(
            [block["type"] for block in parsed],
            ["heading", "unordered_list"],
        )
        self.assertEqual(parsed[0]["level"], 4)
        self.assertEqual(
            parsed[1]["items"][0],
            [
                {"type": "strong", "text": "Access:"},
                {
                    "type": "text",
                    "text": (
                        " keep <script>alert(1)</script> visible"
                    ),
                },
            ],
        )
        self.assertEqual(
            parsed[1]["items"][1],
            [
                {"type": "text", "text": "Use "},
                {"type": "code", "text": "relative time"},
            ],
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_markdown_javascript_passes_syntax_validation(self):
        result = subprocess.run(
            ["node", "--check", str(MARKDOWN_RENDERER)],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_renderer_builds_expected_dom_without_html_elements(self):
        source = """
const renderer = require(process.argv[1]);
class Element {
  constructor(tag, ownerDocument) {
    this.tag = tag;
    this.ownerDocument = ownerDocument;
    this.children = [];
  }
  appendChild(child) {
    this.children.push(child);
  }
  replaceChildren(...children) {
    this.children = children;
  }
  set textContent(value) {
    this.children = [{ tag: "#text", text: String(value) }];
  }
}
const documentObject = {
  createElement(tag) {
    return new Element(tag, this);
  },
  createTextNode(text) {
    return { tag: "#text", text: String(text) };
  }
};
const container = new Element("div", documentObject);
renderer.render(container, process.argv[2]);
process.stdout.write(JSON.stringify(container));
"""
        markdown = (
            "#### Final check\n"
            "- **Access:** keep <script>alert(1)</script> visible\n"
            "- Use `relative time`"
        )
        result = subprocess.run(
            [
                "node",
                "-e",
                source,
                str(MARKDOWN_RENDERER),
                markdown,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = json.loads(result.stdout)
        self.assertEqual(
            [child["tag"] for child in rendered["children"]],
            ["h4", "ul"],
        )
        first_item = rendered["children"][1]["children"][0]
        self.assertEqual(first_item["children"][0]["tag"], "strong")
        self.assertNotIn(
            "script",
            {
                node.get("tag")
                for node in first_item["children"]
            },
        )
        self.assertIn(
            "<script>alert(1)</script>",
            "".join(
                node.get("text", "")
                for node in first_item["children"]
                if node.get("tag") == "#text"
            ),
        )


if __name__ == "__main__":
    unittest.main()

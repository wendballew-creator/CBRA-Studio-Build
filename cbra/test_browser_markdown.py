"""Safe browser Markdown rendering contracts."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cbra.app import create_app
from cbra.tests_support import write_legacy_corpus


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
            root_path = Path(root)
            application = create_app(
                session_root=root_path / "sessions",
                corpus_root=write_legacy_corpus(root_path / "corpus"),
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
    def test_ordered_items_continue_across_indented_supporting_lists(self):
        source = (
            "const renderer = require(process.argv[1]);"
            "const result = renderer.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(result));"
        )
        markdown = (
            "1. **Room layout and accessible path — 2 people**\n"
            "\n"
            "   - Clear the main route.\n"
            "   - Position twenty chairs.\n"
            "\n"
            "1. **Welcome table and water — 1 person**\n"
            "\n"
            "   - Keep the entrance route clear.\n"
            "\n"
            "1. **Signs and final supply check — 1 person**\n"
            "\n"
            "   - Place directional signs."
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
        ordered = [
            block for block in parsed
            if block["type"] == "ordered_list"
        ]
        self.assertEqual(
            [block["start"] for block in ordered],
            [1, 2, 3],
        )
        self.assertEqual(
            [block["items"][0][0]["text"] for block in ordered],
            [
                "Room layout and accessible path — 2 people",
                "Welcome table and water — 1 person",
                "Signs and final supply check — 1 person",
            ],
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_paragraph_resets_ordered_list_numbering(self):
        source = (
            "const renderer = require(process.argv[1]);"
            "const result = renderer.parse(process.argv[2]);"
            "process.stdout.write(JSON.stringify(result));"
        )
        markdown = (
            "1. First sequence\n"
            "\n"
            "A separate paragraph.\n"
            "\n"
            "1. New sequence"
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
        ordered = [
            block for block in parsed
            if block["type"] == "ordered_list"
        ]
        self.assertEqual(
            [block["start"] for block in ordered],
            [1, 1],
        )

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

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_renderer_sets_continuation_start_on_ordered_lists(self):
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
            "1. **First assignment**\n"
            "\n"
            "   - Supporting action\n"
            "\n"
            "1. **Second assignment**\n"
            "\n"
            "   - Supporting action\n"
            "\n"
            "1. **Third assignment**"
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
        ordered = [
            child for child in rendered["children"]
            if child["tag"] == "ol"
        ]
        self.assertNotIn("start", ordered[0])
        self.assertEqual(ordered[1]["start"], 2)
        self.assertEqual(ordered[2]["start"], 3)


if __name__ == "__main__":
    unittest.main()

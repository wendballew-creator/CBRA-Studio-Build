(function (root, factory) {
  "use strict";

  const renderer = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = renderer;
  } else {
    root.CBRAMarkdown = renderer;
  }
})(
  typeof globalThis === "object" ? globalThis : this,
  function () {
    "use strict";

    function textToken(value) {
      return { type: "text", text: value };
    }

    function nextInline(text, start) {
      const candidates = [
        { marker: "**", type: "strong" },
        { marker: "__", type: "strong" },
        { marker: "`", type: "code" },
        { marker: "*", type: "emphasis" },
        { marker: "_", type: "emphasis" }
      ];
      let selected = null;
      for (const candidate of candidates) {
        const open = text.indexOf(candidate.marker, start);
        if (open < 0) {
          continue;
        }
        const contentStart = open + candidate.marker.length;
        const close = text.indexOf(candidate.marker, contentStart);
        if (close <= contentStart) {
          continue;
        }
        if (
          selected === null ||
          open < selected.open ||
          (
            open === selected.open &&
            candidate.marker.length > selected.marker.length
          )
        ) {
          selected = {
            open,
            close,
            marker: candidate.marker,
            type: candidate.type
          };
        }
      }
      return selected;
    }

    function parseInline(value) {
      const text = String(value == null ? "" : value);
      const tokens = [];
      let position = 0;
      while (position < text.length) {
        const match = nextInline(text, position);
        if (match === null) {
          tokens.push(textToken(text.slice(position)));
          break;
        }
        if (match.open > position) {
          tokens.push(textToken(text.slice(position, match.open)));
        }
        tokens.push({
          type: match.type,
          text: text.slice(
            match.open + match.marker.length,
            match.close
          )
        });
        position = match.close + match.marker.length;
      }
      return tokens.length ? tokens : [textToken("")];
    }

    function parse(value) {
      const source = String(value == null ? "" : value).replace(
        /\r\n?/g,
        "\n"
      );
      const lines = source.split("\n");
      const blocks = [];
      let paragraph = [];
      let list = null;
      let code = null;

      function flushParagraph() {
        if (!paragraph.length) {
          return;
        }
        blocks.push({
          type: "paragraph",
          inlines: parseInline(paragraph.join(" "))
        });
        paragraph = [];
      }

      function flushList() {
        if (list === null) {
          return;
        }
        blocks.push({
          type: list.type,
          items: list.items.map(parseInline)
        });
        list = null;
      }

      function flushCode() {
        if (code === null) {
          return;
        }
        blocks.push({
          type: "code_block",
          text: code.lines.join("\n")
        });
        code = null;
      }

      for (const line of lines) {
        if (code !== null) {
          if (/^\s*```/.test(line)) {
            flushCode();
          } else {
            code.lines.push(line);
          }
          continue;
        }
        if (/^\s*```/.test(line)) {
          flushParagraph();
          flushList();
          code = { lines: [] };
          continue;
        }
        if (!line.trim()) {
          flushParagraph();
          flushList();
          continue;
        }

        const heading = /^(#{1,6})\s+(.+?)\s*$/.exec(line);
        if (heading) {
          flushParagraph();
          flushList();
          blocks.push({
            type: "heading",
            level: heading[1].length,
            inlines: parseInline(heading[2])
          });
          continue;
        }

        const unordered = /^\s*[-+*]\s+(.+)$/.exec(line);
        const ordered = /^\s*\d+[.)]\s+(.+)$/.exec(line);
        const item = unordered || ordered;
        if (item) {
          flushParagraph();
          const type = unordered ? "unordered_list" : "ordered_list";
          if (list !== null && list.type !== type) {
            flushList();
          }
          if (list === null) {
            list = { type, items: [] };
          }
          list.items.push(item[1]);
          continue;
        }

        if (list !== null && list.items.length) {
          const finalIndex = list.items.length - 1;
          list.items[finalIndex] += " " + line.trim();
          continue;
        }
        paragraph.push(line.trim());
      }

      flushCode();
      flushParagraph();
      flushList();
      return blocks;
    }

    function appendInlines(parent, inlines, documentObject) {
      for (const inline of inlines) {
        if (inline.type === "text") {
          parent.appendChild(documentObject.createTextNode(inline.text));
          continue;
        }
        const tag = inline.type === "strong"
          ? "strong"
          : inline.type === "emphasis"
            ? "em"
            : "code";
        const element = documentObject.createElement(tag);
        element.textContent = inline.text;
        parent.appendChild(element);
      }
    }

    function render(container, value) {
      if (
        !container ||
        !container.ownerDocument ||
        typeof container.replaceChildren !== "function"
      ) {
        throw new TypeError("A DOM container is required.");
      }
      const documentObject = container.ownerDocument;
      container.replaceChildren();
      for (const block of parse(value)) {
        let element;
        if (block.type === "heading") {
          element = documentObject.createElement("h" + block.level);
          appendInlines(element, block.inlines, documentObject);
        } else if (
          block.type === "unordered_list" ||
          block.type === "ordered_list"
        ) {
          element = documentObject.createElement(
            block.type === "unordered_list" ? "ul" : "ol"
          );
          for (const item of block.items) {
            const listItem = documentObject.createElement("li");
            appendInlines(listItem, item, documentObject);
            element.appendChild(listItem);
          }
        } else if (block.type === "code_block") {
          element = documentObject.createElement("pre");
          const codeElement = documentObject.createElement("code");
          codeElement.textContent = block.text;
          element.appendChild(codeElement);
        } else {
          element = documentObject.createElement("p");
          appendInlines(element, block.inlines, documentObject);
        }
        container.appendChild(element);
      }
    }

    return Object.freeze({
      parse,
      render
    });
  }
);

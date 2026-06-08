// Minimal, dependency-free Markdown → HTML renderer.
//
// Runs at build time inside build-library.mjs, so the web app never ships a
// markdown library to the client. It covers what research reports actually use:
// headings, lists, blockquotes, code fences/spans, links, emphasis, rules, and
// paragraphs. Intentionally small — extend here if reports start needing more
// (tables, footnotes) rather than reaching for a heavy dependency.

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderInline(text) {
  // Split on inline code spans so their contents are never treated as markup.
  const parts = text.split(/(`[^`]+`)/g);
  return parts
    .map((part) => {
      if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
        return "<code>" + escapeHtml(part.slice(1, -1)) + "</code>";
      }
      let s = escapeHtml(part);
      // [label](url) — url is HTML-escaped already, which is safe for the attr.
      s = s.replace(
        /\[([^\]]+)\]\(([^)\s]+)\)/g,
        (_m, label, url) =>
          `<a href="${url}" target="_blank" rel="noreferrer">${label}</a>`
      );
      s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
      s = s.replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, "$1<em>$2</em>");
      s = s.replace(/(^|[^_])_([^_\s][^_]*?)_/g, "$1<em>$2</em>");
      return s;
    })
    .join("");
}

export function renderMarkdown(md) {
  const lines = (md || "").replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let i = 0;

  const isBlank = (l) => /^\s*$/.test(l);
  const startsBlock = (l) =>
    /^(#{1,6})\s/.test(l) ||
    /^```/.test(l) ||
    /^>\s?/.test(l) ||
    /^\s*[-*+]\s+/.test(l) ||
    /^\s*\d+\.\s+/.test(l) ||
    /^\s*([-*_])\1{2,}\s*$/.test(l);

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (/^```/.test(line)) {
      i++;
      const code = [];
      while (i < lines.length && !/^```/.test(lines[i])) {
        code.push(lines[i]);
        i++;
      }
      i++; // consume closing fence
      out.push("<pre><code>" + escapeHtml(code.join("\n")) + "</code></pre>");
      continue;
    }

    // Heading
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      out.push(`<h${level}>${renderInline(heading[2].trim())}</h${level}>`);
      i++;
      continue;
    }

    // Horizontal rule
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      out.push("<hr/>");
      i++;
      continue;
    }

    // Blockquote (recurse on the unwrapped content)
    if (/^>\s?/.test(line)) {
      const quoted = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quoted.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      out.push("<blockquote>" + renderMarkdown(quoted.join("\n")) + "</blockquote>");
      continue;
    }

    // Unordered list
    if (/^\s*[-*+]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*+]\s+/, ""));
        i++;
      }
      out.push("<ul>" + items.map((it) => `<li>${renderInline(it)}</li>`).join("") + "</ul>");
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      out.push("<ol>" + items.map((it) => `<li>${renderInline(it)}</li>`).join("") + "</ol>");
      continue;
    }

    // Blank line
    if (isBlank(line)) {
      i++;
      continue;
    }

    // Paragraph — gather consecutive non-blank, non-block lines
    const para = [];
    while (i < lines.length && !isBlank(lines[i]) && !startsBlock(lines[i])) {
      para.push(lines[i]);
      i++;
    }
    out.push("<p>" + renderInline(para.join(" ")) + "</p>");
  }

  return out.join("\n");
}

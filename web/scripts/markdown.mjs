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
  // Protect inline code and links by stashing their final HTML behind
  // placeholders, so emphasis processing can't reach inside them — e.g. the
  // underscores in a link's target="_blank" must not be treated as italics.
  // The fence is a NUL char, which never appears in source text, so the restore
  // step can't accidentally match real digits in the prose.
  const stash = [];
  const keep = (html) => "\x00" + (stash.push(html) - 1) + "\x00";

  let s = text.replace(/`([^`]+)`/g, (_m, code) => keep("<code>" + escapeHtml(code) + "</code>"));
  // Images BEFORE links — `![alt](url)` overlaps the link pattern `[alt](url)`,
  // so the image rule must claim the syntax first. Inline (within prose) images
  // render as a bare <img> to stay valid inside <p>; standalone image lines are
  // promoted to a <figure> block by renderMarkdown below.
  s = s.replace(
    /!\[([^\]]*)\]\(([^)\s]+)\)/g,
    (_m, alt, url) =>
      keep('<img loading="lazy" src="' + escapeHtml(url) + '" alt="' + escapeHtml(alt) + '"/>')
  );
  s = s.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    (_m, label, url) =>
      keep(
        '<a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">' +
          escapeHtml(label) +
          "</a>"
      )
  );

  // Escape the remaining text, then apply emphasis. Placeholders hold no * or _.
  s = escapeHtml(s);
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, "$1<em>$2</em>");
  s = s.replace(/(^|[^_])_([^_\s][^_]*?)_/g, "$1<em>$2</em>");

  // Restore the protected code/link HTML.
  return s.replace(/\x00(\d+)\x00/g, (_m, i) => stash[Number(i)]);
}

export function renderMarkdown(md) {
  const lines = (md || "").replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let i = 0;

  const isBlank = (l) => /^\s*$/.test(l);
  const IMAGE_LINE = /^\s*!\[([^\]]*)\]\(([^)\s]+)\)\s*$/;
  const startsBlock = (l) =>
    /^(#{1,6})\s/.test(l) ||
    /^```/.test(l) ||
    /^>\s?/.test(l) ||
    /^\s*[-*+]\s+/.test(l) ||
    /^\s*\d+\.\s+/.test(l) ||
    /^\s*([-*_])\1{2,}\s*$/.test(l) ||
    IMAGE_LINE.test(l);

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

    // Standalone image line → figure block (caption from alt text)
    const img = line.match(IMAGE_LINE);
    if (img) {
      const alt = img[1].trim();
      const url = img[2];
      out.push(
        '<figure class="figure">' +
          `<img loading="lazy" src="${escapeHtml(url)}" alt="${escapeHtml(alt)}"/>` +
          (alt ? `<figcaption>${escapeHtml(alt)}</figcaption>` : "") +
          "</figure>"
      );
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

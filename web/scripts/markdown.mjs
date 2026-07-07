// Minimal, dependency-free Markdown → HTML renderer.
//
// Runs at build time inside build-library.mjs, so the web app never ships a
// markdown library to the client. It covers what research reports actually use:
// headings, lists, tables, blockquotes, code fences/spans, links, emphasis,
// rules, and paragraphs. Intentionally small — extend here if reports start
// needing more (footnotes) rather than reaching for a heavy dependency.

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Reports reference their sibling artifacts with bare relative paths
// ("chart.svg"), but the page serves them from /library/<slug>/. Rewrite
// relative srcs; absolute URLs and site-absolute paths pass through.
function resolveImageSrc(url, assetBase) {
  if (!assetBase) return url;
  if (/^(https?:)?\/\//.test(url) || url.startsWith("/") || url.startsWith("data:")) return url;
  return assetBase.replace(/\/$/, "") + "/" + url.replace(/^\.\//, "");
}

function renderInline(text, assetBase) {
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
      keep(
        '<img loading="lazy" src="' +
          escapeHtml(resolveImageSrc(url, assetBase)) +
          '" alt="' + escapeHtml(alt) + '"/>'
      )
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

// A table row is `| cell | cell |`; the separator row under the header is
// `| --- | :---: |` etc.
const TABLE_ROW = /^\s*\|(.+)\|\s*$/;
const TABLE_SEP = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/;

function slugifyHeading(text) {
  return text
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/&[a-z]+;/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 64);
}

export function renderMarkdown(md, assetBase = "") {
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
    IMAGE_LINE.test(l) ||
    (TABLE_ROW.test(l) && i + 1 < lines.length && TABLE_SEP.test(lines[i + 1] || ""));

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

    // Heading (h2/h3 get ids so the report page can build a mini-TOC)
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const inner = renderInline(heading[2].trim(), assetBase);
      const id = level === 2 || level === 3 ? slugifyHeading(heading[2].trim()) : "";
      out.push(`<h${level}${id ? ` id="${id}"` : ""}>${inner}</h${level}>`);
      i++;
      continue;
    }

    // Table (header row + separator row + body rows)
    if (TABLE_ROW.test(line) && TABLE_SEP.test(lines[i + 1] || "")) {
      const splitRow = (l) =>
        l
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((c) => c.trim());
      const headers = splitRow(line);
      i += 2; // consume header + separator
      const rows = [];
      while (i < lines.length && TABLE_ROW.test(lines[i])) {
        rows.push(splitRow(lines[i]));
        i++;
      }
      const thead =
        "<thead><tr>" +
        headers.map((h) => `<th>${renderInline(h, assetBase)}</th>`).join("") +
        "</tr></thead>";
      const tbody =
        "<tbody>" +
        rows
          .map(
            (r) =>
              "<tr>" +
              headers
                .map((_h, ci) => `<td>${renderInline(r[ci] ?? "", assetBase)}</td>`)
                .join("") +
              "</tr>"
          )
          .join("") +
        "</tbody>";
      out.push(`<div class="tableWrap"><table>${thead}${tbody}</table></div>`);
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
      const url = resolveImageSrc(img[2], assetBase);
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
      out.push("<blockquote>" + renderMarkdown(quoted.join("\n"), assetBase) + "</blockquote>");
      continue;
    }

    // Unordered list
    if (/^\s*[-*+]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*+]\s+/, ""));
        i++;
      }
      out.push("<ul>" + items.map((it) => `<li>${renderInline(it, assetBase)}</li>`).join("") + "</ul>");
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      out.push("<ol>" + items.map((it) => `<li>${renderInline(it, assetBase)}</li>`).join("") + "</ol>");
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
    out.push("<p>" + renderInline(para.join(" "), assetBase) + "</p>");
  }

  return out.join("\n");
}

"""Full-source fetching tools.

Search results are only snippets; these tools let the search agent read the
complete text of the sources it triages as most promising, so findings can
quote real passages instead of paraphrasing blurbs.

- tavily_extract: primary path. Uses the Tavily extract API (same key as
  search), which handles JS-rendered pages and PDFs.
- fetch_url: aiohttp fallback for pages Tavily can't extract. Plain HTML
  only — PDFs are redirected to tavily_extract.
"""

from __future__ import annotations

import json
import os
import re
from html.parser import HTMLParser
from typing import Any

from claude_agent_sdk import tool

from research_agent.tools.limits import exhausted_message, get_budget

# Cap per-source text so a handful of extractions can't blow out the agent's
# context window. Truncation is flagged so the agent knows to quote from what
# it has rather than assume it saw the whole document.
MAX_CHARS_PER_SOURCE = 35_000


class _TextExtractor(HTMLParser):
    """Minimal readability: drop script/style/nav/etc., keep visible text."""

    _SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form"}
    _BLOCK = {"p", "div", "section", "article", "li", "br", "tr",
              "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


def _clip(text: str) -> tuple[str, bool]:
    if len(text) > MAX_CHARS_PER_SOURCE:
        return text[:MAX_CHARS_PER_SOURCE], True
    return text, False


@tool(
    "tavily_extract",
    "Extract the full text content of one or more web pages (including PDFs and "
    "JS-rendered pages). Use this to deep-read the most promising search results "
    "so findings can quote actual passages. Pass up to 5 URLs at a time.",
    {"urls": list, "extract_depth": str},
)
async def tavily_extract(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch full page text via the Tavily extract API."""
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return {
            "content": [
                {"type": "text", "text": "ERROR: TAVILY_API_KEY environment variable is not set."}
            ]
        }

    urls = args.get("urls") or []
    if isinstance(urls, str):
        urls = [urls]
    urls = [u for u in urls if isinstance(u, str) and u.strip()][:5]
    if not urls:
        return {"content": [{"type": "text", "text": "ERROR: no URLs provided."}]}

    budget = get_budget()
    if not budget.try_extract():
        return {"content": [{"type": "text", "text": exhausted_message("extract", budget)}]}

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=api_key)
        response = await client.extract(
            urls=urls,
            extract_depth=args.get("extract_depth") or "advanced",
        )

        results = []
        for item in response.get("results", []):
            text, truncated = _clip(item.get("raw_content") or "")
            results.append(
                {
                    "url": item.get("url", ""),
                    "raw_content": text,
                    "truncated": truncated,
                    "char_count": len(text),
                }
            )
        failed = [
            {"url": item.get("url", ""), "error": item.get("error", "extraction failed")}
            for item in response.get("failed_results", [])
        ]

        output = {"results": results, "failed": failed, "budget": budget.summary()}
        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"ERROR: Tavily extract failed: {e}"}]}


@tool(
    "fetch_url",
    "Fetch a single web page directly and return its readable text. Fallback for "
    "pages tavily_extract could not handle. HTML only — for PDFs use tavily_extract.",
    {"url": str},
)
async def fetch_url(args: dict[str, Any]) -> dict[str, Any]:
    """Direct aiohttp fetch with a minimal readable-text extraction."""
    url = (args.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"content": [{"type": "text", "text": f"ERROR: invalid URL: {url!r}"}]}

    budget = get_budget()
    if not budget.try_extract():
        return {"content": [{"type": "text", "text": exhausted_message("extract", budget)}]}

    try:
        import aiohttp

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            )
        }
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "pdf" in content_type:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"ERROR: {url} is a PDF — use tavily_extract for this URL instead.",
                            }
                        ]
                    }
                if resp.status >= 400:
                    return {
                        "content": [
                            {"type": "text", "text": f"ERROR: HTTP {resp.status} fetching {url}"}
                        ]
                    }
                body = await resp.text(errors="replace")

        parser = _TextExtractor()
        parser.feed(body)
        text, truncated = _clip(parser.text())
        if not text:
            return {
                "content": [
                    {"type": "text", "text": f"ERROR: no readable text extracted from {url}"}
                ]
            }

        output = {
            "url": url,
            "raw_content": text,
            "truncated": truncated,
            "char_count": len(text),
            "budget": budget.summary(),
        }
        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"ERROR: fetch failed for {url}: {e}"}]}

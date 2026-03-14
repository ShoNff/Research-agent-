"""Source reliability evaluation tool."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from claude_agent_sdk import tool

# Domain reputation database
ESTABLISHED_DOMAINS = {
    "gov", "edu", "mil",
    "nature.com", "science.org", "ieee.org", "acm.org",
    "who.int", "nih.gov", "cdc.gov", "arxiv.org",
    "sciencedirect.com", "springer.com", "wiley.com",
}

REPUTABLE_DOMAINS = {
    "nytimes.com", "bbc.com", "bbc.co.uk", "reuters.com",
    "arstechnica.com", "theverge.com", "wired.com",
    "docs.python.org", "developer.mozilla.org", "kubernetes.io",
    "docs.microsoft.com", "learn.microsoft.com", "cloud.google.com",
    "aws.amazon.com", "docs.aws.amazon.com",
    "github.com", "stackoverflow.com",
    "washingtonpost.com", "economist.com", "ft.com",
    "techcrunch.com", "theregister.com",
}

OPINION_INDICATORS = {
    "blog", "medium.com", "substack.com", "dev.to",
    "reddit.com", "news.ycombinator.com", "twitter.com", "x.com",
    "quora.com", "wordpress.com", "tumblr.com",
}


def _extract_base_domain(domain: str) -> str:
    """Extract the base domain (e.g., 'bbc.co.uk' from 'www.bbc.co.uk')."""
    parts = domain.lower().split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "ac"):
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


@tool(
    "evaluate_source",
    "Evaluate the reliability tier of a web source based on domain reputation, content type, and metadata. Returns a reliability tier (established, reputable, emerging, opinion, unknown) with confidence score and reasoning.",
    {"url": str, "domain": str, "title": str, "snippet": str},
)
async def evaluate_source(args: dict[str, Any]) -> dict[str, Any]:
    """Evaluate source reliability using domain heuristics."""
    domain = args.get("domain", "").lower().strip()
    if not domain:
        try:
            domain = urlparse(args.get("url", "")).netloc.lower()
        except Exception:
            domain = ""

    # Remove www prefix
    if domain.startswith("www."):
        domain = domain[4:]

    base_domain = _extract_base_domain(domain)
    tld = domain.split(".")[-1] if domain else ""

    tier = "unknown"
    confidence = 0.5
    reasoning_parts = []

    # Check TLD
    if tld in ("gov", "edu", "mil"):
        tier = "established"
        confidence = 0.9
        reasoning_parts.append(f"TLD .{tld} indicates institutional source")
    # Check established domains
    elif base_domain in ESTABLISHED_DOMAINS or domain in ESTABLISHED_DOMAINS:
        tier = "established"
        confidence = 0.85
        reasoning_parts.append(f"Domain {domain} is a known established source")
    # Check reputable domains
    elif base_domain in REPUTABLE_DOMAINS or domain in REPUTABLE_DOMAINS:
        tier = "reputable"
        confidence = 0.8
        reasoning_parts.append(f"Domain {domain} is a known reputable source")
    # Check opinion indicators
    elif any(indicator in domain for indicator in OPINION_INDICATORS):
        tier = "opinion"
        confidence = 0.75
        reasoning_parts.append("Domain pattern suggests opinion/user-generated content")
    # Fallback: check for corporate/org domains
    elif tld in ("org", "com"):
        tier = "emerging"
        confidence = 0.4
        reasoning_parts.append(f"Generic .{tld} domain — classified as emerging by default")

    # Title-based adjustments
    title_lower = (args.get("title", "") or "").lower()
    opinion_keywords = ["opinion", "editorial", "my thoughts", "i think", "rant", "hot take"]
    research_keywords = ["study", "research", "paper", "journal", "proceedings", "survey"]

    if any(kw in title_lower for kw in opinion_keywords):
        if tier not in ("established",):
            tier = "opinion"
            confidence = max(confidence, 0.7)
            reasoning_parts.append("Title language suggests opinion piece")

    if any(kw in title_lower for kw in research_keywords):
        if tier in ("unknown", "emerging"):
            tier = "emerging"
            confidence = max(confidence, 0.6)
            reasoning_parts.append("Title suggests research/academic content")

    result = {
        "url": args.get("url", ""),
        "domain": domain,
        "title": args.get("title", ""),
        "reliability_tier": tier,
        "confidence_score": round(confidence, 2),
        "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "No strong signals detected",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

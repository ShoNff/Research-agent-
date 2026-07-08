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
    # Academic / primary research
    "semanticscholar.org", "ssrn.com", "nber.org", "jstor.org",
    "pubmed.ncbi.nlm.nih.gov", "plos.org", "pnas.org", "cell.com",
    "thelancet.com", "nejm.org", "bmj.com",
    # International institutions
    "oecd.org", "imf.org", "worldbank.org", "un.org", "europa.eu",
    "ecb.europa.eu", "bis.org", "weforum.org",
    # Standards bodies
    "w3.org", "ietf.org", "iso.org", "nist.gov",
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
    # Quality business/finance press
    "wsj.com", "bloomberg.com", "cnbc.com", "morningstar.com",
    "apnews.com", "axios.com", "theinformation.com",
    # Analyst / advisory research
    "gartner.com", "forrester.com", "mckinsey.com", "bcg.com",
    "bain.com", "deloitte.com", "pwc.com", "kpmg.com", "ey.com",
    "statista.com", "pewresearch.org",
    # Official vendor documentation and engineering blogs
    "anthropic.com", "openai.com", "deepmind.google", "ai.meta.com",
    "azure.microsoft.com", "microsoft.com", "google.com", "apple.com",
    "nvidia.com", "huggingface.co", "databricks.com", "snowflake.com",
    "docker.com", "hashicorp.com", "redhat.com", "vmware.com",
}

OPINION_INDICATORS = {
    "blog", "medium.com", "substack.com", "dev.to",
    "reddit.com", "news.ycombinator.com", "twitter.com", "x.com",
    "quora.com", "wordpress.com", "tumblr.com",
    "linkedin.com", "facebook.com", "youtube.com", "tiktok.com",
}

# URL path patterns that shift the assessment regardless of domain lists.
ACADEMIC_PATH_PATTERNS = ("/doi/", "/abs/", "/paper/", "/pubs/", "/publication/")
OPINION_PATH_PATTERNS = ("/blog/", "/blogs/", "/opinion/", "/opinions/", "/commentary/", "/column/")

# Below this confidence the heuristic is guessing; the reading agent (which
# has the full text) should assign the final tier itself.
NEEDS_JUDGMENT_THRESHOLD = 0.6


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
    "Evaluate the reliability tier of a web source based on domain reputation, content type, and metadata. Returns a reliability tier (established, reputable, emerging, opinion, unknown) with confidence score and reasoning. If the result includes needs_judgment: true, the caller should assign the final tier itself based on the source's actual content.",
    {"url": str, "domain": str, "title": str, "snippet": str},
)
async def evaluate_source(args: dict[str, Any]) -> dict[str, Any]:
    """Evaluate source reliability using domain heuristics."""
    url = args.get("url", "")
    domain = args.get("domain", "").lower().strip()
    path = ""
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        if not domain:
            domain = parsed.netloc.lower()
    except Exception:
        pass

    # Remove www prefix
    if domain.startswith("www."):
        domain = domain[4:]

    base_domain = _extract_base_domain(domain)
    tld = domain.split(".")[-1] if domain else ""

    tier = "unknown"
    confidence = 0.5
    reasoning_parts = []

    institutional = tld in ("gov", "edu", "mil") or domain.endswith(
        (".gov", ".edu", ".mil", ".ac.uk", ".gov.uk")
    )

    # Check TLD
    if institutional:
        tier = "established"
        confidence = 0.9
        reasoning_parts.append("Institutional domain (.gov/.edu/.mil class)")
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

    # URL-path adjustments
    if any(p in path for p in ACADEMIC_PATH_PATTERNS) or (
        path.endswith(".pdf") and tier in ("established", "reputable")
    ):
        if tier in ("unknown", "emerging"):
            tier = "reputable"
        confidence = max(confidence, 0.7)
        reasoning_parts.append("URL pattern suggests academic/primary document")
    elif any(p in path for p in OPINION_PATH_PATTERNS):
        if tier not in ("established",):
            tier = "opinion" if tier in ("unknown", "emerging") else tier
            reasoning_parts.append("URL path suggests blog/opinion content")

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

    needs_judgment = confidence < NEEDS_JUDGMENT_THRESHOLD or tier == "unknown"
    if needs_judgment:
        reasoning_parts.append(
            "Weak heuristic signal — assess the tier yourself from the source's "
            "actual content (authorship, citations, evidence quality, recency)"
        )

    result = {
        "url": url,
        "domain": domain,
        "title": args.get("title", ""),
        "reliability_tier": tier,
        "confidence_score": round(confidence, 2),
        "needs_judgment": needs_judgment,
        "reasoning": "; ".join(reasoning_parts) if reasoning_parts else "No strong signals detected",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

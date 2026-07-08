"""Edition email rendering + delivery via the Resend API.

Deliberately NOT an agent tool: once a validated edition exists, delivery is
deterministic code. Rendering uses the Jinja2 newspaper template; sending is
one HTTPS POST to Resend (RESEND_API_KEY env var).
"""

from __future__ import annotations

import os
from datetime import date as date_type
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from research_agent.models.edition import Edition

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

TIER_DOTS = {
    "established": "🟢",
    "reputable": "🔵",
    "emerging": "🟡",
    "opinion": "🟠",
    "unknown": "⚪",
}


def _tier_dot(tier: str) -> str:
    return TIER_DOTS.get((tier or "unknown").lower(), "⚪")


def render_edition_html(edition: Edition, library_base: str = "") -> str:
    """Render the edition to inline-styled HTML for email clients."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["tier_dot"] = _tier_dot
    template = env.get_template("newspaper.html")

    try:
        date_human = date_type.fromisoformat(edition.date).strftime("%A, %B %-d, %Y")
    except ValueError:
        date_human = edition.date

    return template.render(
        edition=edition,
        date_human=date_human,
        subject=f"The Daily Brief — {edition.date}",
        library_base=library_base.rstrip("/"),
    )


async def send_edition_email(
    edition: Edition,
    to: list[str],
    from_addr: str,
    subject_prefix: str = "The Daily Brief",
    library_base: str = "",
) -> dict:
    """Send the edition via Resend. Returns the API response dict.

    Raises RuntimeError when the key is missing or the API rejects the send —
    callers should treat delivery failure as a run failure, not a warning.
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY environment variable is not set")

    html = render_edition_html(edition, library_base=library_base)
    payload = {
        "from": from_addr,
        "to": to,
        "subject": f"{subject_prefix} — {edition.date}: {edition.headline}",
        "html": html,
    }

    import aiohttp

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as resp:
            body = await resp.json(content_type=None)
            if resp.status >= 400:
                raise RuntimeError(f"Resend API error {resp.status}: {body}")
            return body

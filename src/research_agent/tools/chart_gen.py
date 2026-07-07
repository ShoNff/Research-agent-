"""Brand-standard SVG chart generation.

Pure-Python SVG writer for real dataviz in reports — bar charts, line charts,
timelines, and stat tiles — styled to `assets/brand/STYLE.md` (navy/steel/
blaze/gold palette, soft depth, ≥15px type, rx=14 cards). Deterministic and
dependency-free, so it works identically in local runs and headless CI.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

# Palette — assets/brand/STYLE.md
NAVY = "#1c2d54"
NAVY_MID = "#34518f"
STEEL = "#3a6fae"
STEEL_LIGHT = "#5b91c8"
BLAZE = "#e8732b"
GOLD = "#daa520"
MUTED = "#4a5b80"
SUB_LABEL = "#5a6b8f"
ZONE_LABEL = "#8194b8"
CARD_STROKE = "#d8e1f0"
CANVAS_TOP = "#f6f9fd"
CANVAS_BOTTOM = "#e7eef8"
GRID = "#dce5f2"

SERIES_COLORS = [STEEL, BLAZE, NAVY_MID, GOLD, STEEL_LIGHT, "#3ba66a"]

FONT = "font-family=\"'Segoe UI', 'Helvetica Neue', Arial, sans-serif\""

WIDTH = 1320


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _fmt_value(v: float, unit: str = "") -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, float):
        text = f"{v:,.2f}".rstrip("0").rstrip(".")
    else:
        text = f"{v:,}"
    # Currency symbols read as prefixes; everything else (%, M, GB…) as suffix.
    if unit and unit[0] in "$€£¥":
        return f"{unit}{text}"
    return f"{text}{unit}"


def _svg_open(height: int) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="100%" {FONT}>
<defs>
  <linearGradient id="gCanvas" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{CANVAS_TOP}"/><stop offset="1" stop-color="{CANVAS_BOTTOM}"/>
  </linearGradient>
  <linearGradient id="gSteel" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{STEEL_LIGHT}"/><stop offset="1" stop-color="{STEEL}"/>
  </linearGradient>
  <linearGradient id="gBlaze" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#f0822f"/><stop offset="1" stop-color="#d2541a"/>
  </linearGradient>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="{NAVY}" flood-opacity="0.18"/>
  </filter>
</defs>
<rect width="{WIDTH}" height="{height}" fill="url(#gCanvas)"/>"""


def _title_block(title: str, note: str) -> str:
    parts = [
        f'<text x="70" y="76" font-size="26" font-weight="700" fill="{NAVY}">{_esc(title)}</text>'
    ]
    if note:
        parts.append(
            f'<text x="70" y="106" font-size="15" fill="{MUTED}">{_esc(note)}</text>'
        )
    return "\n".join(parts)


def _card(x: int, y: int, w: int, h: int, accent: str | None = None) -> str:
    out = (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#ffffff" '
        f'stroke="{CARD_STROKE}" filter="url(#soft)"/>'
    )
    if accent:
        out += (
            f'<path d="M {x} {y+14} a 14 14 0 0 1 14 -14 h {w-28} a 14 14 0 0 1 14 14 '
            f'v -8 h -{w} z" fill="{accent}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="6" rx="3" fill="{accent}"/>'
        )
    return out


def _chart_bar(title: str, data: dict) -> str:
    items = data.get("items") or []
    unit = data.get("unit", "")
    note = data.get("note", "")
    n = max(len(items), 1)

    row_h = 58
    top = 140
    height = top + n * row_h + 60
    max_val = max((abs(float(it.get("value", 0))) for it in items), default=1) or 1

    label_w = 320
    bar_zone = WIDTH - 70 - label_w - 200

    rows = []
    for i, it in enumerate(items):
        y = top + i * row_h
        val = float(it.get("value", 0))
        w = max(int(bar_zone * abs(val) / max_val), 6)
        color = it.get("color") or ("url(#gBlaze)" if it.get("highlight") else "url(#gSteel)")
        rows.append(
            f'<text x="{70 + label_w - 18}" y="{y + 27}" font-size="16" fill="{NAVY}" '
            f'text-anchor="end" font-weight="600">{_esc(it.get("label", ""))}</text>'
            f'<rect x="{70 + label_w}" y="{y}" width="{bar_zone}" height="38" rx="10" fill="#eef3fa"/>'
            f'<rect x="{70 + label_w}" y="{y}" width="{w}" height="38" rx="10" fill="{color}"/>'
            f'<text x="{70 + label_w + w + 14}" y="{y + 26}" font-size="16" font-weight="700" '
            f'fill="{NAVY_MID}">{_esc(_fmt_value(val, unit))}</text>'
        )

    return "\n".join([_svg_open(height), _title_block(title, note), *rows, "</svg>"])


def _chart_line(title: str, data: dict) -> str:
    labels = [str(x) for x in (data.get("labels") or [])]
    series = data.get("series") or []
    unit = data.get("unit", "")
    note = data.get("note", "")

    height = 620
    plot_x, plot_y = 120, 150
    plot_w, plot_h = WIDTH - plot_x - 90, height - plot_y - 130

    all_vals = [float(v) for s in series for v in (s.get("values") or [])]
    vmax = max(all_vals, default=1)
    vmin = min(all_vals + [0], default=0)
    span = (vmax - vmin) or 1
    vmax += span * 0.08
    span = (vmax - vmin) or 1

    n_pts = max((len(s.get("values") or []) for s in series), default=2)
    n_pts = max(n_pts, 2)

    def px(i: int) -> float:
        return plot_x + plot_w * i / (n_pts - 1)

    def py(v: float) -> float:
        return plot_y + plot_h * (1 - (v - vmin) / span)

    parts = [_svg_open(height), _title_block(title, note)]

    # Gridlines + y labels
    for g in range(5):
        v = vmin + span * g / 4
        y = py(v)
        parts.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x + plot_w}" y2="{y:.1f}" '
            f'stroke="{GRID}" stroke-width="1.5"/>'
            f'<text x="{plot_x - 14}" y="{y + 5:.1f}" font-size="15" fill="{SUB_LABEL}" '
            f'text-anchor="end">{_esc(_fmt_value(round(v, 2), unit))}</text>'
        )

    # X labels (thin to ~8 max)
    step = max(1, (len(labels) + 7) // 8)
    for i, lab in enumerate(labels):
        if i % step and i != len(labels) - 1:
            continue
        parts.append(
            f'<text x="{px(i):.1f}" y="{plot_y + plot_h + 34}" font-size="15" '
            f'fill="{SUB_LABEL}" text-anchor="middle">{_esc(lab)}</text>'
        )

    # Series
    legend = []
    for si, s in enumerate(series):
        color = s.get("color") or SERIES_COLORS[si % len(SERIES_COLORS)]
        vals = [float(v) for v in (s.get("values") or [])]
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3.2" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        for i, v in enumerate(vals):
            parts.append(
                f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="5" fill="#ffffff" '
                f'stroke="{color}" stroke-width="2.6"/>'
            )
        lx = plot_x + si * 240
        ly = height - 46
        legend.append(
            f'<rect x="{lx}" y="{ly - 13}" width="26" height="8" rx="4" fill="{color}"/>'
            f'<text x="{lx + 36}" y="{ly}" font-size="15" font-weight="600" '
            f'fill="{NAVY}">{_esc(s.get("name", f"Series {si+1}"))}</text>'
        )
    parts.extend(legend)
    parts.append("</svg>")
    return "\n".join(parts)


def _chart_timeline(title: str, data: dict) -> str:
    events = data.get("events") or []
    note = data.get("note", "")
    n = max(len(events), 1)

    height = 560
    axis_y = 300
    pad = 110
    span_w = WIDTH - 2 * pad

    parts = [_svg_open(height), _title_block(title, note)]
    parts.append(
        f'<line x1="{pad}" y1="{axis_y}" x2="{WIDTH - pad}" y2="{axis_y}" '
        f'stroke="{NAVY_MID}" stroke-width="3" stroke-linecap="round"/>'
    )

    card_w = min(250, int(span_w / n) - 14) if n > 1 else 250
    for i, ev in enumerate(events):
        x = pad + (span_w * i / (n - 1) if n > 1 else span_w / 2)
        above = i % 2 == 0
        cy = axis_y - 150 if above else axis_y + 44
        accent = BLAZE if ev.get("highlight") else STEEL
        cx = min(max(x - card_w / 2, 40), WIDTH - 40 - card_w)
        detail = str(ev.get("detail", ""))
        if len(detail) > 64:
            detail = detail[:61] + "…"
        # stem + dot
        stem_y1, stem_y2 = (cy + 106, axis_y) if above else (axis_y, cy)
        parts.append(
            f'<line x1="{x:.1f}" y1="{stem_y1}" x2="{x:.1f}" y2="{stem_y2}" '
            f'stroke="{ZONE_LABEL}" stroke-width="2"/>'
            f'<circle cx="{x:.1f}" cy="{axis_y}" r="9" fill="{accent}" '
            f'stroke="#ffffff" stroke-width="3"/>'
        )
        parts.append(_card(int(cx), int(cy), card_w, 106, accent))
        parts.append(
            f'<text x="{cx + 18:.0f}" y="{cy + 36}" font-size="15" font-weight="700" '
            f'fill="{accent}" letter-spacing="1">{_esc(ev.get("date", ""))}</text>'
            f'<text x="{cx + 18:.0f}" y="{cy + 62}" font-size="16" font-weight="700" '
            f'fill="{NAVY}">{_esc(str(ev.get("label", ""))[:34])}</text>'
            + (
                f'<text x="{cx + 18:.0f}" y="{cy + 86}" font-size="14" '
                f'fill="{MUTED}">{_esc(detail)}</text>'
                if detail
                else ""
            )
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _chart_stat_row(title: str, data: dict) -> str:
    stats = data.get("stats") or []
    note = data.get("note", "")
    n = max(len(stats), 1)

    height = 360
    pad = 70
    gap = 26
    card_w = int((WIDTH - 2 * pad - gap * (n - 1)) / n)
    top = 150

    parts = [_svg_open(height), _title_block(title, note)]
    for i, st in enumerate(stats):
        x = pad + i * (card_w + gap)
        accent = BLAZE if st.get("highlight") else (st.get("color") or STEEL)
        parts.append(_card(x, top, card_w, 150, accent))
        parts.append(
            f'<text x="{x + card_w / 2:.0f}" y="{top + 74}" font-size="40" font-weight="800" '
            f'fill="{NAVY}" text-anchor="middle">{_esc(st.get("value", ""))}</text>'
            f'<text x="{x + card_w / 2:.0f}" y="{top + 106}" font-size="15" font-weight="600" '
            f'fill="{SUB_LABEL}" text-anchor="middle">{_esc(str(st.get("label", ""))[:40])}</text>'
            + (
                f'<text x="{x + card_w / 2:.0f}" y="{top + 130}" font-size="14" '
                f'fill="{ZONE_LABEL}" text-anchor="middle">{_esc(str(st.get("detail", ""))[:44])}</text>'
                if st.get("detail")
                else ""
            )
        )
    parts.append("</svg>")
    return "\n".join(parts)


RENDERERS = {
    "bar": _chart_bar,
    "line": _chart_line,
    "timeline": _chart_timeline,
    "stat_row": _chart_stat_row,
}


def render_chart_svg(kind: str, title: str, data: dict) -> str:
    renderer = RENDERERS.get(kind)
    if renderer is None:
        raise ValueError(f"unknown chart kind {kind!r} — use one of {sorted(RENDERERS)}")
    return renderer(title, data)


@tool(
    "generate_chart",
    "Render a brand-standard SVG data chart. kinds: 'bar' (data_json: {items:[{label,value,highlight?}],unit?,note?}), "
    "'line' (data_json: {labels:[...],series:[{name,values:[...]}],unit?,note?}), "
    "'timeline' (data_json: {events:[{date,label,detail?,highlight?}],note?}), "
    "'stat_row' (data_json: {stats:[{value,label,detail?,highlight?}],note?}). "
    "Use these for quantitative findings instead of Mermaid diagrams.",
    {"kind": str, "title": str, "data_json": str, "output_filename": str, "output_dir": str},
)
async def generate_chart(args: dict[str, Any]) -> dict[str, Any]:
    """Render a chart to an SVG file in the project directory."""
    kind = (args.get("kind") or "").strip()
    title = args.get("title") or ""
    try:
        data = json.loads(args.get("data_json") or "{}")
    except json.JSONDecodeError as e:
        return {"content": [{"type": "text", "text": f"ERROR: invalid data_json: {e}"}]}

    filename = args.get("output_filename") or "chart.svg"
    filename = re.sub(r"[^A-Za-z0-9._-]", "-", filename)
    if not filename.endswith(".svg"):
        filename += ".svg"

    try:
        svg = render_chart_svg(kind, title, data)
    except ValueError as e:
        return {"content": [{"type": "text", "text": f"ERROR: {e}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"ERROR: chart rendering failed: {e}"}]}

    out_dir = Path(args.get("output_dir") or ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(svg, encoding="utf-8")

    result = {
        "status": "success",
        "kind": kind,
        "path": str(out_path.resolve()),
        "markdown_ref": f"![{title}]({filename})",
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

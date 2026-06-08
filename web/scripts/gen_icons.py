#!/usr/bin/env python3
"""Generate the app icon set (PNG + ICO) for the Research Library web app.

Pure Pillow — no SVG rasterizer needed. The design mirrors web/app/icon.svg:
a rounded blue gradient tile with a gold magnifying glass examining a few
"document" lines (the research metaphor). Full-bleed background so iOS / Android
maskable icons can round/crop the corners without clipping the glyph.

Run from anywhere:
    python web/scripts/gen_icons.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
WEB = HERE.parent
APP = WEB / "app"
PUBLIC = WEB / "public"

SS = 4  # supersample factor for smooth edges

# Palette (matches globals.css + icon.svg)
BG_TOP = (59, 98, 168)     # #3b62a8
BG_BOT = (19, 29, 54)      # #131d36
GOLD = (233, 188, 79)      # ~ #e9bc4f (gradient midpoint of f2cd7a→e8b64c)
LINE_BRIGHT = (220, 230, 251)  # #dce6fb
LINE_DIM = (174, 187, 217)     # #aebbd9


def _vertical_gradient(size: int, top: tuple, bot: tuple) -> Image.Image:
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        grad.putpixel((0, y), tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return grad.resize((size, size))


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def render(px: int, *, full_bleed: bool = True) -> Image.Image:
    """Render the icon at `px` pixels (square)."""
    S = px * SS
    radius = 0 if full_bleed else round(S * 0.22)

    # Background tile (gradient, optionally rounded for non-maskable contexts).
    bg = _vertical_gradient(S, BG_TOP, BG_BOT).convert("RGBA")
    if not full_bleed:
        bg.putalpha(_rounded_mask(S, radius))
    # For full-bleed we still round visually only when the platform masks it;
    # keep the corners filled so maskable crops never show empty pixels.

    img = bg
    draw = ImageDraw.Draw(img)

    # Geometry (proportions match icon.svg's 512 viewBox).
    cx, cy = 0.434 * S, 0.434 * S       # lens centre (222/512)
    r_out = 0.203 * S                   # lens radius to ring centre (104/512)
    ring = round(0.066 * S)             # ring stroke (34/512)
    handle_w = round(0.090 * S)         # handle width (46/512)

    # Handle (under the ring), 45° down-right.
    hx1, hy1 = 0.586 * S, 0.586 * S     # 300/512
    hx2, hy2 = 0.789 * S, 0.789 * S     # 404/512
    draw.line([(hx1, hy1), (hx2, hy2)], fill=GOLD, width=handle_w)
    rcap = handle_w // 2
    for (x, y) in ((hx1, hy1), (hx2, hy2)):
        draw.ellipse([x - rcap, y - rcap, x + rcap, y + rcap], fill=GOLD)

    # Document lines, clipped to the lens interior.
    lines_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines_layer)
    lh = round(0.039 * S)               # line height (20/512)
    lr = lh // 2
    x0 = 0.293 * S                      # 150/512
    specs = [
        (0.348 * S, 0.293 * S, LINE_BRIGHT),  # y=178, w=150
        (0.414 * S, 0.281 * S, LINE_DIM),     # y=212, w=144
        (0.480 * S, 0.203 * S, LINE_DIM),     # y=246, w=104
    ]
    for (y, w, col) in specs:
        ld.rounded_rectangle([x0, y, x0 + w, y + lh], radius=lr, fill=col)
    clip = Image.new("L", (S, S), 0)
    inner = r_out  # lines sit inside the ring
    ImageDraw.Draw(clip).ellipse(
        [cx - inner, cy - inner, cx + inner, cy + inner], fill=255
    )
    img.paste(lines_layer, (0, 0), Image.composite(lines_layer.split()[3], Image.new("L", (S, S), 0), clip))

    # Lens ring (on top of lines + handle).
    bbox = [cx - r_out, cy - r_out, cx + r_out, cy + r_out]
    draw.ellipse(bbox, outline=GOLD, width=ring)

    return img.resize((px, px), Image.LANCZOS)


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)

    # Apple touch icon — iOS masks the corners itself, so go full-bleed.
    render(180, full_bleed=True).save(APP / "apple-icon.png")

    # PWA / Android maskable + any-purpose icons.
    render(192, full_bleed=True).save(PUBLIC / "icon-192.png")
    render(512, full_bleed=True).save(PUBLIC / "icon-512.png")

    # Legacy favicon.ico (rounded so it looks right on a white tab bar).
    ico = render(256, full_bleed=False)
    ico.save(APP / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    print("Wrote:")
    for p in [APP / "apple-icon.png", PUBLIC / "icon-192.png",
              PUBLIC / "icon-512.png", APP / "favicon.ico"]:
        print("  ", p.relative_to(WEB), f"({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

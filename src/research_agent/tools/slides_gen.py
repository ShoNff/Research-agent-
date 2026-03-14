"""PowerPoint generation tool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

# Slide layout constants
SLIDE_WIDTH_INCHES = 13.333
SLIDE_HEIGHT_INCHES = 7.5
TITLE_FONT_SIZE = 28
BODY_FONT_SIZE = 16
BULLET_FONT_SIZE = 14

# Color palette
COLORS = {
    "primary": (41, 65, 122),       # Dark blue
    "secondary": (70, 130, 180),     # Steel blue
    "accent": (218, 165, 32),        # Gold
    "text": (51, 51, 51),            # Dark gray
    "light_bg": (245, 247, 250),     # Light gray-blue
    "white": (255, 255, 255),
}


def _create_presentation():
    """Create a new 16:9 presentation."""
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_INCHES)
    prs.slide_height = Inches(SLIDE_HEIGHT_INCHES)
    return prs


def _add_title_slide(prs, title: str, subtitle: str = ""):
    """Add a title slide."""
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

    # Title text box
    from pptx.util import Emu
    txBox = slide.shapes.add_textbox(
        Inches(1), Inches(2.5), Inches(11.333), Inches(2)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = RGBColor(*COLORS["primary"])
    p.alignment = PP_ALIGN.CENTER

    if subtitle:
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.font.size = Pt(18)
        p2.font.color.rgb = RGBColor(*COLORS["text"])
        p2.alignment = PP_ALIGN.CENTER

    return slide


def _add_content_slide(prs, title: str, bullets: list[str], diagram_path: str | None = None):
    """Add a content slide with optional two-column layout."""
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Title
    title_box = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.3), Inches(12.333), Inches(1)
    )
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(TITLE_FONT_SIZE)
    p.font.bold = True
    p.font.color.rgb = RGBColor(*COLORS["primary"])

    # Content area — two column if diagram, full width otherwise
    if diagram_path and Path(diagram_path).exists():
        content_width = Inches(5.5)
        content_left = Inches(0.5)
    else:
        content_width = Inches(12.333)
        content_left = Inches(0.5)

    content_box = slide.shapes.add_textbox(
        content_left, Inches(1.5), content_width, Inches(5.5)
    )
    tf = content_box.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = f"  {bullet}"
        p.font.size = Pt(BULLET_FONT_SIZE)
        p.font.color.rgb = RGBColor(*COLORS["text"])
        p.space_after = Pt(8)

    # Add diagram image
    if diagram_path and Path(diagram_path).exists():
        try:
            slide.shapes.add_picture(
                diagram_path,
                Inches(6.5), Inches(1.5),
                Inches(6.333), Inches(5)
            )
        except Exception:
            pass  # Skip if image can't be loaded

    return slide


def _render_pptx(report_data: dict, output_path: str, diagram_paths: list[str]) -> str:
    """Render a ReportDraft dict to a .pptx file."""
    prs = _create_presentation()

    # Title slide
    _add_title_slide(
        prs,
        report_data.get("title", "Research Report"),
        "Multi-Agent Research System",
    )

    # Executive Summary slide
    takeaways = report_data.get("key_takeaways", [])
    if takeaways:
        _add_content_slide(prs, "Key Takeaways", takeaways)

    # Executive summary as a slide
    exec_summary = report_data.get("executive_summary", "")
    if exec_summary:
        # Split into bullet-sized chunks
        sentences = [s.strip() for s in exec_summary.split(". ") if s.strip()]
        _add_content_slide(prs, "Executive Summary", sentences[:5])

    # Content slides — one per section
    diagram_iter = iter(diagram_paths or [])
    for section in report_data.get("sections", []):
        # Extract key bullets from content
        content = section.get("content", "")
        # Try to extract bullet points or split into sentences
        lines = content.split("\n")
        bullets = []
        for line in lines:
            line = line.strip()
            if line.startswith(("- ", "* ", "• ")):
                bullets.append(line.lstrip("-*• ").strip())
            elif line and len(bullets) < 5:
                bullets.append(line[:120])
        if not bullets:
            bullets = [content[:200]]

        # Try to pair with a diagram
        diagram = next(diagram_iter, None)
        _add_content_slide(
            prs,
            section.get("title", ""),
            bullets[:5],
            diagram,
        )

    # Sources slide
    sources = report_data.get("sources", [])
    if sources:
        source_bullets = []
        for src in sources[:8]:
            tier = src.get("reliability_tier", "unknown").upper()
            source_bullets.append(f"[{tier}] {src.get('title', 'Untitled')}")
        _add_content_slide(prs, "Sources & Methodology", source_bullets)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output))
    return str(output)


@tool(
    "render_pptx",
    "Render a structured research report into a PowerPoint presentation (.pptx). Pass the report as a JSON string.",
    {
        "type": "object",
        "properties": {
            "report_json": {"type": "string", "description": "JSON-serialized ReportDraft"},
            "output_path": {"type": "string", "description": "Path for the output .pptx file"},
            "diagram_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Paths to diagram images to embed",
            },
        },
        "required": ["report_json", "output_path"],
    },
)
async def render_pptx(args: dict[str, Any]) -> dict[str, Any]:
    """Generate a PowerPoint from report data."""
    try:
        report_data = json.loads(args["report_json"])
        diagram_paths = args.get("diagram_paths", [])
        path = _render_pptx(report_data, args["output_path"], diagram_paths)
        return {
            "content": [{"type": "text", "text": f"PowerPoint saved to: {path}"}]
        }
    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"ERROR: Failed to generate PowerPoint: {e}"}
            ]
        }


@tool(
    "generate_slide",
    "Add a single slide to an existing or new PowerPoint presentation.",
    {
        "type": "object",
        "properties": {
            "pptx_path": {"type": "string", "description": "Path to .pptx file (creates new if doesn't exist)"},
            "title": {"type": "string", "description": "Slide title"},
            "bullets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Bullet point text items",
            },
            "diagram_path": {"type": "string", "description": "Optional path to diagram image"},
            "layout": {"type": "string", "description": "Slide layout: title, content, two_column, visual"},
            "speaker_notes": {"type": "string", "description": "Optional speaker notes"},
        },
        "required": ["pptx_path", "title", "layout"],
    },
)
async def generate_slide(args: dict[str, Any]) -> dict[str, Any]:
    """Add a single slide to a presentation."""
    from pptx import Presentation

    pptx_path = Path(args["pptx_path"])

    try:
        if pptx_path.exists():
            prs = Presentation(str(pptx_path))
        else:
            prs = _create_presentation()

        layout = args.get("layout", "content")
        if layout == "title":
            _add_title_slide(prs, args["title"], args.get("speaker_notes", ""))
        else:
            _add_content_slide(
                prs,
                args["title"],
                args.get("bullets", []),
                args.get("diagram_path"),
            )

        pptx_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(pptx_path))
        return {
            "content": [{"type": "text", "text": f"Slide added to: {pptx_path}"}]
        }
    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"ERROR: Failed to add slide: {e}"}
            ]
        }

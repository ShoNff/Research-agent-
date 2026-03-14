"""Mermaid diagram generation tool."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool


@tool(
    "generate_diagram",
    "Render a Mermaid diagram to PNG or SVG file. Write the Mermaid source code and specify the output filename and directory. Returns the output file path on success.",
    {"mermaid_source": str, "output_filename": str, "output_dir": str},
)
async def generate_diagram(args: dict[str, Any]) -> dict[str, Any]:
    """Render a Mermaid diagram using mmdc CLI."""
    output_dir = Path(args["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args["output_filename"]

    # Determine output format from extension
    fmt = "png" if output_path.suffix == ".png" else "svg"

    # Write mermaid source to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mmd", delete=False
    ) as f:
        f.write(args["mermaid_source"])
        mmd_path = f.name

    try:
        result = subprocess.run(
            [
                "mmdc",
                "-i", mmd_path,
                "-o", str(output_path),
                "-f", fmt,
                "--backgroundColor", "white",
                "--width", "1200",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            # Fallback: save the mermaid source as .mmd file
            mmd_output = output_path.with_suffix(".mmd")
            mmd_output.write_text(args["mermaid_source"])
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "status": "partial",
                                "message": f"mmdc rendering failed: {result.stderr.strip()}. Mermaid source saved.",
                                "mermaid_source_path": str(mmd_output),
                                "mermaid_source": args["mermaid_source"],
                            }
                        ),
                    }
                ]
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "success",
                            "output_path": str(output_path),
                            "format": fmt,
                        }
                    ),
                }
            ]
        }

    except FileNotFoundError:
        # mmdc not installed — save source file as fallback
        mmd_output = output_path.with_suffix(".mmd")
        mmd_output.write_text(args["mermaid_source"])
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "status": "partial",
                            "message": "mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli. Mermaid source saved.",
                            "mermaid_source_path": str(mmd_output),
                            "mermaid_source": args["mermaid_source"],
                        }
                    ),
                }
            ]
        }
    except subprocess.TimeoutExpired:
        return {
            "content": [
                {"type": "text", "text": "ERROR: Diagram rendering timed out (30s limit)"}
            ]
        }
    finally:
        Path(mmd_path).unlink(missing_ok=True)

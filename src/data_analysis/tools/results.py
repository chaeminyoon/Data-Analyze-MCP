"""Tools that bring generated artifacts back into the conversation.

Chart tools return file paths; these tools let the client actually *see*
the results — ``view_chart`` streams a PNG back as MCP image content (so
multimodal clients like Claude Desktop/Code render it inline), and
``list_outputs`` browses everything generated so far.
"""
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import Image

from .. import config
from ..server import mcp

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")


def _resolve(file_path: str) -> Path:
    """Resolve a result path, also accepting bare filenames from OUTPUT_DIR."""
    p = Path(file_path)
    if not p.exists():
        candidate = config.OUTPUT_DIR / p.name
        if candidate.exists():
            return candidate
    return p


@mcp.tool()
def view_chart(file_path: str) -> Image:
    """Display a generated chart directly in the conversation.

    Pass the path returned by any plot tool (plot_auto, plot_histogram, ...).
    The PNG is returned as MCP image content, so multimodal clients render it
    inline — the user sees the result without opening any files.
    Interactive .html charts cannot be inlined; open those in a browser.
    """
    p = _resolve(file_path)
    if not p.exists():
        raise ValueError(f"File not found: {file_path}")
    suffix = p.suffix.lower()
    if suffix == ".html":
        raise ValueError(
            f"'{p.name}' is an interactive HTML chart and cannot be displayed inline — "
            f"open it in a browser: {p.resolve()}"
        )
    if suffix not in _IMAGE_SUFFIXES:
        raise ValueError(f"view_chart supports PNG/JPEG images, got '{suffix}'.")
    return Image(path=str(p))


@mcp.tool()
def list_outputs(limit: int = 20) -> dict:
    """List recently generated result files (charts, exports), newest first."""
    out = config.OUTPUT_DIR
    if not out.exists():
        return {"output_dir": str(out.resolve()), "files": [], "count": 0}

    files = sorted(
        (f for f in out.iterdir() if f.is_file()),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return {
        "output_dir": str(out.resolve()),
        "count": len(files),
        "files": [
            {
                "name": f.name,
                "path": str(f.resolve()),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"),
                "viewable_inline": f.suffix.lower() in _IMAGE_SUFFIXES,
            }
            for f in files[:limit]
        ],
    }

"""Chart style tools — let the LLM switch the visual theme on request."""
from .. import theming
from ..server import mcp


@mcp.tool()
def list_chart_styles() -> dict:
    """List available chart design themes and which one is active.

    Every plot tool draws through the active theme, so switching it changes
    colors, grid, typography and background for all subsequent charts.
    """
    return {
        "current": theming.current(),
        "available": theming.available(),
        "hint": "Switch with set_chart_style(style). The theme applies to all "
        "later charts (static PNG and interactive HTML alike).",
    }


@mcp.tool()
def set_chart_style(style: str) -> dict:
    """Switch the chart design theme for all subsequent charts.

    Styles: 'modern' (default, refined palette + subtle grid), 'dark'
    (dark background for dashboards), 'minimal' (single accent, report-ready),
    'vibrant' (high-saturation for presentations), 'classic' (library defaults).
    """
    theming.apply(style)
    return {
        "style": style,
        "description": theming.available()[style],
        "palette": theming.palette(),
        "message": f"Chart style switched to '{style}'. All charts from now on use this design.",
    }

"""Tool implementations, grouped by domain.

Importing every submodule here registers all ``@mcp.tool()`` functions on the
shared server instance.
"""
from . import (  # noqa: F401  (imported for @mcp.tool registration side effects)
    exploration,
    feature_engineering,
    ml,
    preprocessing,
    statistics,
    visualization,
)

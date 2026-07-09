"""The shared FastMCP server instance.

Tool modules import ``mcp`` from here and attach themselves with the
``@mcp.tool()`` decorator.  Importing a tool module is what registers its
tools, so :mod:`data_analysis.__main__` imports every module for its side
effects before calling ``mcp.run()``.
"""
from mcp.server.fastmcp import FastMCP

from . import fonts  # noqa: F401  (configures matplotlib on import)

mcp = FastMCP("DataAnalysis")

"""MCP Advanced Data Analysis System.

A FastMCP server exposing data exploration, preprocessing, feature
engineering, visualization, machine-learning and statistical tools.

The package is organised by domain:

- ``data_analysis.server``   -- the shared ``FastMCP`` instance and config
- ``data_analysis.cache``    -- the in-memory dataset cache / loader
- ``data_analysis.helpers``  -- shared validation & plotting helpers
- ``data_analysis.tools.*``  -- the actual ``@mcp.tool()`` implementations
"""

__version__ = "3.2.0"

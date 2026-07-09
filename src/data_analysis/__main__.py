"""Entry point: ``python -m data_analysis`` starts the MCP server over stdio."""
from . import prompts  # noqa: F401  (registers the default prompt)
from . import tools  # noqa: F401  (registers all @mcp.tool functions)
from .server import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

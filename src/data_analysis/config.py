"""Runtime configuration for the data-analysis server.

All values can be overridden via environment variables so the server can be
deployed without touching the code.
"""
import os
from pathlib import Path

# Directory where generated artifacts (plots, HTML, exported CSVs) are written.
# Defaults to ``./outputs`` under the current working directory.
OUTPUT_DIR = Path(os.getenv("MCP_OUTPUT_DIR", "outputs"))

# Correlation threshold used by profiling to flag "high" correlations.
HIGH_CORRELATION_THRESHOLD = float(os.getenv("MCP_HIGH_CORR_THRESHOLD", "0.7"))

# A target column is treated as a classification target when it is
# non-numeric, or numeric with at most this many distinct values.
CLASSIFICATION_MAX_UNIQUE = int(os.getenv("MCP_CLASSIFICATION_MAX_UNIQUE", "10"))

# Maximum number of indices/values echoed back in tool responses so payloads
# stay small.  This never limits how many rows an *operation* touches.
PREVIEW_LIMIT = int(os.getenv("MCP_PREVIEW_LIMIT", "100"))

# Default DPI for saved matplotlib figures.
FIGURE_DPI = int(os.getenv("MCP_FIGURE_DPI", "100"))

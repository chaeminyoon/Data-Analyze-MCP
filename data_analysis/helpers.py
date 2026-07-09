"""Shared validation, plotting and ML helpers.

These functions collapse the boilerplate that was previously copy-pasted
across every tool (column checks, filename sanitising, figure saving, and
classification-vs-regression detection).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from . import config


# --- [Validation] ---------------------------------------------------------
def require_columns(df: pd.DataFrame, *columns: str) -> None:
    """Raise ValueError if any of ``columns`` is missing from ``df``.

    ``None`` entries are ignored so optional columns can be passed straight
    through, e.g. ``require_columns(df, x, y, hue)``.
    """
    missing = [c for c in columns if c is not None and c not in df.columns]
    if missing:
        raise ValueError(f"Column(s) not found in CSV: {missing}")


def require_numeric(df: pd.DataFrame, column: str) -> None:
    """Raise ValueError if ``column`` is missing or not numeric."""
    require_columns(df, column)
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")


# --- [Output artifacts] ----------------------------------------------------
def safe_name(text: str) -> str:
    """Sanitise a string for use in a filename."""
    cleaned = "".join(c for c in text if c.isalnum() or c in (" ", "_"))
    return cleaned.replace(" ", "_")


def output_path(filename: str) -> str:
    """Resolve ``filename`` inside the configured output directory."""
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return str(config.OUTPUT_DIR / filename)


def save_current_figure(filename: str) -> str:
    """Save the active matplotlib figure to the output dir and close it.

    Always closes the figure, even on error, to avoid leaking figures across
    tool calls.
    """
    try:
        path = output_path(filename)
        plt.savefig(path, dpi=config.FIGURE_DPI, bbox_inches="tight")
        return path
    finally:
        plt.close()


# --- [ML task detection] ---------------------------------------------------
def is_classification_target(y: pd.Series) -> bool:
    """Decide whether ``y`` should be modelled as classification.

    Non-numeric targets are always classification; numeric targets with at
    most ``config.CLASSIFICATION_MAX_UNIQUE`` distinct values are treated as
    classification too.  Centralising this keeps every ML tool consistent.
    """
    if y.dtype == "object" or isinstance(y.dtype, pd.CategoricalDtype):
        return True
    return y.nunique() <= config.CLASSIFICATION_MAX_UNIQUE

"""Shared validation, plotting and ML helpers.

These functions collapse the boilerplate that was previously copy-pasted
across every tool (column checks, filename sanitising, figure saving, and
classification-vs-regression detection).
"""
from __future__ import annotations

import re
import warnings

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


# --- [Column role classification] -------------------------------------------
# Strings must look date-like (separators / time parts) before we even try
# pd.to_datetime, so plain numbers like "10" are never treated as dates.
_DATE_HINT = re.compile(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\d{4}[-/]\d{1,2}\b|\d{1,2}:\d{2}")
_ID_NAME = re.compile(r"(^|[_\s])(id|uuid|key|code)s?$", re.IGNORECASE)


def _mostly_datetime(series: pd.Series, threshold: float = 0.9) -> bool:
    """True if a (sampled) object series parses as datetime for >=threshold."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    if float(sample.str.contains(_DATE_HINT, regex=True).mean()) < threshold:
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(sample, errors="coerce")
    return float(parsed.notna().mean()) >= threshold


def classify_columns(df: pd.DataFrame) -> dict[str, dict]:
    """Classify every column into a visualization/analysis role.

    Roles: ``numeric`` (continuous), ``discrete`` (few-valued numeric),
    ``categorical``, ``high_cardinality`` (categorical with many levels),
    ``datetime``, ``id`` (unique per row / identifier-named), ``text``
    (free-form strings), ``constant``, ``empty``.

    Returns ``{column: {"role", "nunique", "missing_pct"}}``.
    """
    n = len(df)
    out: dict[str, dict] = {}
    for col in df.columns:
        s = df[col]
        nunique = int(s.nunique(dropna=True))
        entry = {
            "nunique": nunique,
            "missing_pct": round(float(s.isna().mean()) * 100, 2) if n else 0.0,
        }
        if n == 0 or nunique == 0:
            entry["role"] = "empty"
        elif nunique == 1:
            entry["role"] = "constant"
        elif pd.api.types.is_datetime64_any_dtype(s):
            entry["role"] = "datetime"
        elif pd.api.types.is_bool_dtype(s):
            entry["role"] = "categorical"
        elif pd.api.types.is_numeric_dtype(s):
            if _ID_NAME.search(str(col)) and nunique / n > 0.9:
                entry["role"] = "id"
            elif nunique <= 15:
                entry["role"] = "discrete"
            else:
                entry["role"] = "numeric"
        elif _mostly_datetime(s):
            entry["role"] = "datetime"
        elif nunique / n >= 0.95:
            entry["role"] = "id"
        elif nunique / n >= 0.5:
            entry["role"] = "text"
        else:
            entry["role"] = "categorical" if nunique <= 50 else "high_cardinality"
        out[col] = entry
    return out


# --- [ML task detection] ---------------------------------------------------
def is_classification_target(y: pd.Series) -> bool:
    """Decide whether ``y`` should be modelled as classification.

    Non-numeric targets are always classification; numeric targets with at
    most ``config.CLASSIFICATION_MAX_UNIQUE`` distinct values are treated as
    classification too.  Centralising this keeps every ML tool consistent.
    """
    # dtype-agnostic: pandas 3 strings are 'str' dtype, not 'object'
    if not pd.api.types.is_numeric_dtype(y):
        return True
    return y.nunique() <= config.CLASSIFICATION_MAX_UNIQUE

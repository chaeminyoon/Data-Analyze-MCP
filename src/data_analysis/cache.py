"""In-memory dataset cache and CSV loader.

The cache is keyed by CSV path.  Preprocessing tools intentionally overwrite
the cached frame with their transformed result via :func:`store`, so that a
chain of operations (handle missing -> scale -> encode) accumulates on the
same key without re-reading the file.  Call :func:`reload` to discard
in-memory changes and read the original file again.
"""
import os

import pandas as pd

_DATA_CACHE: dict[str, pd.DataFrame] = {}


def get_data(csv_path: str) -> pd.DataFrame:
    """Return the (possibly cached) DataFrame for ``csv_path``.

    Raises FileNotFoundError if the path does not exist and is not cached, and
    ValueError if the CSV cannot be parsed.
    """
    if csv_path in _DATA_CACHE:
        return _DATA_CACHE[csv_path]

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the client
        raise ValueError(f"Error loading CSV: {exc}") from exc

    _DATA_CACHE[csv_path] = df
    return df


def store(csv_path: str, df: pd.DataFrame) -> None:
    """Replace the cached frame for ``csv_path`` (used after transformations)."""
    _DATA_CACHE[csv_path] = df


def reload(csv_path: str) -> pd.DataFrame:
    """Drop any in-memory changes and re-read the original CSV."""
    _DATA_CACHE.pop(csv_path, None)
    return get_data(csv_path)


def cached() -> dict[str, pd.DataFrame]:
    """Return the live cache mapping."""
    return _DATA_CACHE


def clear(csv_path: str | None = None) -> int:
    """Clear one or all cached datasets. Returns the number removed."""
    if csv_path is None:
        count = len(_DATA_CACHE)
        _DATA_CACHE.clear()
        return count
    return 1 if _DATA_CACHE.pop(csv_path, None) is not None else 0

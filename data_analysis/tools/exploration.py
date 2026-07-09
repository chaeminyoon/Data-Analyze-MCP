"""Phase 1: data exploration, profiling and cache management tools."""
import os

import pandas as pd

from ..cache import cached, clear, get_data
from ..config import HIGH_CORRELATION_THRESHOLD, PREVIEW_LIMIT
from ..server import mcp


@mcp.tool()
def get_dataset_info(csv_path: str) -> dict:
    """Get basic information about a CSV dataset."""
    df = get_data(csv_path)
    return {
        "filename": os.path.basename(csv_path),
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict(),
    }


@mcp.tool()
def profile_dataset(csv_path: str) -> dict:
    """Comprehensive dataset profiling with statistics and correlations."""
    df = get_data(csv_path)

    profile = {
        "filename": os.path.basename(csv_path),
        "shape": df.shape,
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2),
    }

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        profile["numeric_stats"] = df[numeric_cols].describe().to_dict()

    categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
    if categorical_cols:
        cat_stats = {}
        for col in categorical_cols:
            modes = df[col].mode()
            cat_stats[col] = {
                "unique_count": df[col].nunique(),
                "most_frequent": modes[0] if len(modes) > 0 else None,
                "frequency": int(df[col].value_counts().iloc[0]) if len(df[col]) > 0 else 0,
            }
        profile["categorical_stats"] = cat_stats

    total_missing = int(df.isnull().sum().sum())
    total_cells = df.shape[0] * df.shape[1]
    profile["missing_summary"] = {
        "total_missing": total_missing,
        "missing_percentage": round(total_missing / total_cells * 100, 2) if total_cells else 0.0,
    }

    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
        high_corr = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > HIGH_CORRELATION_THRESHOLD:
                    high_corr.append(
                        {
                            "feature1": corr_matrix.columns[i],
                            "feature2": corr_matrix.columns[j],
                            "correlation": round(float(corr_value), 3),
                        }
                    )
        profile["high_correlations"] = high_corr

    return profile


@mcp.tool()
def detect_data_types(csv_path: str) -> dict:
    """Auto-detect and classify column data types."""
    df = get_data(csv_path)

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = []
    datetime_cols = []
    text_cols = []

    for col in df.select_dtypes(include=["object"]).columns:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            # Treat as datetime only if the bulk of non-null values parsed.
            non_null = df[col].notna().sum()
            if non_null and parsed.notna().sum() / non_null > 0.9:
                datetime_cols.append(col)
                continue
        except (ValueError, TypeError):
            pass

        if len(df) and df[col].nunique() / len(df) < 0.5:
            categorical_cols.append(col)
        else:
            text_cols.append(col)

    return {
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "text_columns": text_cols,
        "total_columns": len(df.columns),
    }


@mcp.tool()
def find_duplicates(csv_path: str, subset: list = None) -> dict:
    """Detect duplicate rows in dataset."""
    df = get_data(csv_path)

    duplicates = df.duplicated(subset=subset, keep="first")
    duplicate_count = int(duplicates.sum())

    return {
        "duplicate_count": duplicate_count,
        "duplicate_percentage": round(duplicate_count / len(df) * 100, 2) if len(df) else 0.0,
        "duplicate_indices": df[duplicates].index.tolist()[:PREVIEW_LIMIT],
        "total_rows": len(df),
    }


@mcp.tool()
def list_cached_datasets() -> dict:
    """List all currently cached datasets in memory."""
    cached_info = []
    total_memory = 0.0

    for path, df in cached().items():
        memory_mb = df.memory_usage(deep=True).sum() / 1024**2
        total_memory += memory_mb
        cached_info.append({"path": path, "shape": df.shape, "memory_mb": round(memory_mb, 2)})

    return {
        "cached_files": cached_info,
        "count": len(cached_info),
        "total_memory_mb": round(total_memory, 2),
    }


@mcp.tool()
def clear_cache(csv_path: str = None) -> str:
    """Clear cached datasets from memory."""
    if csv_path:
        removed = clear(csv_path)
        if removed:
            return f"Cache cleared for: {csv_path}"
        return f"No cached data found for: {csv_path}"

    count = clear()
    return f"Cache cleared successfully. {count} dataset(s) removed from memory."

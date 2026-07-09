"""Data cleaning & preprocessing tools: missing values, outliers, encoding, scaling."""
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from ..cache import get_data, store
from ..config import PREVIEW_LIMIT
from ..helpers import require_columns, require_numeric
from ..server import mcp


@mcp.tool()
def handle_missing_values(csv_path: str, strategy: dict = None, save_to: str = None) -> dict:
    """Handle missing values with various strategies.

    ``strategy`` maps ``"numeric"``/``"categorical"`` to a fill method:
    numeric -> mean|median|mode|ffill, categorical -> mode|ffill.  If any value
    in ``strategy`` is ``"drop"``, rows with remaining NaNs are dropped.
    """
    df = get_data(csv_path).copy()
    original_shape = df.shape

    if strategy is None:
        strategy = {"numeric": "mean", "categorical": "mode"}

    strategies_used = {}

    for col in df.select_dtypes(include=["number"]).columns:
        if df[col].isnull().sum() == 0:
            continue
        strat = strategy.get("numeric", "mean")
        if strat == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif strat == "median":
            df[col] = df[col].fillna(df[col].median())
        elif strat == "mode":
            modes = df[col].mode()
            df[col] = df[col].fillna(modes[0] if len(modes) > 0 else 0)
        elif strat == "ffill":
            df[col] = df[col].ffill()
        strategies_used[col] = strat

    for col in df.select_dtypes(include=["object"]).columns:
        if df[col].isnull().sum() == 0:
            continue
        strat = strategy.get("categorical", "mode")
        if strat == "mode":
            modes = df[col].mode()
            df[col] = df[col].fillna(modes[0] if len(modes) > 0 else "Unknown")
        elif strat == "ffill":
            df[col] = df[col].ffill()
        strategies_used[col] = strat

    if "drop" in strategy.values():
        df = df.dropna()

    store(csv_path, df)

    result = {
        "original_shape": original_shape,
        "new_shape": df.shape,
        "rows_affected": original_shape[0] - df.shape[0],
        "strategies_used": strategies_used,
    }
    if save_to:
        df.to_csv(save_to, index=False)
        result["output_path"] = save_to
    return result


def _outlier_indices(df: pd.DataFrame, column: str, method: str):
    """Return (indices, lower_bound, upper_bound) for outliers in ``column``.

    Shared by :func:`detect_outliers` and :func:`remove_outliers` so both agree
    on the full set of outliers (the display tool truncates, removal does not).
    """
    data = df[column].dropna()

    if method == "iqr":
        q1, q3 = data.quantile(0.25), data.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    elif method == "zscore":
        lower = data.mean() - 3 * data.std()
        upper = data.mean() + 3 * data.std()
    else:
        raise ValueError("Method must be 'iqr' or 'zscore'.")

    mask = (df[column] < lower) | (df[column] > upper)
    return df.index[mask.fillna(False)].tolist(), float(lower), float(upper)


@mcp.tool()
def detect_outliers(csv_path: str, column: str, method: str = "iqr") -> dict:
    """Detect outliers in a numeric column using the IQR or z-score rule."""
    df = get_data(csv_path)
    require_numeric(df, column)

    indices, lower, upper = _outlier_indices(df, column, method)

    return {
        "outlier_count": len(indices),
        "outlier_percentage": round(len(indices) / len(df) * 100, 2) if len(df) else 0.0,
        "outlier_indices": indices[:PREVIEW_LIMIT],
        "outlier_values": df.loc[indices, column].tolist()[:PREVIEW_LIMIT],
        "lower_bound": lower,
        "upper_bound": upper,
        "method": method,
    }


@mcp.tool()
def remove_outliers(csv_path: str, column: str, method: str = "iqr", save_to: str = None) -> dict:
    """Remove *all* outliers from a numeric column (not just the first 100)."""
    df = get_data(csv_path).copy()
    require_numeric(df, column)
    original_shape = df.shape

    indices, _, _ = _outlier_indices(df, column, method)
    df_cleaned = df.drop(index=indices)
    store(csv_path, df_cleaned)

    result = {
        "rows_removed": len(indices),
        "original_shape": original_shape,
        "new_shape": df_cleaned.shape,
        "method": method,
    }
    if save_to:
        df_cleaned.to_csv(save_to, index=False)
        result["output_path"] = save_to
    return result


@mcp.tool()
def encode_categorical(
    csv_path: str, columns: list, method: str = "label", save_to: str = None
) -> dict:
    """Encode categorical variables using label encoding or one-hot encoding."""
    if method not in ("label", "onehot"):
        raise ValueError("Method must be 'label' or 'onehot'.")

    df = get_data(csv_path).copy()
    require_columns(df, *columns)

    encoded_info = {}
    if method == "label":
        for col in columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoded_info[col] = {"method": "label", "classes": le.classes_.tolist()}
    else:  # onehot
        df = pd.get_dummies(df, columns=columns, prefix=columns)
        for col in columns:
            new_cols = [c for c in df.columns if c.startswith(f"{col}_")]
            encoded_info[col] = {"method": "onehot", "new_columns": new_cols}

    store(csv_path, df)

    result = {"encoded_columns": encoded_info, "new_shape": df.shape}
    if save_to:
        df.to_csv(save_to, index=False)
        result["output_path"] = save_to
    return result


@mcp.tool()
def scale_features(
    csv_path: str, columns: list = None, method: str = "standard", save_to: str = None
) -> dict:
    """Scale numeric features using Standard or MinMax scaling."""
    if method not in ("standard", "minmax"):
        raise ValueError("Method must be 'standard' or 'minmax'.")

    df = get_data(csv_path).copy()

    if columns is None:
        columns = df.select_dtypes(include=["number"]).columns.tolist()
    for col in columns:
        require_numeric(df, col)

    if method == "standard":
        scaler = StandardScaler()
        df[columns] = scaler.fit_transform(df[columns])
        scaling_info = {
            "method": "StandardScaler",
            "mean": scaler.mean_.tolist(),
            "std": scaler.scale_.tolist(),
        }
    else:  # minmax
        scaler = MinMaxScaler()
        df[columns] = scaler.fit_transform(df[columns])
        scaling_info = {
            "method": "MinMaxScaler",
            "min": scaler.data_min_.tolist(),
            "max": scaler.data_max_.tolist(),
        }

    store(csv_path, df)

    result = {
        "scaled_columns": columns,
        "scaling_info": scaling_info,
        "new_shape": df.shape,
    }
    if save_to:
        df.to_csv(save_to, index=False)
        result["output_path"] = save_to
    return result  # NOTE: this return was missing in v3.1 (function returned None)

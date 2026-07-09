"""Phase 3.5: advanced feature engineering tools."""
import pandas as pd
from sklearn.preprocessing import PolynomialFeatures

from ..cache import get_data, store
from ..helpers import require_columns
from ..server import mcp

_DATETIME_EXTRACTORS = {
    "year": lambda s: s.dt.year,
    "month": lambda s: s.dt.month,
    "day": lambda s: s.dt.day,
    "hour": lambda s: s.dt.hour,
    "minute": lambda s: s.dt.minute,
    "second": lambda s: s.dt.second,
    "dayofweek": lambda s: s.dt.dayofweek,
    "quarter": lambda s: s.dt.quarter,
    "is_weekend": lambda s: s.dt.dayofweek.isin([5, 6]).astype(int),
}


@mcp.tool()
def create_derived_feature(
    csv_path: str, expression: str, new_column_name: str, save_to: str = None
) -> dict:
    """Create a new feature from a math expression over existing columns.

    Uses ``DataFrame.eval`` (supports +, -, *, /, **, parentheses and column
    names), which is safer and faster than Python ``eval``.
    Example: expression="price / area", new_column_name="price_per_sqft".
    """
    df = get_data(csv_path).copy()
    try:
        df[new_column_name] = df.eval(expression)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Feature creation failed: {exc}") from exc

    store(csv_path, df)

    result = {
        "message": f"Created feature '{new_column_name}'",
        "expression": expression,
        "preview": df[[new_column_name]].head().to_dict(),
        "new_shape": df.shape,
    }
    if save_to:
        df.to_csv(save_to, index=False)
        result["saved_to"] = save_to
    return result


@mcp.tool()
def create_polynomial_features(
    csv_path: str,
    columns: list[str],
    degree: int = 2,
    interaction_only: bool = False,
    save_to: str = None,
) -> dict:
    """Generate polynomial and interaction features for the given columns."""
    df = get_data(csv_path).copy()
    require_columns(df, *columns)

    try:
        poly = PolynomialFeatures(
            degree=degree, interaction_only=interaction_only, include_bias=False
        )
        poly_data = poly.fit_transform(df[columns])
        feature_names = poly.get_feature_names_out(columns)
        poly_df = pd.DataFrame(poly_data, columns=feature_names, index=df.index)

        # PolynomialFeatures echoes the original degree-1 terms; only add the
        # genuinely new columns so we don't duplicate existing data.
        new_columns = [c for c in feature_names if c not in df.columns]
        for col in new_columns:
            df[col] = poly_df[col]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Polynomial feature generation failed: {exc}") from exc

    store(csv_path, df)

    result = {
        "message": f"Generated {len(new_columns)} new polynomial features",
        "input_columns": columns,
        "degree": degree,
        "new_columns": [c for c in feature_names.tolist() if c not in columns],
        "new_shape": df.shape,
    }
    if save_to:
        df.to_csv(save_to, index=False)
        result["saved_to"] = save_to
    return result


@mcp.tool()
def extract_datetime_features(
    csv_path: str,
    column: str,
    features: list[str] = None,
    save_to: str = None,
) -> dict:
    """Extract temporal features from a datetime column.

    Supported features: year, month, day, hour, minute, second, dayofweek,
    quarter, is_weekend.
    """
    if features is None:
        features = ["year", "month", "day", "dayofweek"]

    df = get_data(csv_path).copy()
    require_columns(df, column)

    try:
        if not pd.api.types.is_datetime64_any_dtype(df[column]):
            df[column] = pd.to_datetime(df[column])

        created = []
        for feat in features:
            extractor = _DATETIME_EXTRACTORS.get(feat)
            if extractor is None:
                raise ValueError(f"Unsupported datetime feature: '{feat}'")
            new_col = f"{column}_{feat}"
            df[new_col] = extractor(df[column])
            created.append(new_col)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Datetime extraction failed: {exc}") from exc

    store(csv_path, df)

    result = {
        "message": f"Extracted {len(created)} datetime features",
        "source_column": column,
        "created_columns": created,
        "new_shape": df.shape,
    }
    if save_to:
        df.to_csv(save_to, index=False)
        result["saved_to"] = save_to
    return result

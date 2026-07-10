"""Preprocessing tools — including regressions for bugs fixed in the refactor."""
import warnings

import pytest

from data_analysis import cache
from data_analysis.tools import preprocessing as pp


def test_scale_features_returns_result(house_csv):
    """Regression: v3.1 was missing `return result` (always returned None)."""
    result = pp.scale_features(house_csv, columns=["area"], method="standard")
    assert isinstance(result, dict)
    assert result["scaling_info"]["method"] == "StandardScaler"
    assert result["scaled_columns"] == ["area"]


def test_remove_outliers_not_capped_at_100(house_csv):
    """Regression: removal used detect's display list truncated to 100 rows."""
    detected = pp.detect_outliers(house_csv, "price")
    cache.reload(house_csv)
    removed = pp.remove_outliers(house_csv, "price")

    assert detected["outlier_count"] > 100
    assert removed["rows_removed"] == detected["outlier_count"]
    # The *display* list stays capped for payload size; the removal must not be.
    assert len(detected["outlier_indices"]) == 100


def test_handle_missing_values_no_deprecation(churn_csv):
    """Regression: fillna(inplace)/method='ffill' raised FutureWarnings on pandas 2+."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        result = pp.handle_missing_values(churn_csv)
    assert result["strategies_used"] == {"charges": "mean"}
    assert cache.get_data(churn_csv)["charges"].isna().sum() == 0


def test_encode_categorical_label_and_onehot(churn_csv):
    label = pp.encode_categorical(churn_csv, ["contract"], "label")
    assert sorted(label["encoded_columns"]["contract"]["classes"]) == ["Monthly", "Yearly"]

    cache.reload(churn_csv)
    onehot = pp.encode_categorical(churn_csv, ["contract"], "onehot")
    assert any(c.startswith("contract_") for c in onehot["encoded_columns"]["contract"]["new_columns"])


def test_detect_outliers_rejects_non_numeric(churn_csv):
    with pytest.raises(ValueError, match="must be numeric"):
        pp.detect_outliers(churn_csv, "contract")


def test_unknown_method_rejected(house_csv):
    with pytest.raises(ValueError):
        pp.detect_outliers(house_csv, "price", method="magic")
    with pytest.raises(ValueError):
        pp.scale_features(house_csv, method="magic")

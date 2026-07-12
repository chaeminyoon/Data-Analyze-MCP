"""Smoke tests for the composition / distribution / ML-diagnostic chart tools."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data_analysis.tools import composition, distribution, ml
from data_analysis.tools.composition import OTHER_LABEL, fold_other


@pytest.fixture
def sales_csv(tmp_path: Path) -> str:
    rng = np.random.default_rng(7)
    n = 400
    df = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=n, freq="D").astype(str),
            "region": rng.choice(["North", "South", "East", "West"], n),
            "channel": rng.choice(list("ABCDEFGHIJKL"), n),  # 12 levels -> folds
            "period": rng.choice(["2024", "2025"], n),
            "revenue": rng.gamma(2.0, 100.0, n).round(2),
            "units": rng.integers(1, 50, n),
            "with_nan": np.where(rng.random(n) < 0.25, np.nan, rng.random(n)),
        }
    )
    path = tmp_path / "sales.csv"
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def ml_csv(tmp_path: Path) -> str:
    rng = np.random.default_rng(11)
    n = 300
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    df = pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
            "target_bin": (x1 + x2 + rng.normal(0, 0.5, n) > 0).astype(int),
            "target_reg": 3 * x1 - 2 * x2 + rng.normal(0, 0.3, n),
        }
    )
    path = tmp_path / "ml.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_fold_other_keeps_small_sets_and_folds_large_ones():
    small = pd.Series(list("aabbcc"))
    assert OTHER_LABEL not in set(fold_other(small))
    large = pd.Series(list("abcdefghij") * 3)
    folded = fold_other(large)
    assert OTHER_LABEL in set(folded)
    assert folded.nunique() <= 8


def test_stacked_area_slope_facets(sales_csv):
    assert os.path.exists(
        composition.plot_stacked_bar(sales_csv, "region", "channel", y_column="revenue")
    )
    assert os.path.exists(
        composition.plot_area(sales_csv, "date", "revenue",
                              group_column="region", resample="W")
    )
    assert os.path.exists(
        composition.plot_slope(sales_csv, "region", "revenue", "period")
    )
    assert os.path.exists(
        composition.plot_small_multiples(sales_csv, "revenue", "region")
    )


def test_stacked_bar_folds_channel_levels(sales_csv):
    path = composition.plot_stacked_bar(sales_csv, "region", "channel")
    assert os.path.exists(path)


def test_ecdf_violin(sales_csv):
    assert os.path.exists(distribution.plot_ecdf(sales_csv, "revenue"))
    assert os.path.exists(
        distribution.plot_ecdf(sales_csv, "revenue", group_column="region")
    )
    assert os.path.exists(
        distribution.plot_violin(sales_csv, "revenue", by_column="region")
    )


def test_missingness_reports_and_plots(sales_csv):
    result = distribution.plot_missingness(sales_csv)
    assert result["columns_with_missing"] == 1
    assert "with_nan" in result["missing_pct"]
    assert os.path.exists(result["plot_path"])


def test_missingness_clean_data(tmp_path):
    path = tmp_path / "clean.csv"
    pd.DataFrame({"a": [1, 2, 3]}).to_csv(path, index=False)
    result = distribution.plot_missingness(str(path))
    assert result["plot_path"] is None


def test_stat_tile(sales_csv):
    result = distribution.stat_tile(sales_csv, "revenue", agg="mean",
                                    compare_agg="median")
    assert result["value"] > 0
    assert result["compare_value"] > 0
    assert os.path.exists(result["plot_path"])


def test_roc_pr_and_calibration(ml_csv):
    roc = ml.plot_roc_pr(ml_csv, "target_bin", feature_columns=["x1", "x2"])
    (label,) = roc["scores"]
    assert roc["scores"][label]["roc_auc"] > 0.7
    assert os.path.exists(roc["plot_path"])

    cal = ml.plot_calibration(ml_csv, "target_bin", feature_columns=["x1", "x2"])
    assert 0 <= cal["mean_calibration_gap"] <= 1
    assert os.path.exists(cal["plot_path"])


def test_roc_rejects_regression_target(ml_csv):
    with pytest.raises(ValueError, match="classification"):
        ml.plot_roc_pr(ml_csv, "target_reg", feature_columns=["x1", "x2"])


def test_feature_importance_and_residuals(ml_csv):
    imp = ml.plot_feature_importance(ml_csv, "target_reg",
                                     feature_columns=["x1", "x2"])
    assert set(imp["importances"]) == {"x1", "x2"}
    assert os.path.exists(imp["plot_path"])

    res = ml.plot_residuals(ml_csv, "target_reg", feature_columns=["x1", "x2"])
    assert abs(res["mean_residual"]) < 1.0
    assert os.path.exists(res["plot_path"])


def test_residuals_rejects_classification_target(ml_csv):
    with pytest.raises(ValueError, match="regression"):
        ml.plot_residuals(ml_csv, "target_bin", feature_columns=["x1", "x2"])

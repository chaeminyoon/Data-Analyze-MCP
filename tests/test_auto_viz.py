"""Column role classification, recommendations and plot_auto dispatch."""
import os

import numpy as np
import pandas as pd
import pytest

from data_analysis.helpers import classify_columns
from data_analysis.tools import auto_viz as av


def test_classify_columns_roles(tmp_path):
    n = 100
    df = pd.DataFrame(
        {
            "value": np.random.RandomState(0).normal(0, 1, n),
            "level": np.random.RandomState(1).choice([1, 2, 3], n),
            "city": np.random.RandomState(2).choice(["서울", "부산"], n),
            "when": pd.date_range("2024-01-01", periods=n).strftime("%Y-%m-%d"),
            "user_id": [f"u{i}" for i in range(n)],
            "note": [f"free text {i} " + "x" * (i % 37) for i in range(n)],
            "fixed": ["same"] * n,
        }
    )
    roles = {c: i["role"] for c, i in classify_columns(df).items()}
    assert roles["value"] == "numeric"
    assert roles["level"] == "discrete"
    assert roles["city"] == "categorical"
    assert roles["when"] == "datetime"
    assert roles["user_id"] == "id"
    assert roles["fixed"] == "constant"


def test_numeric_strings_are_not_dates():
    df = pd.DataFrame({"n": ["10", "20", "30"] * 20})
    assert classify_columns(df)["n"]["role"] != "datetime"


def test_recommendations_prefer_timeseries(timeseries_csv):
    rec = av.recommend_visualizations(timeseries_csv)
    assert rec["recommendations"][0]["chart"] == "line"
    assert rec["recommendations"][0]["columns"][0] == "date"


def test_recommendations_target_aware(churn_csv):
    rec = av.recommend_visualizations(churn_csv, target_column="churn")
    assert rec["recommendations"][0]["chart"] == "target_distribution"
    # every recommendation ships an executable tool_call
    for r in rec["recommendations"]:
        assert "tool" in r["tool_call"] and "csv_path" in r["tool_call"]["params"]


@pytest.mark.parametrize(
    ("columns", "chart"),
    [
        (["price"], "histogram"),
        (["aircon"], "bar"),
        (["area", "price"], "scatter"),
        (["price", "aircon"], "boxplot"),
        (["aircon", "bedrooms"], "crosstab_heatmap"),
        (["area", "price", "aircon"], "scatter"),
    ],
)
def test_plot_auto_dispatch(house_csv, columns, chart):
    result = av.plot_auto(house_csv, columns)
    assert result["chart"] == chart
    assert os.path.exists(result["output_path"])


def test_plot_auto_datetime_line(timeseries_csv):
    result = av.plot_auto(timeseries_csv, ["date", "sales", "store"])
    assert result["chart"] == "line"
    assert os.path.exists(result["output_path"])


def test_plot_auto_no_columns_uses_top_recommendation(timeseries_csv):
    result = av.plot_auto(timeseries_csv)
    assert result["chart"] == "line"
    assert "reason" in result and "alternatives" in result


def test_plot_auto_rejects_unplottable(tmp_path):
    path = tmp_path / "ids.csv"
    pd.DataFrame({"user_id": range(50)}).to_csv(path, index=False)
    with pytest.raises(ValueError):
        av.plot_auto(str(path), ["user_id"])

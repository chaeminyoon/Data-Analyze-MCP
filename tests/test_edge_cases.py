"""Hostile inputs must be handled or rejected with a clean ValueError — never crash."""
import numpy as np
import pandas as pd
import pytest

from data_analysis.tools import exploration as ex
from data_analysis.tools import ml
from data_analysis.tools import preprocessing as pp
from data_analysis.tools import statistics as st


def _csv(tmp_path, name, df):
    path = tmp_path / name
    df.to_csv(path, index=False)
    return str(path)


def test_empty_frame(tmp_path):
    path = _csv(tmp_path, "empty.csv", pd.DataFrame({"a": [], "b": []}))
    info = ex.get_dataset_info(path)
    assert info["shape"][0] == 0
    profile = ex.profile_dataset(path)
    assert profile["missing_summary"]["missing_percentage"] == 0.0


def test_all_nan_and_constant_columns(tmp_path):
    path = _csv(
        tmp_path, "nan.csv",
        pd.DataFrame({"x": [np.nan] * 20, "k": [7.0] * 20, "y": np.random.rand(20)}),
    )
    assert isinstance(pp.handle_missing_values(path), dict)
    assert isinstance(pp.scale_features(path, ["k"]), dict)  # zero variance ok


def test_single_class_target_clean_error(tmp_path):
    path = _csv(
        tmp_path, "oneclass.csv",
        pd.DataFrame({"f": np.random.rand(40), "target": ["yes"] * 40}),
    )
    with pytest.raises(ValueError):
        ml.compare_models(path, "target", ["f"])


def test_tiny_samples_clean_errors(tmp_path):
    path = _csv(tmp_path, "tiny.csv", pd.DataFrame({"x": [5.0], "g": ["a"]}))
    with pytest.raises(ValueError, match="at least 3 samples"):
        st.test_normality(path, "x")
    with pytest.raises(ValueError, match="at least 2 samples"):
        st.calculate_confidence_interval(path, "x")


def test_korean_columns_full_flow(tmp_path):
    rng = np.random.RandomState(3)
    path = _csv(
        tmp_path, "korean.csv",
        pd.DataFrame(
            {
                "나이": rng.randint(20, 60, 60),
                "지역": rng.choice(["서울", "부산", "대전"], 60),
                "매출": rng.rand(60) * 100,
            }
        ),
    )
    assert ex.profile_dataset(path)["shape"] == (60, 3)
    anova = st.test_anova(path, "매출", "지역")
    assert anova["num_groups"] == 3

    from data_analysis.tools import auto_viz as av

    result = av.plot_auto(path, ["매출", "지역"])
    assert result["chart"] == "boxplot"


def test_missing_file_and_missing_column(tmp_path, house_csv):
    with pytest.raises(FileNotFoundError):
        ex.get_dataset_info(str(tmp_path / "nope.csv"))
    with pytest.raises(ValueError, match="not found"):
        pp.detect_outliers(house_csv, "ghost")

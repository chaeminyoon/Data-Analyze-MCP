"""Shared fixtures: isolated output dir, clean cache/theme, synthetic datasets."""
import os

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from data_analysis import cache, config, theming


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test gets its own output dir, an empty cache and the default theme."""
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "outputs")
    cache.clear()
    theming.apply("modern")
    yield
    cache.clear()
    theming.apply("modern")


def _write(tmp_path, name, df):
    path = tmp_path / name
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def house_csv(tmp_path):
    """Regression-style dataset: numeric target with >100 injected outliers."""
    rng = np.random.RandomState(0)
    n = 2000
    df = pd.DataFrame(
        {
            "area": rng.normal(2000, 400, n).round(0),
            "price": rng.normal(500_000, 60_000, n).round(0),
            "bedrooms": rng.choice([1, 2, 3, 4], n),
            "aircon": rng.choice(["yes", "no"], n),
        }
    )
    df.loc[:119, "price"] = 10_000_000  # 120 extreme outliers (> old 100-row cap)
    df["price"] = df["price"] + df["area"] * 200  # real area-price signal
    return _write(tmp_path, "house.csv", df)


@pytest.fixture
def churn_csv(tmp_path):
    """Classification dataset with a string target and categorical features."""
    rng = np.random.RandomState(1)
    n = 400
    tenure = rng.randint(0, 72, n)
    contract = rng.choice(["Monthly", "Yearly"], n)
    charges = rng.normal(70, 15, n) + (contract == "Monthly") * 10
    churn = np.where(
        rng.random(n) < 1 / (1 + np.exp(-((tenure < 12) * 1.5 - 0.5))), "Yes", "No"
    )
    df = pd.DataFrame(
        {
            "tenure": tenure,
            "contract": contract,
            "charges": charges.round(2),
            "churn": churn,
        }
    )
    df.loc[:9, "charges"] = np.nan  # some missing values
    return _write(tmp_path, "churn.csv", df)


@pytest.fixture
def timeseries_csv(tmp_path):
    """Datetime + numeric + categorical, for line-chart / role detection."""
    dates = pd.date_range("2024-01-01", periods=180, freq="D")
    rng = np.random.RandomState(2)
    df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "sales": (1000 + np.arange(180) * 3 + rng.normal(0, 50, 180)).round(0),
            "store": rng.choice(["A", "B"], 180),
        }
    )
    return _write(tmp_path, "sales.csv", df)

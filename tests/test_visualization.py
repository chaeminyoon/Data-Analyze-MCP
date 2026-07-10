"""Chart tools produce files; theme + filename regressions stay fixed."""
import os

import matplotlib.pyplot as plt
import pytest

from data_analysis import theming
from data_analysis.tools import preprocessing as pp
from data_analysis.tools import visualization as vz


def test_basic_charts_create_files(house_csv):
    for path in (
        vz.plot_histogram(house_csv, "price"),
        vz.plot_boxplot(house_csv, "price", by_column="bedrooms"),
        vz.plot_scatter(house_csv, "area", "price", hue_column="aircon"),
        vz.plot_correlation_heatmap(house_csv),
        vz.plot_bar(house_csv, "aircon"),
    ):
        assert os.path.exists(path), path


def test_line_chart_grouped_filename_regression(timeseries_csv):
    """Regression: grouped line used to overwrite the ungrouped chart."""
    plain = vz.plot_line(timeseries_csv, "date", "sales")
    grouped = vz.plot_line(timeseries_csv, "date", "sales", group_column="store")
    assert plain != grouped
    assert os.path.exists(plain) and os.path.exists(grouped)


def test_line_resample_converts_string_dates(timeseries_csv):
    """Regression: pandas 3 'str' dtype broke the dtype==object date check."""
    path = vz.plot_line(timeseries_csv, "date", "sales", resample="ME", agg="sum")
    assert os.path.exists(path)


def test_before_after_histogram_and_boxplot(house_csv):
    """Regression: tight_layout(rect) crashed on sharey boxplot axes (mpl 3.11)."""
    pp.remove_outliers(house_csv, "price")
    hist = vz.plot_before_after(house_csv, "price")
    box = vz.plot_before_after(house_csv, "price", chart="boxplot")
    assert os.path.exists(hist) and os.path.exists(box)
    with pytest.raises(ValueError, match="histogram"):
        vz.plot_before_after(house_csv, "price", chart="pie")


def test_interactive_charts_create_html(house_csv):
    for path in (
        vz.plot_interactive_scatter(house_csv, "area", "price"),
        vz.plot_line(house_csv, "area", "price", interactive=True),
        vz.plot_bar(house_csv, "aircon", interactive=True),
    ):
        assert path.endswith(".html") and os.path.exists(path)


def test_theme_switch_changes_rcparams():
    theming.apply("dark")
    assert plt.rcParams["figure.facecolor"] == "#161a20"
    assert theming.current() == "dark"
    theming.apply("modern")
    assert plt.rcParams["figure.facecolor"] == "#ffffff"
    with pytest.raises(ValueError, match="Unknown chart style"):
        theming.apply("nope")


def test_no_figure_leak_on_error(house_csv):
    before = plt.get_fignums()
    with pytest.raises(ValueError):
        vz.plot_histogram(house_csv, "no_such_column")
    assert plt.get_fignums() == before

"""Tool registration, cache management and result-viewing tools."""
import asyncio

from mcp.server.fastmcp import Image

from data_analysis import prompts, tools  # noqa: F401  (registers everything)
from data_analysis.server import mcp
from data_analysis.tools import exploration as ex
from data_analysis.tools import results as rs
from data_analysis.tools import style as sty
from data_analysis.tools import visualization as vz

EXPECTED_TOOL_COUNT = 41


def test_all_tools_registered():
    registered = asyncio.run(mcp.list_tools())
    names = {t.name for t in registered}
    assert len(registered) == EXPECTED_TOOL_COUNT
    for key in (
        "plot_auto", "recommend_visualizations", "plot_before_after",
        "set_chart_style", "view_chart", "list_outputs", "compare_models",
    ):
        assert key in names


def test_cache_management(house_csv):
    ex.get_dataset_info(house_csv)
    listed = ex.list_cached_datasets()
    assert listed["count"] == 1
    assert "cleared" in ex.clear_cache().lower()
    assert ex.list_cached_datasets()["count"] == 0


def test_view_chart_returns_image(house_csv):
    path = vz.plot_histogram(house_csv, "price")
    image = rs.view_chart(path)
    assert isinstance(image, Image)


def test_view_chart_guides_on_html_and_missing(house_csv):
    html = vz.plot_line(house_csv, "area", "price", interactive=True)
    try:
        rs.view_chart(html)
        raise AssertionError("expected ValueError for html")
    except ValueError as exc:
        assert "browser" in str(exc) or "브라우저" in str(exc) or ".html" in str(exc)

    try:
        rs.view_chart("ghost.png")
        raise AssertionError("expected ValueError for missing file")
    except ValueError as exc:
        assert "not found" in str(exc)


def test_list_outputs_newest_first(house_csv):
    vz.plot_histogram(house_csv, "price")
    vz.plot_histogram(house_csv, "area")
    outputs = rs.list_outputs()
    assert outputs["count"] >= 2
    assert outputs["files"][0]["viewable_inline"] is True


def test_style_tools_roundtrip():
    styles = sty.list_chart_styles()
    assert styles["current"] == "modern"
    assert set(styles["available"]) == {"modern", "dark", "minimal", "vibrant", "classic"}

    switched = sty.set_chart_style("minimal")
    assert switched["style"] == "minimal"
    assert sty.list_chart_styles()["current"] == "minimal"

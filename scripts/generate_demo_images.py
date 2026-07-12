"""Regenerate every README demo image from the bundled demo datasets.

Run from the repo root (after ``python generate_all_test_data.py``):

    MCP_OUTPUT_DIR=outputs python scripts/generate_demo_images.py

Each image is the unedited output of an actual MCP tool call, so the README
demos never drift from what the server really draws. The showcase panel is a
2×2 montage spanning four themes and four chart forms.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

WORK = Path(tempfile.mkdtemp(prefix="demo_images_"))
os.environ["MCP_OUTPUT_DIR"] = str(WORK)

from data_analysis import theming  # noqa: E402
from data_analysis.tools import (  # noqa: E402
    auto_viz,
    composition,
    distribution,
    preprocessing,
    visualization,
)

IMAGES = ROOT / "docs" / "images"
HOUSE = str(ROOT / "house_price.csv")
SALES = str(ROOT / "sales_timeseries.csv")
CHURN = str(ROOT / "customer_churn.csv")

for f in (HOUSE, SALES, CHURN):
    if not Path(f).exists():
        sys.exit(f"Missing {f} — run `python generate_all_test_data.py` first.")


def ship(src: str, name: str) -> None:
    shutil.copy(src, IMAGES / name)
    print(f"  {name}")


print("Rendering demo images (unedited tool outputs)...")

# 1. Before/after: the README's outlier-removal walkthrough on house prices.
theming.apply("modern")
preprocessing.detect_outliers(HOUSE, "price")
preprocessing.remove_outliers(HOUSE, "price")
ship(visualization.plot_before_after(HOUSE, "price"), "demo_before_after.png")

# 2. Scatter after cleaning — area vs price colored by bedrooms.
ship(
    visualization.plot_scatter(
        HOUSE, "area", "price", hue_column="bedrooms",
        title="Area vs Price (after outlier removal)",
    ),
    "demo_scatter.png",
)

# 3. Time series line with weekly resampling.
ship(
    visualization.plot_line(SALES, "date", "sales", resample="W",
                            title="Weekly sales"),
    "demo_timeseries.png",
)

# 4. Crosstab heatmap via plot_auto (two categoricals).
ship(
    auto_viz.plot_auto(CHURN, columns=["contract_type", "payment_method"])[
        "output_path"
    ],
    "demo_crosstab.png",
)

# 5-7. Theme demos — a different validated palette per theme.
theming.apply("dark")
ship(
    composition.plot_stacked_bar(
        CHURN, "contract_type", "internet_service", title="Contracts by internet service",
    ),
    "demo_dark.png",
)
theming.apply("minimal")
ship(
    distribution.plot_ecdf(HOUSE, "price", group_column="furnishingstatus",
                           title="Price ECDF by furnishing"),
    "demo_minimal.png",
)
theming.apply("vibrant")
ship(
    distribution.plot_violin(CHURN, "monthly_charges", by_column="contract_type",
                             title="Monthly charges by contract"),
    "demo_vibrant.png",
)

# 8. Showcase montage: four forms × four themes in one strip.
from PIL import Image  # noqa: E402

theming.apply("modern")
panel_a = visualization.plot_scatter(
    HOUSE, "area", "price", hue_column="bedrooms", title="modern — scatter",
)
theming.apply("dark")
panel_b = composition.plot_stacked_bar(
    CHURN, "contract_type", "internet_service", title="dark — stacked bar",
)
theming.apply("minimal")
panel_c = distribution.plot_ecdf(
    HOUSE, "price", group_column="furnishingstatus", title="minimal — ECDF",
)
theming.apply("vibrant")
panel_d = composition.plot_area(
    SALES, "date", "sales", group_column="product_id", resample="ME",
    title="vibrant — stacked area",
)

cells = [Image.open(p) for p in (panel_a, panel_b, panel_c, panel_d)]
w = min(im.width for im in cells)
cells = [im.resize((w, int(im.height * w / im.width)), Image.LANCZOS) for im in cells]
gap = 16
row_h = [max(cells[i].height for i in pair) for pair in ((0, 1), (2, 3))]
canvas = Image.new("RGB", (2 * w + gap, sum(row_h) + gap), "#ffffff")
canvas.paste(cells[0], (0, 0))
canvas.paste(cells[1], (w + gap, 0))
canvas.paste(cells[2], (0, row_h[0] + gap))
canvas.paste(cells[3], (w + gap, row_h[0] + gap))
canvas.save(IMAGES / "showcase.png", optimize=True)
print("  showcase.png")

theming.apply("modern")
print(f"\nDone → {IMAGES}")

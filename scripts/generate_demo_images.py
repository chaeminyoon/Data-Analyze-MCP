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

# 8. Showcase hero — a typeset board: title row + four captioned panels.
#    Every panel is still an unedited tool output; only the framing is set.
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import shutil as _shutil  # noqa: E402

theming.apply("modern")
panel_a = _shutil.copy(
    visualization.plot_scatter(
        HOUSE, "area", "price", hue_column="bedrooms",
        title="주택 면적 vs 가격 — 침실 수는 시퀀셜 램프",
    ),
    WORK / "_panel_a.png",
)
theming.apply("dark")
panel_b = _shutil.copy(
    composition.plot_stacked_bar(
        CHURN, "contract_type", "internet_service",
        title="계약 유형별 인터넷 서비스 구성",
    ),
    WORK / "_panel_b.png",
)
theming.apply("minimal")
panel_c = _shutil.copy(
    distribution.plot_ecdf(
        HOUSE, "price", group_column="furnishingstatus",
        title="가구 상태별 가격 누적분포",
    ),
    WORK / "_panel_c.png",
)
theming.apply("vibrant")
panel_d = _shutil.copy(
    composition.plot_area(
        SALES, "date", "sales", group_column="product_id", resample="ME",
        title="제품별 월간 매출 구성",
    ),
    WORK / "_panel_d.png",
)
theming.apply("modern")

PANELS = [
    (panel_a, "modern (기본)", "자동 추천 산점도 — 순서형 hue는 한 색상의 명도로"),
    (panel_b, "dark", "set_chart_style 한 번으로 다크 전용 팔레트 전환"),
    (panel_c, "minimal", "보고서용 뮤트 톤 — ECDF로 정확한 백분위"),
    (panel_d, "vibrant", "발표용 고채도 — 스택 영역으로 구성 변화"),
]

fig = plt.figure(figsize=(16, 11.6), facecolor="#ffffff")
gs = fig.add_gridspec(2, 2, left=0.015, right=0.985, top=0.845, bottom=0.015,
                      wspace=0.05, hspace=0.17)
for (path, theme, caption), pos in zip(PANELS, [gs[0, 0], gs[0, 1], gs[1, 0], gs[1, 1]]):
    ax = fig.add_subplot(pos)
    ax.imshow(mpimg.imread(path))
    ax.axis("off")
    ax.set_title(f"{theme}  ·  {caption}", fontsize=12.5, color="#3a4553",
                 loc="left", pad=8)
fig.text(0.015, 0.955, "Data-Analyze-MCP", fontsize=24, fontweight="bold",
         color="#2a78d6", ha="left")
fig.text(0.015, 0.905,
         "자연어 한 마디 → 분석·전처리·시각화  ·  60개 MCP 도구  ·  접근성 검증 팔레트 4종 (CVD 시뮬레이션 · 대비 3:1 · CI 강제)",
         fontsize=13, color="#52514e", ha="left")
fig.text(0.985, 0.955, "모든 패널은 무편집 도구 출력", fontsize=11,
         color="#8b96a5", ha="right")
fig.savefig(IMAGES / "showcase.png", dpi=110, facecolor="#ffffff",
            bbox_inches="tight")
plt.close(fig)
print("  showcase.png")

theming.apply("modern")
print(f"\nDone → {IMAGES}")

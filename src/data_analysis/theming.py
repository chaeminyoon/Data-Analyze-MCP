"""Chart theme system — polished presets applied across matplotlib/seaborn/plotly.

Every chart tool draws through the active theme, so switching the theme
changes the look of everything (colors, grid, spines, typography) without
touching individual tool calls. The default is ``modern``; set the
``MCP_CHART_THEME`` env var or call the ``set_chart_style`` tool to switch.
"""
from cycler import cycler

import matplotlib.pyplot as plt
import seaborn as sns

_BASE_LIGHT = {
    "figure.facecolor": "#ffffff",
    "savefig.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.titleweight": "bold",
    "axes.titlesize": 13,
    "axes.titlepad": 12,
    "axes.titlelocation": "left",
    "axes.labelsize": 10.5,
    "axes.labelcolor": "#3a4553",
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "xtick.color": "#5c6b7a",
    "ytick.color": "#5c6b7a",
    "legend.frameon": False,
    "legend.fontsize": 9.5,
    "lines.linewidth": 2.0,
    "lines.markersize": 7,
}

# Every palette below (except ``classic``) passes the four accessibility
# checks in ``palette_check`` on its own surface: OKLCH lightness band,
# chroma floor (>= 0.1), adjacent-pair CVD separation (ΔE >= 12 under
# protan/deutan/tritan simulation), and WCAG contrast >= 3:1. The slot
# ORDER is part of the safety mechanism — it was chosen by exhaustive
# search to maximize the minimum adjacent-pair CVD distance, so series
# that appear next to each other stay distinguishable. Don't reorder or
# swap hues casually; run ``pytest tests/test_palettes.py`` after edits.
THEMES = {
    "modern": {
        "description": "차분한 전문가 팔레트, 옅은 그리드, 좌측 정렬 볼드 타이틀 (기본값, 접근성 검증 통과)",
        "palette": ["#2a78d6", "#e34948", "#4a3aa7", "#008300", "#c4497c",
                    "#b07c00", "#12946a", "#eb6834"],
        "plotly_template": "plotly_white",
        "sequential_cmap": "Blues",
        "diverging_cmap": "RdBu_r",
        "rc": {
            **_BASE_LIGHT,
            "axes.edgecolor": "#d0d5db",
            "axes.grid": True,
            "grid.color": "#e9ecf0",
            "grid.linewidth": 0.9,
        },
    },
    "dark": {
        "description": "다크 배경 팔레트 — 대시보드/발표용 (접근성 검증 통과)",
        "palette": ["#3987e5", "#e66767", "#c98500", "#199e70", "#d95926",
                    "#9085e9", "#2e9e2e", "#d55181"],
        "plotly_template": "plotly_dark",
        "sequential_cmap": "Blues",
        "diverging_cmap": "RdBu_r",
        "rc": {
            **_BASE_LIGHT,
            "figure.facecolor": "#161a20",
            "savefig.facecolor": "#161a20",
            "axes.facecolor": "#161a20",
            "axes.edgecolor": "#3a424d",
            "axes.grid": True,
            "grid.color": "#262c35",
            "grid.linewidth": 0.9,
            "text.color": "#e8ecf1",
            "axes.labelcolor": "#aab4c0",
            "xtick.color": "#8b96a5",
            "ytick.color": "#8b96a5",
        },
    },
    "minimal": {
        "description": "뮤트 톤 팔레트, 그리드 최소화 — 보고서/논문용 (접근성 검증 통과)",
        "palette": ["#3f6ea6", "#9a6a14", "#0a83ad", "#ad4a5e", "#6f60b8",
                    "#238a3e"],
        "plotly_template": "simple_white",
        "sequential_cmap": "Blues",
        "diverging_cmap": "RdBu_r",
        "rc": {
            **_BASE_LIGHT,
            "axes.edgecolor": "#c3cad3",
            "axes.linewidth": 0.8,
            "axes.grid": False,
            "axes.titlelocation": "left",
        },
    },
    "vibrant": {
        "description": "고채도 팔레트, 강한 대비 — 프레젠테이션 강조용 (접근성 검증 통과)",
        "palette": ["#d81e5b", "#0f7fd4", "#e05206", "#425bd1", "#b26a00",
                    "#00926e", "#6a35c8", "#3d8f00"],
        "plotly_template": "plotly_white",
        "sequential_cmap": "Blues",
        "diverging_cmap": "RdBu_r",
        "rc": {
            **_BASE_LIGHT,
            "axes.edgecolor": "#b9c0c8",
            "axes.grid": True,
            "grid.color": "#eef1f4",
            "grid.linewidth": 1.0,
            "axes.titlesize": 14,
            "axes.titlelocation": "center",
        },
    },
    "classic": {
        "description": "matplotlib/plotly 기본 스타일 (레거시 호환용 — 접근성 미검증)",
        "palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
        "plotly_template": "plotly",
        "sequential_cmap": "Blues",
        "diverging_cmap": "RdBu_r",
        "rc": {},
    },
}

_current = "modern"


def available() -> dict:
    """Theme name -> description."""
    return {name: spec["description"] for name, spec in THEMES.items()}


def current() -> str:
    return _current


def palette() -> list[str]:
    return list(THEMES[_current]["palette"])


def face_color() -> str:
    """The active figure background color (used e.g. for histogram bar edges)."""
    return plt.rcParams.get("figure.facecolor", "#ffffff")


def plotly_template() -> str:
    return THEMES[_current]["plotly_template"]


def sequential_cmap() -> str:
    """One-hue light→dark colormap for continuous magnitude."""
    return THEMES[_current]["sequential_cmap"]


def diverging_cmap() -> str:
    """Two-hue + neutral-midpoint colormap for signed values (e.g. correlation)."""
    return THEMES[_current]["diverging_cmap"]


def is_dark() -> bool:
    return _current == "dark"


def plotly_kwargs() -> dict:
    """Keyword args for plotly express calls with discrete colors."""
    return {"template": plotly_template(), "color_discrete_sequence": palette()}


def apply(name: str) -> None:
    """Activate a theme globally (matplotlib rc + seaborn palette)."""
    global _current
    if name not in THEMES:
        raise ValueError(f"Unknown chart style '{name}'. Available: {list(THEMES)}")

    # Reset to defaults first so switching themes never leaks settings,
    # then restore the Korean font config on top.
    plt.rcdefaults()
    from . import fonts

    fonts.configure()

    spec = THEMES[name]
    rc = dict(spec["rc"])
    rc["axes.prop_cycle"] = cycler(color=spec["palette"])
    plt.rcParams.update(rc)
    sns.set_palette(spec["palette"])
    _current = name

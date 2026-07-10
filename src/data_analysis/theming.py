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
}

THEMES = {
    "modern": {
        "description": "차분한 전문가 팔레트, 옅은 그리드, 좌측 정렬 볼드 타이틀 (기본값)",
        "palette": ["#3d6fb6", "#e8853d", "#43a57c", "#d95b5b", "#8a6fc8",
                    "#3fa9bc", "#c9a227", "#77808c"],
        "plotly_template": "plotly_white",
        "rc": {
            **_BASE_LIGHT,
            "axes.edgecolor": "#d0d5db",
            "axes.grid": True,
            "grid.color": "#e9ecf0",
            "grid.linewidth": 0.9,
        },
    },
    "dark": {
        "description": "다크 배경 + 밝은 파스텔 팔레트 — 대시보드/발표용",
        "palette": ["#6ea8e8", "#f2a65e", "#5bc895", "#f07878", "#b195e8",
                    "#5fc8dc", "#e8c25a", "#9aa5b5"],
        "plotly_template": "plotly_dark",
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
        "description": "단일 액센트 + 그레이스케일, 그리드 최소화 — 보고서/논문용",
        "palette": ["#3d6fb6", "#8b96a5", "#5c6b7a", "#c3cad3", "#2b3440", "#a9b2bd"],
        "plotly_template": "simple_white",
        "rc": {
            **_BASE_LIGHT,
            "axes.edgecolor": "#c3cad3",
            "axes.linewidth": 0.8,
            "axes.grid": False,
            "axes.titlelocation": "left",
        },
    },
    "vibrant": {
        "description": "고채도 팔레트, 강한 대비 — 프레젠테이션 강조용",
        "palette": ["#ff595e", "#1982c4", "#8ac926", "#ffca3a", "#6a4c93",
                    "#36bfb1", "#ff7bac", "#4267ac"],
        "plotly_template": "plotly_white",
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
        "description": "matplotlib/plotly 기본 스타일 (기존 형태)",
        "palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
        "plotly_template": "plotly",
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

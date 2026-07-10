"""Automatic visualization: recommend the right chart for ANY dataset, then render it.

Two tools:

- ``recommend_visualizations`` inspects column roles (numeric / discrete /
  categorical / datetime / id / text ...) and returns a ranked list of chart
  recommendations, each with a ready-to-call ``tool_call``.
- ``plot_auto`` renders a chart for a given column combination (or, with no
  columns, the top recommendation) by dispatching to the concrete plot tools.
"""
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns

from .. import theming
from ..cache import get_data
from ..helpers import classify_columns, output_path, require_columns, safe_name, save_current_figure
from ..server import mcp
from . import visualization as vz

# Roles that cannot be charted directly.
_UNPLOTTABLE = ("id", "text", "constant", "empty")
# Max category levels for grouping/hue to keep charts readable.
_MAX_GROUP_LEVELS = 12


def _measures(roles: dict) -> list[str]:
    """Numeric columns worth plotting as values (continuous first, then discrete)."""
    numeric = [c for c, i in roles.items() if i["role"] == "numeric"]
    discrete = [c for c, i in roles.items() if i["role"] == "discrete" and i["nunique"] > 2]
    return numeric + discrete


def _low_cats(roles: dict) -> list[str]:
    """Categorical/discrete columns with few enough levels to group by."""
    return [
        c
        for c, i in roles.items()
        if i["role"] in ("categorical", "discrete") and i["nunique"] <= _MAX_GROUP_LEVELS
    ]


def _build_recommendations(csv_path, df, roles, target_column=None, limit=8):
    """Return (ranked recommendation list, skipped-column notes)."""
    recs = []

    def add(chart, cols, reason, tool, params):
        if any(r["chart"] == chart and r["columns"] == cols for r in recs):
            return
        recs.append(
            {
                "chart": chart,
                "columns": cols,
                "reason": reason,
                "tool_call": {"tool": tool, "params": {"csv_path": csv_path, **params}},
            }
        )

    numeric = [c for c, i in roles.items() if i["role"] == "numeric"]
    measures = _measures(roles)
    lowcat = _low_cats(roles)
    hicard = [c for c, i in roles.items() if i["role"] == "high_cardinality"]
    dts = [c for c, i in roles.items() if i["role"] == "datetime"]

    # Target-aware charts come first when a target is named.
    if target_column and target_column in roles:
        add(
            "target_distribution", [target_column],
            f"Class balance of target '{target_column}' — checks for imbalance before modeling",
            "analyze_target_distribution", {"target_column": target_column},
        )
        if numeric and roles[target_column]["role"] in ("categorical", "discrete"):
            add(
                "boxplot", [numeric[0], target_column],
                f"How '{numeric[0]}' differs across '{target_column}' classes",
                "plot_boxplot", {"column": numeric[0], "by_column": target_column},
            )

    # Time series: a datetime column is the strongest signal for chart choice.
    if dts and measures:
        x, y = dts[0], measures[0]
        add(
            "line", [x, y],
            f"'{x}' is temporal — a line chart shows the trend of '{y}' over time",
            "plot_line", {"x_column": x, "y_column": y},
        )
        if lowcat:
            add(
                "line", [x, y, lowcat[0]],
                f"Trend of '{y}' over '{x}', one line per '{lowcat[0]}' group",
                "plot_line", {"x_column": x, "y_column": y, "group_column": lowcat[0]},
            )

    # Relationships between numeric columns.
    if len(numeric) >= 3:
        add(
            "correlation_heatmap", numeric,
            f"{len(numeric)} numeric columns — heatmap reveals which variables move together",
            "plot_correlation_heatmap", {},
        )
    if len(numeric) >= 2:
        corr = df[numeric].corr().abs()
        best, best_v = None, -1.0
        for i in range(len(numeric)):
            for j in range(i + 1, len(numeric)):
                v = corr.iloc[i, j]
                if pd.notna(v) and v > best_v:
                    best_v, best = float(v), (numeric[i], numeric[j])
        if best:
            params = {"x_column": best[0], "y_column": best[1]}
            cols = list(best)
            if lowcat:
                params["hue_column"] = lowcat[0]
                cols.append(lowcat[0])
            add(
                "scatter", cols,
                f"Strongest numeric relationship (|r|={best_v:.2f}): '{best[0]}' vs '{best[1]}'",
                "plot_scatter", params,
            )

    # A measure split by a category.
    if measures and lowcat:
        by = lowcat[0] if lowcat[0] != measures[0] else (lowcat[1] if len(lowcat) > 1 else None)
        if by:
            add(
                "boxplot", [measures[0], by],
                f"Compare '{measures[0]}' across '{by}' groups (medians, spread, outliers)",
                "plot_boxplot", {"column": measures[0], "by_column": by},
            )

    # Single-column distributions.
    for c in numeric[:2]:
        add(
            "histogram", [c],
            f"Distribution shape of '{c}' (skew, modes, outliers)",
            "plot_histogram", {"column": c},
        )
    cat_candidates = [c for c, i in roles.items() if i["role"] in ("categorical", "discrete")]
    for c in (cat_candidates + hicard)[:2]:
        note = " (top 20 shown)" if roles[c]["nunique"] > 20 else ""
        add("bar", [c], f"Frequency of each '{c}' category{note}", "plot_bar", {"column": c})

    # Two categoricals.
    if len(lowcat) >= 2:
        add(
            "crosstab_heatmap", lowcat[:2],
            f"Joint frequency of '{lowcat[0]}' × '{lowcat[1]}'",
            "plot_auto", {"columns": lowcat[:2]},
        )

    skipped = [
        {"column": c, "role": i["role"], "why": "identifier/free-text/constant — not chartable"}
        for c, i in roles.items()
        if i["role"] in _UNPLOTTABLE
    ]
    return recs[:limit], skipped


@mcp.tool()
def recommend_visualizations(
    csv_path: str, target_column: str = None, max_recommendations: int = 8
) -> dict:
    """Recommend suitable visualizations for ANY dataset.

    Classifies every column's role, then returns a ranked list of chart
    recommendations. Each recommendation includes a ``tool_call`` you can
    invoke directly, or pass its ``columns`` to ``plot_auto``.
    """
    df = get_data(csv_path)
    roles = classify_columns(df)
    recs, skipped = _build_recommendations(csv_path, df, roles, target_column, max_recommendations)
    return {
        "column_roles": {c: i["role"] for c, i in roles.items()},
        "recommendations": recs,
        "skipped_columns": skipped,
        "hint": "Render any recommendation via plot_auto(csv_path, columns=rec['columns'], "
        "interactive=True|False) or by calling rec['tool_call'] directly.",
    }


def _plot_crosstab(df, a, b, interactive, title):
    ct = pd.crosstab(df[a], df[b])
    chart_title = title or f"Counts: {a} × {b}"
    if interactive:
        fig = px.imshow(ct, text_auto=True, aspect="auto", title=chart_title,
                        template=theming.plotly_template())
        path = output_path(f"crosstab_{safe_name(a)}_{safe_name(b)}.html")
        fig.write_html(path)
        return path
    plt.figure(figsize=(10, 8))
    try:
        sns.heatmap(ct, annot=True, fmt="d", cmap="Blues")
        plt.title(chart_title)
        plt.xlabel(b)
        plt.ylabel(a)
        return save_current_figure(f"crosstab_{safe_name(a)}_{safe_name(b)}.png")
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


def _kind(role: str) -> str:
    """Collapse a role into a dispatch kind: num / cat / dt."""
    if role in ("numeric",):
        return "num"
    if role in ("discrete", "categorical", "high_cardinality"):
        return "cat"
    if role == "datetime":
        return "dt"
    return "bad"


def _dispatch(df, columns, roles):
    """Pick (chart, params) for an explicit column combination."""
    kinds = {c: _kind(roles[c]["role"]) for c in columns}
    # discrete numerics count as 'cat' above, but alone or against datetime
    # they behave like numbers, so patch those cases below where needed.
    nums = [c for c in columns if kinds[c] == "num"]
    cats = [c for c in columns if kinds[c] == "cat"]
    dts = [c for c in columns if kinds[c] == "dt"]
    discretes = [c for c in cats if roles[c]["role"] == "discrete"]

    if len(columns) == 1:
        c = columns[0]
        if kinds[c] == "num":
            return "histogram", {"column": c}
        if kinds[c] == "cat":
            return "bar", {"column": c}
        raise ValueError(
            f"A datetime column alone isn't chartable — pair '{c}' with a numeric column "
            "for a line chart."
        )

    if len(columns) == 2:
        if dts:
            y = (nums + discretes) or None
            if not y:
                raise ValueError(
                    "A datetime axis needs a numeric y column (got a categorical). "
                    "Pass e.g. columns=[datetime_col, numeric_col]."
                )
            return "line", {"x_column": dts[0], "y_column": y[0]}
        if len(nums) == 2:
            return "scatter", {"x_column": nums[0], "y_column": nums[1]}
        if len(nums) == 1 and len(cats) == 1:
            if roles[cats[0]]["nunique"] > _MAX_GROUP_LEVELS:
                return "bar", {"column": cats[0], "y_column": nums[0]}
            return "boxplot", {"column": nums[0], "by_column": cats[0]}
        if len(cats) == 2:
            return "crosstab_heatmap", {"columns": cats}

    if len(columns) == 3:
        group = [c for c in cats if roles[c]["nunique"] <= _MAX_GROUP_LEVELS]
        if dts and (nums or discretes) and group:
            y = (nums + [d for d in discretes if d != group[0]])[0]
            return "line", {"x_column": dts[0], "y_column": y, "group_column": group[0]}
        if len(nums) >= 2 and group:
            return "scatter", {"x_column": nums[0], "y_column": nums[1], "hue_column": group[0]}

    raise ValueError(
        f"No chart rule for this combination: { {c: roles[c]['role'] for c in columns} }. "
        "Try 1-3 columns mixing numeric/categorical/datetime."
    )


def _execute(csv_path, df, chart, params, interactive, title):
    """Render ``chart`` with the matching concrete tool and return its path."""
    if chart == "histogram":
        if interactive:
            return vz.plot_interactive_histogram(csv_path, params["column"], title=title)
        return vz.plot_histogram(csv_path, params["column"], title=title)
    if chart == "bar":
        return vz.plot_bar(
            csv_path, params["column"], y_column=params.get("y_column"),
            interactive=interactive, title=title,
        )
    if chart == "scatter":
        if interactive:
            return vz.plot_interactive_scatter(
                csv_path, params["x_column"], params["y_column"],
                color_column=params.get("hue_column"), title=title,
            )
        return vz.plot_scatter(
            csv_path, params["x_column"], params["y_column"],
            hue_column=params.get("hue_column"), title=title,
        )
    if chart == "boxplot":
        if interactive:
            return vz.plot_interactive_boxplot(
                csv_path, params["column"], x_column=params.get("by_column"), title=title
            )
        return vz.plot_boxplot(
            csv_path, params["column"], by_column=params.get("by_column"), title=title
        )
    if chart == "line":
        return vz.plot_line(
            csv_path, params["x_column"], params["y_column"],
            group_column=params.get("group_column"), interactive=interactive, title=title,
        )
    if chart == "correlation_heatmap":
        if interactive:
            return vz.plot_interactive_heatmap(csv_path, title=title)
        return vz.plot_correlation_heatmap(csv_path)
    if chart == "crosstab_heatmap":
        a, b = params["columns"]
        return _plot_crosstab(df, a, b, interactive, title)
    if chart == "target_distribution":
        return vz.analyze_target_distribution(csv_path, params["target_column"]).get("plot_path")
    raise ValueError(f"Unknown chart type: {chart}")


@mcp.tool()
def plot_auto(
    csv_path: str,
    columns: list = None,
    interactive: bool = False,
    title: str = None,
    target_column: str = None,
) -> dict:
    """Automatically pick and render the right chart for the given columns.

    With ``columns`` (1-3 names) the chart type is chosen by their roles:
    numeric→histogram, categorical→bar, numeric+numeric→scatter,
    numeric+categorical→boxplot, datetime+numeric→line,
    categorical+categorical→crosstab heatmap, +category as hue/group for a
    third column. With no ``columns``, the dataset's top recommendation is
    rendered. Set ``interactive=True`` for a Plotly HTML instead of PNG.
    """
    df = get_data(csv_path)
    roles = classify_columns(df)

    if not columns:
        recs, skipped = _build_recommendations(csv_path, df, roles, target_column)
        if not recs:
            raise ValueError(
                f"No chartable columns found. Skipped: {[s['column'] for s in skipped]}"
            )
        top = recs[0]
        chart = top["chart"]
        params = {k: v for k, v in top["tool_call"]["params"].items() if k != "csv_path"}
        if chart == "crosstab_heatmap":
            params = {"columns": top["columns"]}
        path = _execute(csv_path, df, chart, params, interactive, title)
        return {
            "chart": chart,
            "columns": top["columns"],
            "reason": top["reason"],
            "interactive": interactive,
            "output_path": path,
            "alternatives": recs[1:4],
        }

    require_columns(df, *columns)
    if len(columns) > 3:
        raise ValueError("plot_auto accepts at most 3 columns.")
    bad = {c: roles[c]["role"] for c in columns if roles[c]["role"] in _UNPLOTTABLE}
    if bad:
        raise ValueError(
            f"Not chartable (identifier/free-text/constant/empty): {bad}. "
            "Pick numeric, categorical or datetime columns."
        )

    chart, params = _dispatch(df, columns, roles)
    path = _execute(csv_path, df, chart, params, interactive, title)
    return {
        "chart": chart,
        "columns": columns,
        "column_roles": {c: roles[c]["role"] for c in columns},
        "interactive": interactive,
        "output_path": path,
    }

"""Composition & comparison charts: stacked bars, areas, slopes, small multiples.

Shared design rules: at most ``MAX_SERIES`` colored series — beyond that the
smallest levels fold into an "Other" bucket instead of cycling hues; stacked
segments are separated by a surface-colored gap; a legend is always present
for two or more series.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .. import theming
from ..cache import get_data
from ..helpers import (
    require_columns,
    require_numeric,
    safe_name,
    save_current_figure,
    style_bars,
)
from ..server import mcp

MAX_SERIES = 8
OTHER_LABEL = "Other"


def fold_other(series: pd.Series, max_levels: int = MAX_SERIES) -> pd.Series:
    """Keep the ``max_levels - 1`` largest levels, fold the rest into 'Other'.

    A 9th series never gets a new hue — identity beyond the palette folds.
    """
    counts = series.value_counts()
    if len(counts) <= max_levels:
        return series
    keep = set(counts.head(max_levels - 1).index)
    return series.where(series.isin(keep), OTHER_LABEL)


def _legend_outside(ax, title: str) -> None:
    ax.legend(title=title, bbox_to_anchor=(1.02, 1), loc="upper left")


@mcp.tool()
def plot_stacked_bar(
    csv_path: str,
    category_column: str,
    stack_column: str,
    y_column: str = None,
    agg: str = "sum",
    normalize: bool = False,
    top_n: int = 12,
    title: str = None,
    figsize_width: int = 11,
    figsize_height: int = 6,
) -> str:
    """Stacked bar chart: composition of ``stack_column`` within each category.

    Args:
        category_column: X-axis categories (largest ``top_n`` kept).
        stack_column: Segment identity; more than 8 levels fold into 'Other'.
        y_column: Optional numeric value; counts are used when omitted.
        agg: Aggregation for y_column (sum, mean, ...).
        normalize: True shows 100%-stacked shares instead of absolute values.
    """
    df = get_data(csv_path).copy()
    require_columns(df, category_column, stack_column, y_column)
    if y_column:
        require_numeric(df, y_column)

    df[stack_column] = fold_other(df[stack_column].astype(str))
    if y_column:
        table = df.pivot_table(
            index=category_column, columns=stack_column, values=y_column,
            aggfunc=agg, fill_value=0,
        )
    else:
        table = pd.crosstab(df[category_column], df[stack_column])

    table = table.loc[table.sum(axis=1).sort_values(ascending=False).index].head(top_n)
    if normalize:
        table = table.div(table.sum(axis=1), axis=0) * 100

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        ax = table.plot(kind="bar", stacked=True, ax=plt.gca(),
                        color=theming.palette()[: table.shape[1]])
        style_bars(ax)
        ylabel = ("Share (%)" if normalize
                  else (f"{agg}({y_column})" if y_column else "Count"))
        ax.set_ylabel(ylabel)
        ax.set_xlabel(category_column)
        ax.set_title(title or f"{ylabel} by {category_column}, stacked by {stack_column}")
        plt.xticks(rotation=45, ha="right")
        _legend_outside(ax, stack_column)
        suffix = "_pct" if normalize else ""
        return save_current_figure(
            f"stacked_{safe_name(category_column)}_by_{safe_name(stack_column)}{suffix}.png"
        )
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_area(
    csv_path: str,
    x_column: str,
    y_column: str,
    group_column: str = None,
    resample: str = None,
    agg: str = "sum",
    normalize: bool = False,
    title: str = None,
    figsize_width: int = 12,
    figsize_height: int = 6,
) -> str:
    """Stacked area chart: how a total and its composition evolve over time.

    Args:
        x_column: Time-like x-axis (date strings are auto-converted).
        group_column: Composition identity; >8 levels fold into 'Other'.
        resample: Optional pandas frequency ('D', 'W', 'M', ...).
        normalize: True shows 100%-stacked shares.
    """
    df = get_data(csv_path).copy()
    require_columns(df, x_column, y_column, group_column)
    require_numeric(df, y_column)

    if not pd.api.types.is_datetime64_any_dtype(df[x_column]) and not pd.api.types.is_numeric_dtype(df[x_column]):
        converted = pd.to_datetime(df[x_column], errors="coerce", format="mixed")
        if converted.notna().mean() > 0.9:
            df[x_column] = converted

    try:
        if group_column:
            df[group_column] = fold_other(df[group_column].astype(str))
        x_key = (
            pd.Grouper(key=x_column, freq=resample)
            if resample and pd.api.types.is_datetime64_any_dtype(df[x_column])
            else x_column
        )
        if group_column:
            wide = df.groupby([x_key, group_column])[y_column].agg(agg).unstack(fill_value=0)
        else:
            wide = df.groupby(x_key)[y_column].agg(agg).to_frame(y_column)
        wide = wide.sort_index()
        if normalize:
            wide = wide.div(wide.sum(axis=1), axis=0) * 100

        plt.figure(figsize=(figsize_width, figsize_height))
        ax = plt.gca()
        colors = theming.palette()[: wide.shape[1]]
        ax.stackplot(
            wide.index, [wide[c].to_numpy() for c in wide.columns],
            labels=[str(c) for c in wide.columns], colors=colors,
            alpha=0.85, edgecolor=theming.face_color(), linewidth=1.0,
        )
        ax.set_xlabel(x_column)
        ax.set_ylabel("Share (%)" if normalize else f"{agg}({y_column})")
        ax.set_title(title or f"{y_column} over {x_column}"
                     + (f" by {group_column}" if group_column else ""))
        if wide.shape[1] >= 2:
            _legend_outside(ax, group_column)
        plt.xticks(rotation=30, ha="right")
        base = f"area_{safe_name(y_column)}_over_{safe_name(x_column)}"
        return save_current_figure(base + ("_pct" if normalize else "") + ".png")
    except ValueError:
        plt.close()
        raise
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_slope(
    csv_path: str,
    category_column: str,
    value_column: str,
    period_column: str,
    start_period: str = None,
    end_period: str = None,
    agg: str = "mean",
    top_n: int = 8,
    title: str = None,
    figsize_width: int = 8,
    figsize_height: int = 7,
) -> str:
    """Slope chart: each category's change between two periods.

    The two periods default to the first and last (sorted) values of
    ``period_column``. Every line is direct-labeled at both ends — a slope
    chart with a detached legend defeats its purpose.
    """
    df = get_data(csv_path).copy()
    require_columns(df, category_column, value_column, period_column)
    require_numeric(df, value_column)

    periods = sorted(df[period_column].dropna().unique(), key=str)
    if len(periods) < 2:
        raise ValueError(f"'{period_column}' needs at least 2 distinct periods.")
    p0 = start_period if start_period is not None else periods[0]
    p1 = end_period if end_period is not None else periods[-1]
    if str(p0) == str(p1):
        raise ValueError("start_period and end_period must differ.")

    sub = df[df[period_column].astype(str).isin({str(p0), str(p1)})]
    wide = (
        sub.groupby([category_column, sub[period_column].astype(str)])[value_column]
        .agg(agg)
        .unstack()
    )
    wide = wide.dropna()
    if wide.empty:
        raise ValueError("No category has values in both periods.")
    # Rank by movement so the visible lines are the interesting ones.
    wide = wide.reindex(
        (wide[str(p1)] - wide[str(p0)]).abs().sort_values(ascending=False).index
    ).head(top_n)

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        ax = plt.gca()
        colors = theming.palette()
        label_color = plt.rcParams.get("axes.labelcolor", "#3a4553")
        for i, (name, row) in enumerate(wide.iterrows()):
            c = colors[i % len(colors)] if i < len(colors) else "#9aa5b5"
            y0, y1 = row[str(p0)], row[str(p1)]
            ax.plot([0, 1], [y0, y1], marker="o", color=c)
            ax.annotate(f"{name} {y0:,.3g}", (0, y0), ha="right", va="center",
                        xytext=(-8, 0), textcoords="offset points",
                        fontsize=9.5, color=label_color)
            ax.annotate(f"{y1:,.3g} {name}", (1, y1), ha="left", va="center",
                        xytext=(8, 0), textcoords="offset points",
                        fontsize=9.5, color=label_color)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([str(p0), str(p1)])
        ax.set_xlim(-0.45, 1.45)
        ax.set_ylabel(f"{agg}({value_column})")
        ax.set_title(title or f"{value_column}: {p0} → {p1}")
        ax.grid(axis="x", visible=False)
        return save_current_figure(
            f"slope_{safe_name(value_column)}_{safe_name(str(p0))}_{safe_name(str(p1))}.png"
        )
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_small_multiples(
    csv_path: str,
    column: str,
    by_column: str,
    chart: str = "histogram",
    x_column: str = None,
    max_facets: int = 12,
    bins: int = 20,
    title: str = None,
) -> str:
    """Small multiples: one mini-chart per category, shared axes.

    The right answer when a single chart would need more than ~8 colors:
    instead of cycling hues, split into facets so each group is judged on
    the same scale.

    Args:
        chart: 'histogram' (distribution of ``column`` per facet) or
            'line' (``column`` over ``x_column`` per facet).
    """
    if chart not in ("histogram", "line"):
        raise ValueError("chart must be 'histogram' or 'line'.")
    df = get_data(csv_path).copy()
    require_columns(df, column, by_column, x_column)
    require_numeric(df, column)
    if chart == "line" and not x_column:
        raise ValueError("chart='line' requires x_column.")

    levels = df[by_column].astype(str).value_counts().head(max_facets).index.tolist()
    dropped = int(df[by_column].nunique()) - len(levels)
    df = df[df[by_column].astype(str).isin(levels)]

    n = len(levels)
    ncols = min(4, max(1, int(np.ceil(np.sqrt(n)))))
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(3.2 * ncols, 2.6 * nrows),
        sharex=True, sharey=True, squeeze=False,
    )
    try:
        primary = theming.palette()[0]
        label_color = plt.rcParams.get("axes.labelcolor", "#3a4553")
        if chart == "histogram":
            lo, hi = df[column].min(), df[column].max()
            edges = np.linspace(lo, hi, bins + 1)
        for ax, level in zip(axes.flat, levels):
            sub = df[df[by_column].astype(str) == level]
            if chart == "histogram":
                ax.hist(sub[column].dropna(), bins=edges, color=primary,
                        edgecolor=theming.face_color(), linewidth=0.8)
            else:
                s = sub[[x_column, column]].dropna().sort_values(x_column)
                ax.plot(s[x_column], s[column], color=primary)
            ax.set_title(str(level), fontsize=10, color=label_color)
        for ax in axes.flat[n:]:
            ax.set_visible(False)
        sup = title or f"{column} by {by_column}" + (
            f" (top {len(levels)}, {dropped} facets dropped)" if dropped > 0 else ""
        )
        fig.suptitle(sup, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        return save_current_figure(
            f"facets_{safe_name(column)}_by_{safe_name(by_column)}.png"
        )
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc

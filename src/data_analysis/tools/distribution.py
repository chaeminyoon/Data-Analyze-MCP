"""Distribution-detail and data-quality charts: ECDF, violin, missingness."""
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

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
from .composition import fold_other


@mcp.tool()
def plot_ecdf(
    csv_path: str,
    column: str,
    group_column: str = None,
    title: str = None,
    figsize_width: int = 9,
    figsize_height: int = 6,
) -> str:
    """Empirical CDF — reads exact percentiles where a histogram only hints.

    "What share of rows is below X?" is answered directly on the y-axis;
    with ``group_column``, distribution shifts between groups are visible
    without binning artifacts. More than 8 groups fold into 'Other'.
    """
    df = get_data(csv_path).copy()
    require_columns(df, column, group_column)
    require_numeric(df, column)

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        if group_column:
            df[group_column] = fold_other(df[group_column].astype(str))
            n = int(df[group_column].nunique())
            ax = sns.ecdfplot(
                data=df, x=column, hue=group_column,
                palette=theming.palette()[:n],
            )
        else:
            ax = sns.ecdfplot(data=df, x=column, color=theming.palette()[0])
        ax.set_ylabel("Cumulative share")
        ax.set_title(title or f"ECDF of {column}"
                     + (f" by {group_column}" if group_column else ""))
        suffix = f"_by_{safe_name(group_column)}" if group_column else ""
        return save_current_figure(f"ecdf_{safe_name(column)}{suffix}.png")
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_violin(
    csv_path: str,
    column: str,
    by_column: str = None,
    title: str = None,
    figsize_width: int = 10,
    figsize_height: int = 6,
) -> str:
    """Violin plot: distribution shape per group (a boxplot hides bimodality).

    Quartiles are drawn inside each violin. More than 8 groups fold into
    'Other' rather than cycling palette hues.
    """
    df = get_data(csv_path).copy()
    require_columns(df, column, by_column)
    require_numeric(df, column)

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        if by_column:
            df[by_column] = fold_other(df[by_column].astype(str))
            n = int(df[by_column].nunique())
            ax = sns.violinplot(
                data=df, x=by_column, y=column, hue=by_column, legend=False,
                palette=theming.palette()[:n], inner="quart", cut=0,
                linewidth=1.0, linecolor=theming.face_color(),
            )
            ax.set_xlabel(by_column)
        else:
            ax = sns.violinplot(
                data=df, y=column, color=theming.palette()[0],
                inner="quart", cut=0, linewidth=1.0,
                linecolor=theming.face_color(),
            )
        ax.set_ylabel(column)
        ax.set_title(title or f"Distribution of {column}"
                     + (f" by {by_column}" if by_column else ""))
        suffix = f"_by_{safe_name(by_column)}" if by_column else ""
        return save_current_figure(f"violin_{safe_name(column)}{suffix}.png")
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_missingness(
    csv_path: str,
    max_columns: int = 30,
    title: str = None,
) -> dict:
    """Missing-data overview: per-column null share + where the gaps sit.

    Left panel ranks columns by missing percentage; right panel shows the
    row-order missingness matrix, which exposes *structured* gaps (a block
    of missing rows, a sensor outage, a join artifact) that a summary
    percentage hides. Only columns with any missing values are drawn.

    Returns the missing stats and the figure path.
    """
    df = get_data(csv_path)
    pct = (df.isna().mean() * 100).sort_values(ascending=False)
    with_missing = pct[pct > 0]
    stats = {
        "total_rows": len(df),
        "columns_with_missing": int((pct > 0).sum()),
        "missing_pct": {c: round(float(v), 2) for c, v in with_missing.items()},
    }
    if with_missing.empty:
        return {**stats, "plot_path": None, "note": "No missing values found."}

    cols = with_missing.head(max_columns).index.tolist()
    fig, (ax_bar, ax_mat) = plt.subplots(
        1, 2, figsize=(13, max(4.0, 0.34 * len(cols) + 1.5)),
        gridspec_kw={"width_ratios": [1, 1.6]},
    )
    try:
        primary = theming.palette()[0]
        ax_bar.barh(
            cols[::-1], with_missing[cols][::-1],
            color=primary, edgecolor=theming.face_color(), linewidth=1.2,
        )
        style_bars(ax_bar)
        ax_bar.set_xlabel("Missing (%)")
        ax_bar.set_title("Missing share", loc="left")

        # Row-order matrix: 1 where missing. Downsample rows for large data.
        matrix = df[cols].isna().to_numpy()
        if matrix.shape[0] > 2000:
            idx = np.linspace(0, matrix.shape[0] - 1, 2000).astype(int)
            matrix = matrix[idx]
        ax_mat.imshow(
            matrix, aspect="auto", interpolation="nearest",
            cmap=theming.sequential_cmap(),
        )
        ax_mat.set_xticks(range(len(cols)))
        ax_mat.set_xticklabels(cols, rotation=45, ha="right", fontsize=8.5)
        ax_mat.set_ylabel("Row (dataset order)")
        ax_mat.set_title("Where the gaps sit (dark = missing)", loc="left")

        fig.suptitle(title or "Missing data overview", fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        stats["plot_path"] = save_current_figure("missingness_overview.png")
        return stats
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def stat_tile(
    csv_path: str,
    column: str,
    agg: str = "mean",
    compare_agg: str = None,
    title: str = None,
    fmt: str = "{:,.2f}",
    figsize_width: int = 5,
    figsize_height: int = 3,
) -> dict:
    """A hero-number tile — when the answer is ONE number, don't chart it.

    Renders ``agg(column)`` as a large figure with the metric name beneath,
    optionally annotated with a second aggregate (e.g. median) for context.

    Returns the computed value(s) and the image path.
    """
    df = get_data(csv_path)
    require_numeric(df, column)

    value = float(df[column].agg(agg))
    result = {"column": column, "agg": agg, "value": round(value, 6)}
    context = None
    if compare_agg:
        context = float(df[column].agg(compare_agg))
        result["compare_agg"] = compare_agg
        result["compare_value"] = round(context, 6)

    fig = plt.figure(figsize=(figsize_width, figsize_height))
    try:
        text_color = plt.rcParams.get("text.color", "#0b0b0b")
        muted = plt.rcParams.get("axes.labelcolor", "#52514e")
        fig.text(0.5, 0.62, fmt.format(value), ha="center", va="center",
                 fontsize=34, fontweight="bold", color=text_color)
        fig.text(0.5, 0.32, title or f"{agg} of {column}", ha="center",
                 va="center", fontsize=12, color=muted)
        if context is not None:
            fig.text(0.5, 0.16, f"{compare_agg}: {fmt.format(context)}",
                     ha="center", va="center", fontsize=10, color=muted)
        result["plot_path"] = save_current_figure(
            f"stat_{safe_name(agg)}_{safe_name(column)}.png"
        )
        return result
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_qq(
    csv_path: str,
    column: str,
    title: str = None,
    figsize_width: int = 7,
    figsize_height: int = 6,
) -> dict:
    """Q-Q plot against a normal distribution — the visual companion to
    ``test_normality``. Systematic curvature means skew; ends peeling off the
    line mean heavy tails. Returns the fit slope/intercept/r as well."""
    from scipy import stats

    df = get_data(csv_path)
    require_numeric(df, column)
    values = df[column].dropna().to_numpy()
    if len(values) < 3:
        raise ValueError(f"Column '{column}' needs at least 3 non-null values.")

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        ax = plt.gca()
        (osm, osr), (slope, intercept, r) = stats.probplot(values, dist="norm")
        ax.scatter(osm, osr, s=22, alpha=0.6, color=theming.palette()[0],
                   edgecolors="none")
        ref_color = plt.rcParams.get("axes.edgecolor", "#c3c2b7")
        ax.plot(osm, slope * np.asarray(osm) + intercept, linestyle="--",
                linewidth=1.4, color=ref_color)
        ax.set_xlabel("Theoretical quantiles (normal)")
        ax.set_ylabel(f"Observed quantiles ({column})")
        ax.set_title(title or f"Q-Q plot — {column} vs normal")
        path = save_current_figure(f"qq_{safe_name(column)}.png")
        return {
            "column": column,
            "fit": {"slope": round(float(slope), 4),
                    "intercept": round(float(intercept), 4),
                    "r": round(float(r), 4)},
            "plot_path": path,
        }
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc

"""Phase 2: EDA visualization tools (static matplotlib/seaborn + interactive Plotly)."""
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns

from .. import theming
from ..cache import get_data
from ..helpers import output_path, require_columns, safe_name, save_current_figure
from ..server import mcp


# --- [Static plots] --------------------------------------------------------
@mcp.tool()
def plot_histogram(
    csv_path: str,
    column: str,
    bins: int = 10,
    kde: bool = True,
    title: str = None,
    xlabel: str = None,
    ylabel: str = None,
    color: str = None,
    figsize_width: int = 8,
    figsize_height: int = 6,
    alpha: float = 0.6,
    show_legend: bool = False,
    legend_label: str = None,
) -> str:
    """Generate a customizable density histogram for a column."""
    df = get_data(csv_path)
    require_columns(df, column)

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        sns.histplot(
            df[column].dropna(),
            bins=bins,
            kde=kde,
            stat="density",
            edgecolor=theming.face_color(),
            alpha=alpha,
            color=color,
            label=legend_label or column,
        )
        plt.xlabel(xlabel or column)
        plt.ylabel(ylabel or "Density")
        plt.title(title or f"Density Histogram of {column}")
        if show_legend:
            plt.legend()
        return save_current_figure(f"{safe_name(column)}_density_hist.png")
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_boxplot(
    csv_path: str,
    column: str,
    by_column: str = None,
    title: str = None,
    xlabel: str = None,
    ylabel: str = None,
    figsize_width: int = 10,
    figsize_height: int = 6,
    color: str = None,
    alpha: float = 0.6,
    show_legend: bool = False,
    legend_label: str = None,
) -> str:
    """Generate a customizable boxplot for outlier visualization."""
    df = get_data(csv_path)
    require_columns(df, column, by_column)

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        if by_column:
            sns.boxplot(
                data=df, x=by_column, y=column, hue=by_column,
                legend=show_legend, palette=theming.palette(),
            )
            plt.title(title or f"Boxplot of {column} by {by_column}")
            plt.xlabel(xlabel or by_column)
            plt.ylabel(ylabel or column)
            if show_legend:
                plt.legend(title=legend_label or by_column)
        else:
            sns.boxplot(data=df, y=column, color=color)
            plt.title(title or f"Boxplot of {column}")
            plt.xlabel(xlabel)
            plt.ylabel(ylabel or column)
            if show_legend:
                patch = mpatches.Patch(color=color, label=legend_label or column)
                plt.legend(handles=[patch])

        suffix = f"_by_{safe_name(by_column)}" if by_column else ""
        return save_current_figure(f"boxplot_{safe_name(column)}{suffix}.png")
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_scatter(
    csv_path: str,
    x_column: str,
    y_column: str,
    hue_column: str = None,
    title: str = None,
    xlabel: str = None,
    ylabel: str = None,
    figsize_width: int = 10,
    figsize_height: int = 6,
    marker_size: int = 50,
    alpha: float = 0.6,
    color_palette: str = None,
    show_legend: bool = True,
    legend_title: str = None,
    legend_position: str = "best",
) -> str:
    """Generate a customizable scatter plot for bivariate analysis."""
    df = get_data(csv_path)
    require_columns(df, x_column, y_column, hue_column)

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        ax = sns.scatterplot(
            data=df, x=x_column, y=y_column, hue=hue_column,
            s=marker_size, alpha=alpha, palette=color_palette,
        )
        plt.title(title or f"Scatter Plot: {x_column} vs {y_column}")
        plt.xlabel(xlabel or x_column)
        plt.ylabel(ylabel or y_column)

        if hue_column:
            if show_legend:
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    plt.legend(
                        handles=handles, labels=labels,
                        loc=legend_position, title=legend_title or hue_column,
                    )
            elif ax.legend_ is not None:
                ax.legend_.remove()

        return save_current_figure(
            f"scatter_{safe_name(x_column)}_vs_{safe_name(y_column)}.png"
        )
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_correlation_heatmap(csv_path: str, columns: list = None) -> str:
    """Generate a correlation heatmap for numeric columns."""
    df = get_data(csv_path)
    numeric_df = (df[columns] if columns else df).select_dtypes(include=["number"])
    if numeric_df.empty:
        raise ValueError("No numeric columns found for correlation analysis.")

    plt.figure(figsize=(12, 10))
    try:
        sns.heatmap(
            numeric_df.corr(), annot=True, fmt=".2f", cmap="coolwarm",
            center=0, square=True, linewidths=0.5,
        )
        plt.title("Correlation Heatmap")
        return save_current_figure("correlation_heatmap.png")
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def analyze_target_distribution(csv_path: str, target_column: str) -> dict:
    """Analyze target variable distribution and detect imbalance."""
    df = get_data(csv_path)
    require_columns(df, target_column)

    value_counts = df[target_column].value_counts()
    percentages = df[target_column].value_counts(normalize=True) * 100

    result = {
        "target_column": target_column,
        "value_counts": value_counts.to_dict(),
        "percentages": {k: round(v, 2) for k, v in percentages.to_dict().items()},
        "is_imbalanced": bool(percentages.min() < 30),
        "total_samples": len(df),
    }

    plt.figure(figsize=(8, 6))
    try:
        value_counts.plot(kind="bar")
        plt.title(f"Distribution of {target_column}")
        plt.xlabel(target_column)
        plt.ylabel("Count")
        plt.xticks(rotation=45)
        result["plot_path"] = save_current_figure(
            f"target_distribution_{safe_name(target_column)}.png"
        )
    except Exception:  # noqa: BLE001 - plot is best-effort, stats already computed
        plt.close()

    return result


@mcp.tool()
def plot_line(
    csv_path: str,
    x_column: str,
    y_column: str,
    group_column: str = None,
    resample: str = None,
    agg: str = "mean",
    interactive: bool = False,
    title: str = None,
    figsize_width: int = 12,
    figsize_height: int = 6,
) -> str:
    """Generate a line chart, ideal for time series (datetime x-axis).

    Args:
        x_column: X-axis column; object columns that parse as dates are
            converted automatically.
        y_column: Numeric column to plot.
        group_column: Optional category column — one line per group.
        resample: Optional pandas frequency ('D', 'W', 'M', ...) to aggregate
            a datetime x-axis into buckets.
        agg: Aggregation for duplicate x values / resampling (mean, sum, ...).
        interactive: True renders a Plotly HTML file instead of a PNG.
    """
    df = get_data(csv_path).copy()
    require_columns(df, x_column, y_column, group_column)
    if not pd.api.types.is_numeric_dtype(df[y_column]):
        raise ValueError(f"Column '{y_column}' must be numeric.")

    # Auto-convert date-like string x-axes so CSV dates plot chronologically.
    # (dtype-agnostic check: pandas 3 uses 'str' dtype, not 'object', for strings)
    if not pd.api.types.is_datetime64_any_dtype(df[x_column]) and not pd.api.types.is_numeric_dtype(df[x_column]):
        converted = pd.to_datetime(df[x_column], errors="coerce", format="mixed")
        if converted.notna().mean() > 0.9:
            df[x_column] = converted

    try:
        keys = [group_column] if group_column else []
        if resample:
            if not pd.api.types.is_datetime64_any_dtype(df[x_column]):
                raise ValueError("resample requires a datetime x_column.")
            keys.append(pd.Grouper(key=x_column, freq=resample))
        else:
            keys.append(x_column)
        data = df.groupby(keys, dropna=True)[y_column].agg(agg).reset_index()
        data = data.sort_values(x_column)

        base = f"line_{safe_name(y_column)}_over_{safe_name(x_column)}"
        if group_column:
            base += f"_by_{safe_name(group_column)}"
        if interactive:
            fig = px.line(
                data, x=x_column, y=y_column, color=group_column,
                title=title or f"{y_column} over {x_column}", **theming.plotly_kwargs(),
            )
            path = output_path(f"{base}.html")
            fig.write_html(path)
            return path

        plt.figure(figsize=(figsize_width, figsize_height))
        if group_column:
            for g, sub in data.groupby(group_column):
                plt.plot(sub[x_column], sub[y_column], marker=".", label=str(g))
            plt.legend(title=group_column)
        else:
            plt.plot(data[x_column], data[y_column], marker=".")
        plt.title(title or f"{y_column} over {x_column}")
        plt.xlabel(x_column)
        plt.ylabel(f"{agg}({y_column})" if resample else y_column)
        plt.xticks(rotation=30, ha="right")
        return save_current_figure(f"{base}.png")
    except ValueError:
        plt.close()
        raise
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_bar(
    csv_path: str,
    column: str,
    y_column: str = None,
    agg: str = "mean",
    top_n: int = 20,
    interactive: bool = False,
    title: str = None,
    figsize_width: int = 10,
    figsize_height: int = 6,
) -> str:
    """Generate a bar chart of category frequencies or aggregated values.

    Args:
        column: Categorical column for the x-axis.
        y_column: Optional numeric column; when given, bars show
            ``agg(y_column)`` per category instead of counts.
        agg: Aggregation when y_column is set (mean, sum, median, ...).
        top_n: Show at most this many categories (largest first).
        interactive: True renders a Plotly HTML file instead of a PNG.
    """
    df = get_data(csv_path)
    require_columns(df, column, y_column)

    try:
        if y_column:
            if not pd.api.types.is_numeric_dtype(df[y_column]):
                raise ValueError(f"Column '{y_column}' must be numeric.")
            data = df.groupby(column)[y_column].agg(agg).sort_values(ascending=False)
            ylabel = f"{agg}({y_column})"
        else:
            data = df[column].value_counts()
            ylabel = "Count"
        total = len(data)
        data = data.head(top_n)

        base = f"bar_{safe_name(column)}" + (f"_{safe_name(y_column)}" if y_column else "")
        chart_title = title or (
            f"{ylabel} by {column}" + (f" (top {top_n} of {total})" if total > top_n else "")
        )
        if interactive:
            plot_df = data.rename(ylabel).reset_index()
            fig = px.bar(
                plot_df, x=column, y=ylabel, title=chart_title, **theming.plotly_kwargs(),
            )
            path = output_path(f"{base}.html")
            fig.write_html(path)
            return path

        plt.figure(figsize=(figsize_width, figsize_height))
        data.plot(kind="bar")
        plt.title(chart_title)
        plt.xlabel(column)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45, ha="right")
        return save_current_figure(f"{base}.png")
    except ValueError:
        plt.close()
        raise
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


# --- [Interactive Plotly plots] --------------------------------------------
@mcp.tool()
def plot_interactive_scatter(
    csv_path: str,
    x_column: str,
    y_column: str,
    color_column: str = None,
    size_column: str = None,
    hover_name: str = None,
    title: str = None,
) -> str:
    """Generate an interactive Plotly scatter plot. Returns the HTML file path."""
    df = get_data(csv_path)
    require_columns(df, x_column, y_column, color_column, size_column)

    try:
        fig = px.scatter(
            df, x=x_column, y=y_column, color=color_column, size=size_column,
            hover_name=hover_name,
            title=title or f"Interactive Scatter: {x_column} vs {y_column}",
            **theming.plotly_kwargs(),
        )
        path = output_path(
            f"interactive_scatter_{safe_name(x_column)}_vs_{safe_name(y_column)}.html"
        )
        fig.write_html(path)
        return path
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Interactive visualization failed: {exc}") from exc


@mcp.tool()
def plot_interactive_histogram(
    csv_path: str,
    column: str,
    color_column: str = None,
    bins: int = None,
    title: str = None,
) -> str:
    """Generate an interactive Plotly histogram (with marginal boxplot)."""
    df = get_data(csv_path)
    require_columns(df, column, color_column)

    try:
        fig = px.histogram(
            df, x=column, color=color_column, nbins=bins,
            title=title or f"Interactive Histogram: {column}",
            **theming.plotly_kwargs(), marginal="box",
        )
        path = output_path(f"interactive_hist_{safe_name(column)}.html")
        fig.write_html(path)
        return path
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Interactive visualization failed: {exc}") from exc


@mcp.tool()
def plot_interactive_boxplot(
    csv_path: str,
    y_column: str,
    x_column: str = None,
    color_column: str = None,
    title: str = None,
) -> str:
    """Generate an interactive Plotly boxplot."""
    df = get_data(csv_path)
    require_columns(df, y_column, x_column, color_column)

    try:
        fig = px.box(
            df, y=y_column, x=x_column, color=color_column,
            title=title or f"Interactive Boxplot: {y_column}",
            **theming.plotly_kwargs(), points="outliers",
        )
        path = output_path(f"interactive_boxplot_{safe_name(y_column)}.html")
        fig.write_html(path)
        return path
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Interactive visualization failed: {exc}") from exc


@mcp.tool()
def plot_interactive_heatmap(csv_path: str, method: str = "pearson", title: str = None) -> str:
    """Generate an interactive Plotly correlation heatmap."""
    df = get_data(csv_path)
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        raise ValueError("No numeric columns found for correlation.")

    try:
        fig = px.imshow(
            numeric_df.corr(method=method), text_auto=True, aspect="auto",
            title=title or f"Interactive Correlation Heatmap ({method})",
            color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
            template=theming.plotly_template(),
        )
        path = output_path("interactive_heatmap.html")
        fig.write_html(path)
        return path
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Interactive visualization failed: {exc}") from exc

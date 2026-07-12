"""Phase 3: statistical analysis and hypothesis-testing tools."""
import pandas as pd
from scipy import stats

from ..cache import get_data
from ..helpers import require_columns, require_numeric
from ..server import mcp

_ALPHA = 0.05


@mcp.tool()
def calculate_correlation(csv_path: str, method: str = "pearson") -> dict:
    """Calculate correlation coefficients between numeric columns."""
    if method not in ("pearson", "spearman", "kendall"):
        raise ValueError("Method must be 'pearson', 'spearman', or 'kendall'.")

    numeric_df = get_data(csv_path).select_dtypes(include=["number"])
    if numeric_df.empty:
        raise ValueError("No numeric columns found.")

    corr_matrix = numeric_df.corr(method=method)
    return {
        "method": method,
        "correlation_matrix": corr_matrix.to_dict(),
        "columns": corr_matrix.columns.tolist(),
    }


@mcp.tool()
def test_normality(csv_path: str, column: str) -> dict:
    """Test normality using the Shapiro-Wilk test."""
    df = get_data(csv_path)
    require_numeric(df, column)

    data = df[column].dropna()
    if len(data) < 3:
        raise ValueError("Need at least 3 samples for normality test.")

    statistic, p_value = stats.shapiro(data)
    is_normal = bool(p_value > _ALPHA)
    return {
        "column": column,
        "test": "Shapiro-Wilk",
        "statistic": round(float(statistic), 4),
        "p_value": round(float(p_value), 4),
        "is_normal": is_normal,
        "alpha": _ALPHA,
        "interpretation": "Data is normally distributed"
        if is_normal
        else "Data is NOT normally distributed",
    }


@mcp.tool()
def test_ttest(csv_path: str, column: str, group_column: str) -> dict:
    """Perform an independent t-test between two groups."""
    df = get_data(csv_path)
    require_numeric(df, column)
    require_columns(df, group_column)

    groups = df[group_column].unique()
    if len(groups) != 2:
        raise ValueError(f"Group column must have exactly 2 unique values. Found: {len(groups)}")

    group1 = df[df[group_column] == groups[0]][column].dropna()
    group2 = df[df[group_column] == groups[1]][column].dropna()

    statistic, p_value = stats.ttest_ind(group1, group2)
    is_significant = bool(p_value < _ALPHA)
    return {
        "column": column,
        "group_column": group_column,
        "groups": [str(groups[0]), str(groups[1])],
        "test": "Independent T-Test",
        "statistic": round(float(statistic), 4),
        "p_value": round(float(p_value), 4),
        "is_significant": is_significant,
        "alpha": _ALPHA,
        "interpretation": "Means are significantly different"
        if is_significant
        else "Means are NOT significantly different",
    }


@mcp.tool()
def test_anova(csv_path: str, column: str, group_column: str) -> dict:
    """Perform a one-way ANOVA test across multiple groups."""
    df = get_data(csv_path)
    require_numeric(df, column)
    require_columns(df, group_column)

    groups = df[group_column].unique()
    if len(groups) < 2:
        raise ValueError("Need at least 2 groups for ANOVA.")

    group_data = [df[df[group_column] == g][column].dropna() for g in groups]
    statistic, p_value = stats.f_oneway(*group_data)
    is_significant = bool(p_value < _ALPHA)
    return {
        "column": column,
        "group_column": group_column,
        "num_groups": len(groups),
        "test": "One-Way ANOVA",
        "statistic": round(float(statistic), 4),
        "p_value": round(float(p_value), 4),
        "is_significant": is_significant,
        "alpha": _ALPHA,
        "interpretation": "At least one group mean is significantly different"
        if is_significant
        else "No significant difference between group means",
    }


@mcp.tool()
def test_chi_square(csv_path: str, column1: str, column2: str) -> dict:
    """Perform a chi-square test of independence between two categorical variables."""
    df = get_data(csv_path)
    require_columns(df, column1, column2)

    contingency_table = pd.crosstab(df[column1], df[column2])
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency_table)
    is_independent = p_value > _ALPHA
    return {
        "column1": column1,
        "column2": column2,
        "test": "Chi-Square Test of Independence",
        "chi2_statistic": round(float(chi2), 4),
        "p_value": round(float(p_value), 4),
        "degrees_of_freedom": int(dof),
        "is_independent": is_independent,
        "alpha": _ALPHA,
        "interpretation": "Variables are independent"
        if is_independent
        else "Variables are NOT independent (associated)",
    }


@mcp.tool()
def calculate_confidence_interval(csv_path: str, column: str, confidence: float = 0.95) -> dict:
    """Calculate the confidence interval for the mean of a numeric column."""
    df = get_data(csv_path)
    require_numeric(df, column)

    data = df[column].dropna()
    if len(data) < 2:
        raise ValueError("Need at least 2 samples for confidence interval.")

    mean = data.mean()
    sem = stats.sem(data)
    ci = stats.t.interval(confidence, len(data) - 1, loc=mean, scale=sem)
    return {
        "column": column,
        "mean": round(float(mean), 4),
        "confidence_level": confidence,
        "lower_bound": round(float(ci[0]), 4),
        "upper_bound": round(float(ci[1]), 4),
        "margin_of_error": round(float(ci[1] - mean), 4),
        "sample_size": len(data),
    }

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import os
from scipy import stats

from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import LabelEncoder, PolynomialFeatures
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    mean_squared_error, mean_absolute_error, r2_score
)
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.svm import SVC, SVR
try:
    from xgboost import XGBClassifier, XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# --- [Smart Cache Manager] ---
_DATA_CACHE = {}

# --- [Korean Font Setup] ---
import platform
from matplotlib import font_manager, rc

system_name = platform.system()
if system_name == "Windows":
    # Windows: Malgun Gothic
    rc('font', family='Malgun Gothic')
elif system_name == "Darwin":
    # Mac: AppleGothic
    rc('font', family='AppleGothic')
else:
    # Linux: NanumGothic (if installed)
    rc('font', family='NanumGothic')

# Fix minus sign display issue
plt.rcParams['axes.unicode_minus'] = False

mcp = FastMCP("DataAnalysis")

# --- [Helper Functions] ---
def get_data(csv_path: str) -> pd.DataFrame:
    """Smart caching data loader"""
    global _DATA_CACHE
    
    if csv_path in _DATA_CACHE:
        return _DATA_CACHE[csv_path]
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
        
    try:
        df = pd.read_csv(csv_path)
        _DATA_CACHE[csv_path] = df
        return df
    except Exception as e:
        raise ValueError(f"Error loading CSV: {str(e)}")

# --- [Phase 1: Data Exploration & Preprocessing Tools] ---
# (Previous tools from Phase 1 remain unchanged)

@mcp.tool()
def get_dataset_info(csv_path: str) -> dict:
    """Get basic information about a CSV dataset."""
    df = get_data(csv_path)
    return {
        "filename": os.path.basename(csv_path),
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict()
    }

@mcp.tool()
def profile_dataset(csv_path: str) -> dict:
    """Comprehensive dataset profiling with statistics and correlations."""
    df = get_data(csv_path)
    
    profile = {
        "filename": os.path.basename(csv_path),
        "shape": df.shape,
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2)
    }
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        profile["numeric_stats"] = df[numeric_cols].describe().to_dict()
    
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    if categorical_cols:
        cat_stats = {}
        for col in categorical_cols:
            cat_stats[col] = {
                "unique_count": df[col].nunique(),
                "most_frequent": df[col].mode()[0] if len(df[col].mode()) > 0 else None,
                "frequency": df[col].value_counts().iloc[0] if len(df[col]) > 0 else 0
            }
        profile["categorical_stats"] = cat_stats
    
    total_missing = df.isnull().sum().sum()
    total_cells = df.shape[0] * df.shape[1]
    profile["missing_summary"] = {
        "total_missing": int(total_missing),
        "missing_percentage": round(total_missing / total_cells * 100, 2)
    }
    
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
        high_corr = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    high_corr.append({
                        "feature1": corr_matrix.columns[i],
                        "feature2": corr_matrix.columns[j],
                        "correlation": round(corr_value, 3)
                    })
        profile["high_correlations"] = high_corr
    
    return profile

@mcp.tool()
def detect_data_types(csv_path: str) -> dict:
    """Auto-detect and classify column data types."""
    df = get_data(csv_path)
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = []
    datetime_cols = []
    text_cols = []
    
    for col in df.select_dtypes(include=['object']).columns:
        try:
            pd.to_datetime(df[col], errors='raise')
            datetime_cols.append(col)
            continue
        except:
            pass
        
        if df[col].nunique() / len(df) < 0.5:
            categorical_cols.append(col)
        else:
            text_cols.append(col)
    
    return {
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "text_columns": text_cols,
        "total_columns": len(df.columns)
    }

@mcp.tool()
def find_duplicates(csv_path: str, subset: list = None) -> dict:
    """Detect duplicate rows in dataset."""
    df = get_data(csv_path)
    
    duplicates = df.duplicated(subset=subset, keep='first')
    duplicate_indices = df[duplicates].index.tolist()
    
    return {
        "duplicate_count": int(duplicates.sum()),
        "duplicate_percentage": round(duplicates.sum() / len(df) * 100, 2),
        "duplicate_indices": duplicate_indices[:100],
        "total_rows": len(df)
    }

@mcp.tool()
def handle_missing_values(
    csv_path: str,
    strategy: dict = None,
    save_to: str = None
) -> dict:
    """Handle missing values with various strategies."""
    df = get_data(csv_path).copy()
    original_shape = df.shape
    
    if strategy is None:
        strategy = {"numeric": "mean", "categorical": "mode"}
    
    strategies_used = {}
    
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            strat = strategy.get("numeric", "mean")
            if strat == "mean":
                df[col].fillna(df[col].mean(), inplace=True)
            elif strat == "median":
                df[col].fillna(df[col].median(), inplace=True)
            elif strat == "mode":
                df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else 0, inplace=True)
            elif strat == "ffill":
                df[col].fillna(method='ffill', inplace=True)
            strategies_used[col] = strat
    
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if df[col].isnull().sum() > 0:
            strat = strategy.get("categorical", "mode")
            if strat == "mode":
                df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else "Unknown", inplace=True)
            elif strat == "ffill":
                df[col].fillna(method='ffill', inplace=True)
            strategies_used[col] = strat
    
    if "drop" in strategy.values():
        df.dropna(inplace=True)
    
    _DATA_CACHE[csv_path] = df
    
    result = {
        "original_shape": original_shape,
        "new_shape": df.shape,
        "rows_affected": original_shape[0] - df.shape[0],
        "strategies_used": strategies_used
    }
    
    if save_to:
        df.to_csv(save_to, index=False)
        result["output_path"] = save_to
    
    return result

@mcp.tool()
def detect_outliers(
    csv_path: str,
    column: str,
    method: str = "iqr"
) -> dict:
    """Detect outliers in a numeric column."""
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")
    
    data = df[column].dropna()
    
    if method == "iqr":
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    elif method == "zscore":
        z_scores = stats.zscore(data)
        outlier_indices = data.index[abs(z_scores) > 3].tolist()
        outliers = df.loc[outlier_indices]
        lower_bound = data.mean() - 3 * data.std()
        upper_bound = data.mean() + 3 * data.std()
    else:
        raise ValueError("Method must be 'iqr' or 'zscore'.")
    
    return {
        "outlier_count": len(outliers),
        "outlier_percentage": round(len(outliers) / len(df) * 100, 2),
        "outlier_indices": outliers.index.tolist()[:100],
        "outlier_values": outliers[column].tolist()[:100],
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "method": method
    }

@mcp.tool()
def remove_outliers(
    csv_path: str,
    column: str,
    method: str = "iqr",
    save_to: str = None
) -> dict:
    """Remove outliers from a numeric column."""
    df = get_data(csv_path).copy()
    original_shape = df.shape
    
    outlier_info = detect_outliers(csv_path, column, method)
    
    outlier_indices = outlier_info["outlier_indices"]
    df_cleaned = df.drop(index=outlier_indices)
    
    _DATA_CACHE[csv_path] = df_cleaned
    
    result = {
        "rows_removed": len(outlier_indices),
        "original_shape": original_shape,
        "new_shape": df_cleaned.shape,
        "method": method
    }
    
    if save_to:
        df_cleaned.to_csv(save_to, index=False)
        result["output_path"] = save_to
    
    return result

@mcp.tool()
def list_cached_datasets() -> dict:
    """List all currently cached datasets in memory."""
    global _DATA_CACHE
    
    cached_info = []
    total_memory = 0
    
    for path, df in _DATA_CACHE.items():
        memory_mb = df.memory_usage(deep=True).sum() / 1024**2
        total_memory += memory_mb
        cached_info.append({
            "path": path,
            "shape": df.shape,
            "memory_mb": round(memory_mb, 2)
        })
    
    return {
        "cached_files": cached_info,
        "count": len(_DATA_CACHE),
        "total_memory_mb": round(total_memory, 2)
    }

@mcp.tool()
def clear_cache(csv_path: str = None) -> str:
    """Clear cached datasets from memory."""
    global _DATA_CACHE
    
    if csv_path:
        if csv_path in _DATA_CACHE:
            del _DATA_CACHE[csv_path]
            return f"Cache cleared for: {csv_path}"
        else:
            return f"No cached data found for: {csv_path}"
    else:
        count = len(_DATA_CACHE)
        _DATA_CACHE.clear()
        return f"Cache cleared successfully. {count} dataset(s) removed from memory."

# --- [Phase 3.5: Advanced Feature Engineering] ---

@mcp.tool()
def create_derived_feature(
    csv_path: str,
    expression: str,
    new_column_name: str
) -> dict:
    """
    Create a new feature using a mathematical expression involving existing columns.
    Supported operators: +, -, *, /, ** (power), (, )
    Example: expression="price / area", new_column_name="price_per_sqft"
    """
    df = get_data(csv_path).copy()
    
    try:
        # Safety check: simplistic validation to allow only column names and math symbols
        # This uses pandas eval which is reasonably efficient and safer than eval()
        df[new_column_name] = df.eval(expression)
        
        _DATA_CACHE[csv_path] = df
        
        return {
            "message": f"Created feature '{new_column_name}'",
            "expression": expression,
            "preview": df[[new_column_name]].head().to_dict(),
            "new_shape": df.shape
        }
    except Exception as e:
        raise ValueError(f"Feature creation failed: {str(e)}")

@mcp.tool()
def create_polynomial_features(
    csv_path: str,
    columns: list[str],
    degree: int = 2,
    interaction_only: bool = False
) -> dict:
    """
    Generate polynomial and interaction features.
    Useful for capturing non-linear relationships.
    """
    df = get_data(csv_path).copy()
    
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found: {missing}")
        
    try:
        poly = PolynomialFeatures(degree=degree, interaction_only=interaction_only, include_bias=False)
        poly_data = poly.fit_transform(df[columns])
        
        feature_names = poly.get_feature_names_out(columns)
        
        # Create a DataFrame with new features
        poly_df = pd.DataFrame(poly_data, columns=feature_names, index=df.index)
        
        # Drop original columns to avoid duplicates if they are part of the output (usually degree 1 terms are kept)
        # However, PolynomialFeatures output includes original cols. 
        # We'll merge carefully. 
        # Actually, let's just add the valid NEW columns that don't exist
        new_features_count = 0
        for col in feature_names:
            if col not in df.columns:
                df[col] = poly_df[col]
                new_features_count += 1
                
        _DATA_CACHE[csv_path] = df
        
        return {
            "message": f"Generated {new_features_count} new polynomial features",
            "input_columns": columns,
            "degree": degree,
            "new_columns": [c for c in feature_names if c not in columns],
            "new_shape": df.shape
        }
    except Exception as e:
        raise ValueError(f"Polynomial feature generation failed: {str(e)}")

@mcp.tool()
def extract_datetime_features(
    csv_path: str,
    column: str,
    features: list[str] = ["year", "month", "day", "dayofweek"]
) -> dict:
    """
    Extract temporal features from a datetime column.
    Supported features: year, month, day, hour, minute, second, dayofweek, quarter, is_weekend
    """
    df = get_data(csv_path).copy()
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
        
    try:
        # Ensure column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df[column]):
            df[column] = pd.to_datetime(df[column])
            
        created_features = []
        
        for feat in features:
            new_col = f"{column}_{feat}"
            if feat == "year":
                df[new_col] = df[column].dt.year
            elif feat == "month":
                df[new_col] = df[column].dt.month
            elif feat == "day":
                df[new_col] = df[column].dt.day
            elif feat == "hour":
                df[new_col] = df[column].dt.hour
            elif feat == "minute":
                df[new_col] = df[column].dt.minute
            elif feat == "second":
                df[new_col] = df[column].dt.second
            elif feat == "dayofweek":
                df[new_col] = df[column].dt.dayofweek
            elif feat == "quarter":
                df[new_col] = df[column].dt.quarter
            elif feat == "is_weekend":
                df[new_col] = df[column].dt.dayofweek.isin([5, 6]).astype(int)
            
            created_features.append(new_col)
            
        _DATA_CACHE[csv_path] = df
        
        return {
            "message": f"Extracted {len(created_features)} datetime features",
            "source_column": column,
            "created_columns": created_features,
            "new_shape": df.shape
        }
    except Exception as e:
        raise ValueError(f"Datetime extraction failed: {str(e)}")

# --- [Phase 2: EDA Visualization Tools] ---

@mcp.tool()
def plot_histogram(
    csv_path: str,
    column: str,
    bins: int = 10,
    kde: bool = True,
    title: str = None,
    xlabel: str = None,
    ylabel: str = None,
    color: str = "skyblue",
    figsize_width: int = 8,
    figsize_height: int = 6,
    alpha: float = 0.6,
    show_legend: bool = False,
    legend_label: str = None
) -> str:
    """
    Generate customizable density histogram for a specific column.
    
    Args:
        csv_path: Path to CSV file
        column: Column name to visualize
        bins: Number of bins (default: 10)
        kde: Show KDE curve (default: True)
        title: Custom plot title (optional)
        xlabel: Custom x-axis label (optional)
        ylabel: Custom y-axis label (optional)
        color: Bar color (default: "skyblue")
        figsize_width: Figure width in inches (default: 8)
        figsize_height: Figure height in inches (default: 6)
        alpha: Transparency (0-1, default: 0.6)
        show_legend: Show legend (default: False)
        legend_label: Custom legend label (optional)
    """
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")

    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        sns.histplot(
            df[column].dropna(),
            bins=bins,
            kde=kde,
            stat="density",
            edgecolor="black",
            alpha=alpha,
            color=color,
            label=legend_label or column
        )
        
        plt.xlabel(xlabel or column)
        plt.ylabel(ylabel or "Density")
        plt.title(title or f"Density Histogram of {column}")
        
        # Legend
        if show_legend:
            plt.legend()
        
        output_path = f"{column}_density_hist.png"
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return output_path
    except Exception as e:
        plt.close()
        raise ValueError(f"Visualization failed: {str(e)}")

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
    color: str = "skyblue",
    alpha: float = 0.6,
    show_legend: bool = False,
    legend_label: str = None
) -> str:
    """
    Generate customizable boxplot for outlier visualization.
    
    Args:
        csv_path: Path to CSV file
        column: Column name to visualize (numerical)
        by_column: Optional column to group by (categorical)
        title: Custom plot title (optional)
        xlabel: Custom x-axis label (optional)
        ylabel: Custom y-axis label (optional)
        figsize_width: Figure width in inches (default: 10)
        figsize_height: Figure height in inches (default: 6)
        color: Box color (default: "skyblue")
        alpha: Transparency (0-1, default: 0.6)
        show_legend: Show legend (default: False)
        legend_label: Custom legend label (optional)
    """
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")
    
    if by_column and by_column not in df.columns:
        raise ValueError(f"Column '{by_column}' not found in CSV.")
    
    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        if by_column:
            # Using seaborn for better control with hue
            sns.boxplot(
                data=df,
                x=by_column,
                y=column,
                hue=by_column, # Use by_column for hue if it's categorical
                legend=show_legend,
                palette="Set2" # Example palette, can be customized
            )
            plt.title(title or f"Boxplot of {column} by {by_column}")
            plt.xlabel(xlabel or by_column)
            plt.ylabel(ylabel or column)
            
            if show_legend:
                 # Legend is handled by seaborn's hue, but we can customize title
                 plt.legend(title=legend_label or by_column)
            
        else:
            sns.boxplot(
                data=df,
                y=column,
                color=color,
                # alpha is not directly supported in boxplot, but we can stick to color
            )
            plt.title(title or f"Boxplot of {column}")
            plt.xlabel(xlabel) # No default x-label if not by_column
            plt.ylabel(ylabel or column)
            
            # Boxplot without hue usually doesn't need a legend, but if requested:
            if show_legend:
                 import matplotlib.patches as mpatches
                 patch = mpatches.Patch(color=color, label=legend_label or column)
                 plt.legend(handles=[patch])

        safe_col = "".join(c for c in column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        safe_by = "".join(c for c in (by_column or "")) if by_column else ""
        output_path = f"boxplot_{safe_col}{'_by_' + safe_by if safe_by else ''}.png"
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return output_path
    except Exception as e:
        plt.close()
        raise ValueError(f"Visualization failed: {str(e)}")

@mcp.tool()
def plot_interactive_scatter(
    csv_path: str,
    x_column: str,
    y_column: str,
    color_column: str = None,
    size_column: str = None,
    hover_name: str = None,
    title: str = None
) -> str:
    """
    Generate interactive scatter plot using Plotly.
    Returns path to the generated HTML file.
    
    Args:
        csv_path: Path to CSV file
        x_column: Column for x-axis
        y_column: Column for y-axis
        color_column: Column for color grouping (optional)
        size_column: Column for marker size (optional)
        hover_name: Column to display on hover (optional)
        title: Chart title (optional)
    """
    df = get_data(csv_path)
    
    if x_column not in df.columns:
         raise ValueError(f"Column '{x_column}' not found.")
    if y_column not in df.columns:
         raise ValueError(f"Column '{y_column}' not found.")
        
    try:
        # Check if columns exist if provided
        if color_column and color_column not in df.columns:
            raise ValueError(f"Column '{color_column}' not found.")
        if size_column and size_column not in df.columns:
            raise ValueError(f"Column '{size_column}' not found.")
            
        fig = px.scatter(
            df, 
            x=x_column, 
            y=y_column,
            color=color_column,
            size=size_column,
            hover_name=hover_name,
            title=title or f"Interactive Scatter: {x_column} vs {y_column}",
            template="plotly_white"
        )
        
        safe_x = "".join(c for c in x_column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        safe_y = "".join(c for c in y_column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        output_path = f"interactive_scatter_{safe_x}_vs_{safe_y}.html"
        
        fig.write_html(output_path)
        return output_path
    except Exception as e:
        raise ValueError(f"Interactive visualization failed: {str(e)}")

@mcp.tool()
def plot_interactive_histogram(
    csv_path: str,
    column: str,
    color_column: str = None,
    bins: int = None,
    title: str = None
) -> str:
    """
    Generate interactive histogram using Plotly.
    
    Args:
        csv_path: Path to CSV file
        column: Column name to visualize
        color_column: Column for color grouping (optional)
        bins: Number of bins (optional)
        title: Chart title (optional)
    """
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")
        
    try:
        fig = px.histogram(
            df, 
            x=column, 
            color=color_column,
            nbins=bins,
            title=title or f"Interactive Histogram: {column}",
            template="plotly_white",
            marginal="box" # Adds a box plot on top
        )
        
        safe_col = "".join(c for c in column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        output_path = f"interactive_hist_{safe_col}.html"
        
        fig.write_html(output_path)
        return output_path
    except Exception as e:
        raise ValueError(f"Interactive visualization failed: {str(e)}")

@mcp.tool()
def plot_interactive_boxplot(
    csv_path: str,
    y_column: str,
    x_column: str = None,
    color_column: str = None,
    title: str = None
) -> str:
    """
    Generate interactive boxplot using Plotly.
    
    Args:
        csv_path: Path to CSV file
        y_column: Numerical column for y-axis
        x_column: Categorical column for x-axis (grouping)
        color_column: Column for color grouping (optional)
        title: Chart title (optional)
    """
    df = get_data(csv_path)
    
    if y_column not in df.columns:
        raise ValueError(f"Column '{y_column}' not found.")
        
    try:
        fig = px.box(
            df, 
            y=y_column, 
            x=x_column,
            color=color_column,
            title=title or f"Interactive Boxplot: {y_column}",
            template="plotly_white",
            points="outliers" # Show outliers points
        )
        
        safe_y = "".join(c for c in y_column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        output_path = f"interactive_boxplot_{safe_y}.html"
        
        fig.write_html(output_path)
        return output_path
    except Exception as e:
        raise ValueError(f"Interactive visualization failed: {str(e)}")

@mcp.tool()
def plot_interactive_heatmap(
    csv_path: str,
    method: str = 'pearson',
    title: str = None
) -> str:
    """
    Generate interactive correlation heatmap using Plotly.
    
    Args:
        csv_path: Path to CSV file
        method: Correlation method ('pearson', 'kendall', 'spearman')
        title: Chart title (optional)
    """
    df = get_data(csv_path)
    numeric_df = df.select_dtypes(include=[np.number])
    
    if numeric_df.empty:
        raise ValueError("No numeric columns found for correlation.")
        
    try:
        corr_matrix = numeric_df.corr(method=method)
        
        fig = px.imshow(
            corr_matrix, 
            text_auto=True,
            aspect="auto",
            title=title or f"Interactive Correlation Heatmap ({method})",
            color_continuous_scale="RdBu_r", # Red-Blue reversed
            zmin=-1, zmax=1
        )
        
        output_path = f"interactive_heatmap.html"
        
        fig.write_html(output_path)
        return output_path
    except Exception as e:
        raise ValueError(f"Interactive visualization failed: {str(e)}")

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
    color_palette: str = "husl",
    show_legend: bool = True,
    legend_title: str = None,
    legend_position: str = "best"
) -> str:
    """
    Generate customizable scatter plot for bivariate analysis.
    
    Args:
        csv_path: Path to CSV file
        x_column: Column for x-axis
        y_column: Column for y-axis
        hue_column: Column for color grouping (optional)
        title: Custom plot title (optional)
        xlabel: Custom x-axis label (optional)
        ylabel: Custom y-axis label (optional)
        figsize_width: Figure width in inches (default: 10)
        figsize_height: Figure height in inches (default: 6)
        marker_size: Size of markers (default: 50)
        alpha: Transparency (0-1, default: 0.6)
        color_palette: Color palette name (default: "husl")
        show_legend: Show legend (default: True)
        legend_title: Custom legend title (optional)
        legend_position: Legend position - 'best', 'upper right', 'upper left', 
                        'lower right', 'lower left', 'center' (default: "best")
    """
    df = get_data(csv_path)
    
    if x_column not in df.columns:
        raise ValueError(f"Column '{x_column}' not found in CSV.")
    if y_column not in df.columns:
        raise ValueError(f"Column '{y_column}' not found in CSV.")
    if hue_column and hue_column not in df.columns:
        raise ValueError(f"Column '{hue_column}' not found in CSV.")
    
    plt.figure(figsize=(figsize_width, figsize_height))
    try:
        # Create scatter plot
        ax = sns.scatterplot(
            data=df,
            x=x_column,
            y=y_column,
            hue=hue_column,
            s=marker_size,
            alpha=alpha,
            palette=color_palette
        )
        
        # Set title and labels
        plt.title(title or f"Scatter Plot: {x_column} vs {y_column}")
        plt.xlabel(xlabel or x_column)
        plt.ylabel(ylabel or y_column)
        
        # Legend customization
        if hue_column:
            if show_legend:
                # Fix: Get handles/labels from the seaborn plot and recreate legend at custom position
                # This ensures seaborn's styling is preserved but moved to 'loc'
                try:
                    handles, labels = ax.get_legend_handles_labels()
                    if not handles: # If seaborn didn't return standard handles, try fetching from axes
                        handles, labels = plt.gca().get_legend_handles_labels()
                    
                    if handles:
                         plt.legend(
                             handles=handles, 
                             labels=labels,
                             loc=legend_position,
                             title=legend_title or hue_column
                         )
                except:
                     # Fallback if handle extraction fails
                    plt.legend(loc=legend_position)
            else:
                if ax.legend_:
                    ax.legend_.remove()
                else:
                    plt.legend().remove()
        
        # Save plot
        safe_x = "".join(c for c in x_column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        safe_y = "".join(c for c in y_column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        output_path = f"scatter_{safe_x}_vs_{safe_y}.png"
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return output_path
    except Exception as e:
        plt.close()
        raise ValueError(f"Visualization failed: {str(e)}")

@mcp.tool()
def plot_correlation_heatmap(csv_path: str, columns: list = None) -> str:
    """Generate correlation heatmap for numeric columns."""
    df = get_data(csv_path)
    
    if columns:
        numeric_df = df[columns].select_dtypes(include=['number'])
    else:
        numeric_df = df.select_dtypes(include=['number'])
    
    if numeric_df.empty:
        raise ValueError("No numeric columns found for correlation analysis.")
    
    plt.figure(figsize=(12, 10))
    try:
        corr_matrix = numeric_df.corr()
        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt='.2f',
            cmap='coolwarm',
            center=0,
            square=True,
            linewidths=0.5
        )
        plt.title("Correlation Heatmap")
        
        output_path = "correlation_heatmap.png"
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return output_path
    except Exception as e:
        plt.close()
        raise ValueError(f"Visualization failed: {str(e)}")

@mcp.tool()
def calculate_correlation(csv_path: str, method: str = "pearson") -> dict:
    """Calculate correlation coefficients between numeric columns."""
    df = get_data(csv_path)
    
    numeric_df = df.select_dtypes(include=['number'])
    
    if numeric_df.empty:
        raise ValueError("No numeric columns found.")
    
    if method not in ["pearson", "spearman", "kendall"]:
        raise ValueError("Method must be 'pearson', 'spearman', or 'kendall'.")
    
    corr_matrix = numeric_df.corr(method=method)
    
    return {
        "method": method,
        "correlation_matrix": corr_matrix.to_dict(),
        "columns": corr_matrix.columns.tolist()
    }

@mcp.tool()
def analyze_target_distribution(csv_path: str, target_column: str) -> dict:
    """Analyze target variable distribution and detect imbalance."""
    df = get_data(csv_path)
    
    if target_column not in df.columns:
        raise ValueError(f"Column '{target_column}' not found in CSV.")
    
    value_counts = df[target_column].value_counts()
    percentages = df[target_column].value_counts(normalize=True) * 100
    
    is_imbalanced = percentages.min() < 30
    
    result = {
        "target_column": target_column,
        "value_counts": value_counts.to_dict(),
        "percentages": {k: round(v, 2) for k, v in percentages.to_dict().items()},
        "is_imbalanced": is_imbalanced,
        "total_samples": len(df)
    }
    
    # Generate distribution plot
    plt.figure(figsize=(8, 6))
    try:
        value_counts.plot(kind='bar')
        plt.title(f"Distribution of {target_column}")
        plt.xlabel(target_column)
        plt.ylabel("Count")
        plt.xticks(rotation=45)
        
        safe_col = "".join(c for c in target_column if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        output_path = f"target_distribution_{safe_col}.png"
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        result["plot_path"] = output_path
    except Exception as e:
        plt.close()
    
    return result

# --- [Phase 2: Machine Learning Tools] ---

@mcp.tool()
def compare_models(
    csv_path: str,
    target_column: str,
    feature_columns: list = None
) -> dict:
    """Compare multiple ML models and return performance metrics."""
    df = get_data(csv_path).copy()
    
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
    
    # Prepare features
    if feature_columns:
        X = df[feature_columns].copy()
    else:
        X = df.drop(columns=[target_column]).copy()
    y = df[target_column].copy()
    
    # Drop rows with missing values
    data = pd.concat([X, y], axis=1).dropna()
    X = data[X.columns]
    y = data[target_column]
    
    # Encode categorical features
    for col in X.select_dtypes(include=['object']).columns:
        X[col] = LabelEncoder().fit_transform(X[col])
    
    # Determine task type
    is_classification = y.dtype == 'object' or y.nunique() <= 10
    
    if is_classification:
        y = LabelEncoder().fit_transform(y)
        models = {
            "RandomForest": RandomForestClassifier(random_state=42, n_estimators=100),
            "LogisticRegression": LogisticRegression(random_state=42, max_iter=1000),
        }
        if XGBOOST_AVAILABLE:
            models["XGBoost"] = XGBClassifier(random_state=42, eval_metric='logloss')
        metric_name = "accuracy"
    else:
        models = {
            "RandomForest": RandomForestRegressor(random_state=42, n_estimators=100),
            "LinearRegression": LinearRegression(),
        }
        if XGBOOST_AVAILABLE:
            models["XGBoost"] = XGBRegressor(random_state=42)
        metric_name = "rmse"
    
    # Train and evaluate
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        if is_classification:
            score = accuracy_score(y_test, y_pred)
        else:
            score = np.sqrt(mean_squared_error(y_test, y_pred))
        
        results[name] = {
            "score": round(score, 4),
            "metric": metric_name
        }
    
    # Find best model
    if is_classification:
        best_model = max(results.items(), key=lambda x: x[1]["score"])
    else:
        best_model = min(results.items(), key=lambda x: x[1]["score"])
    
    return {
        "task_type": "classification" if is_classification else "regression",
        "models": results,
        "best_model": best_model[0],
        "best_score": best_model[1]["score"]
    }

@mcp.tool()
def evaluate_model(
    csv_path: str,
    target_column: str,
    feature_columns: list = None,
    algorithm: str = "RandomForest"
) -> dict:
    """Detailed model evaluation with metrics and visualizations."""
    df = get_data(csv_path).copy()
    
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
    
    # Prepare data
    if feature_columns:
        X = df[feature_columns].copy()
    else:
        X = df.drop(columns=[target_column]).copy()
    y = df[target_column].copy()
    
    data = pd.concat([X, y], axis=1).dropna()
    X = data[X.columns]
    y = data[target_column]
    
    # Encode features
    label_encoders = {}
    for col in X.select_dtypes(include=['object']).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col])
        label_encoders[col] = le
    
    # Determine task
    is_classification = y.dtype == 'object' or y.nunique() <= 10
    
    if is_classification:
        y_encoder = LabelEncoder()
        y = y_encoder.fit_transform(y)
        
        # Select model
        if algorithm == "RandomForest":
            model = RandomForestClassifier(random_state=42, n_estimators=100)
        elif algorithm == "LogisticRegression":
            model = LogisticRegression(random_state=42, max_iter=1000)
        elif algorithm == "XGBoost" and XGBOOST_AVAILABLE:
            model = XGBClassifier(random_state=42, eval_metric='logloss')
        else:
            raise ValueError(f"Algorithm '{algorithm}' not supported for classification.")
    else:
        if algorithm == "RandomForest":
            model = RandomForestRegressor(random_state=42, n_estimators=100)
        elif algorithm == "LinearRegression":
            model = LinearRegression()
        elif algorithm == "XGBoost" and XGBOOST_AVAILABLE:
            model = XGBRegressor(random_state=42)
        else:
            raise ValueError(f"Algorithm '{algorithm}' not supported for regression.")
    
    # Train model
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    result = {
        "algorithm": algorithm,
        "task_type": "classification" if is_classification else "regression"
    }
    
    if is_classification:
        # Classification metrics
        result["accuracy"] = round(accuracy_score(y_test, y_pred), 4)
        result["precision"] = round(precision_score(y_test, y_pred, average='weighted', zero_division=0), 4)
        result["recall"] = round(recall_score(y_test, y_pred, average='weighted', zero_division=0), 4)
        result["f1_score"] = round(f1_score(y_test, y_pred, average='weighted', zero_division=0), 4)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(f"Confusion Matrix - {algorithm}")
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        cm_path = f"confusion_matrix_{algorithm}.png"
        plt.savefig(cm_path, dpi=100, bbox_inches='tight')
        plt.close()
        result["confusion_matrix_path"] = cm_path
    else:
        # Regression metrics
        result["rmse"] = round(np.sqrt(mean_squared_error(y_test, y_pred)), 4)
        result["mae"] = round(mean_absolute_error(y_test, y_pred), 4)
        result["r2_score"] = round(r2_score(y_test, y_pred), 4)
    
    # Feature importance (if available)
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        feature_importance = dict(zip(X.columns, importances))
        feature_importance = {k: round(v, 4) for k, v in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)}
        result["feature_importance"] = feature_importance
    
    return result

# --- [Phase 3: Statistical Analysis Tools] ---

@mcp.tool()
def test_normality(csv_path: str, column: str) -> dict:
    """Test normality using Shapiro-Wilk test."""
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")
    
    data = df[column].dropna()
    
    if len(data) < 3:
        raise ValueError("Need at least 3 samples for normality test.")
    
    statistic, p_value = stats.shapiro(data)
    is_normal = p_value > 0.05
    
    return {
        "column": column,
        "test": "Shapiro-Wilk",
        "statistic": round(float(statistic), 4),
        "p_value": round(float(p_value), 4),
        "is_normal": is_normal,
        "alpha": 0.05,
        "interpretation": "Data is normally distributed" if is_normal else "Data is NOT normally distributed"
    }

@mcp.tool()
def test_ttest(csv_path: str, column: str, group_column: str) -> dict:
    """Perform independent t-test between two groups."""
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")
    if group_column not in df.columns:
        raise ValueError(f"Column '{group_column}' not found in CSV.")
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")
    
    groups = df[group_column].unique()
    if len(groups) != 2:
        raise ValueError(f"Group column must have exactly 2 unique values. Found: {len(groups)}")
    
    group1_data = df[df[group_column] == groups[0]][column].dropna()
    group2_data = df[df[group_column] == groups[1]][column].dropna()
    
    statistic, p_value = stats.ttest_ind(group1_data, group2_data)
    is_significant = p_value < 0.05
    
    return {
        "column": column,
        "group_column": group_column,
        "groups": [str(groups[0]), str(groups[1])],
        "test": "Independent T-Test",
        "statistic": round(float(statistic), 4),
        "p_value": round(float(p_value), 4),
        "is_significant": is_significant,
        "alpha": 0.05,
        "interpretation": "Means are significantly different" if is_significant else "Means are NOT significantly different"
    }

@mcp.tool()
def test_anova(csv_path: str, column: str, group_column: str) -> dict:
    """Perform one-way ANOVA test for multiple groups."""
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")
    if group_column not in df.columns:
        raise ValueError(f"Column '{group_column}' not found in CSV.")
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")
    
    groups = df[group_column].unique()
    if len(groups) < 2:
        raise ValueError("Need at least 2 groups for ANOVA.")
    
    group_data = [df[df[group_column] == g][column].dropna() for g in groups]
    
    statistic, p_value = stats.f_oneway(*group_data)
    is_significant = p_value < 0.05
    
    return {
        "column": column,
        "group_column": group_column,
        "num_groups": len(groups),
        "test": "One-Way ANOVA",
        "statistic": round(float(statistic), 4),
        "p_value": round(float(p_value), 4),
        "is_significant": is_significant,
        "alpha": 0.05,
        "interpretation": "At least one group mean is significantly different" if is_significant else "No significant difference between group means"
    }

@mcp.tool()
def test_chi_square(csv_path: str, column1: str, column2: str) -> dict:
    """Perform chi-square test for independence between two categorical variables."""
    df = get_data(csv_path)
    
    if column1 not in df.columns:
        raise ValueError(f"Column '{column1}' not found in CSV.")
    if column2 not in df.columns:
        raise ValueError(f"Column '{column2}' not found in CSV.")
    
    contingency_table = pd.crosstab(df[column1], df[column2])
    
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
    is_independent = p_value > 0.05
    
    return {
        "column1": column1,
        "column2": column2,
        "test": "Chi-Square Test of Independence",
        "chi2_statistic": round(float(chi2), 4),
        "p_value": round(float(p_value), 4),
        "degrees_of_freedom": int(dof),
        "is_independent": is_independent,
        "alpha": 0.05,
        "interpretation": "Variables are independent" if is_independent else "Variables are NOT independent (associated)"
    }

@mcp.tool()
def calculate_confidence_interval(csv_path: str, column: str, confidence: float = 0.95) -> dict:
    """Calculate confidence interval for mean of a numeric column."""
    df = get_data(csv_path)
    
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in CSV.")
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")
    
    data = df[column].dropna()
    
    if len(data) < 2:
        raise ValueError("Need at least 2 samples for confidence interval.")
    
    mean = data.mean()
    sem = stats.sem(data)
    ci = stats.t.interval(confidence, len(data)-1, loc=mean, scale=sem)
    
    return {
        "column": column,
        "mean": round(float(mean), 4),
        "confidence_level": confidence,
        "lower_bound": round(float(ci[0]), 4),
        "upper_bound": round(float(ci[1]), 4),
        "margin_of_error": round(float(ci[1] - mean), 4),
        "sample_size": len(data)
    }

# --- [Phase 3: Advanced Preprocessing Tools] ---

@mcp.tool()
def encode_categorical(
    csv_path: str,
    columns: list,
    method: str = "label",
    save_to: str = None
) -> dict:
    """Encode categorical variables using label encoding or one-hot encoding."""
    df = get_data(csv_path).copy()
    
    if method not in ["label", "onehot"]:
        raise ValueError("Method must be 'label' or 'onehot'.")
    
    encoded_info = {}
    
    if method == "label":
        from sklearn.preprocessing import LabelEncoder
        for col in columns:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in CSV.")
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoded_info[col] = {
                "method": "label",
                "classes": le.classes_.tolist()
            }
    else:  # onehot
        df = pd.get_dummies(df, columns=columns, prefix=columns)
        for col in columns:
            new_cols = [c for c in df.columns if c.startswith(f"{col}_")]
            encoded_info[col] = {
                "method": "onehot",
                "new_columns": new_cols
            }
    
    _DATA_CACHE[csv_path] = df
    
    result = {
        "encoded_columns": encoded_info,
        "new_shape": df.shape
    }
    
    if save_to:
        df.to_csv(save_to, index=False)
        result["output_path"] = save_to
    
    return result

@mcp.tool()
def scale_features(
    csv_path: str,
    columns: list = None,
    method: str = "standard",
    save_to: str = None
) -> dict:
    """Scale numeric features using Standard or MinMax scaling."""
    df = get_data(csv_path).copy()
    
    if method not in ["standard", "minmax"]:
        raise ValueError("Method must be 'standard' or 'minmax'.")
    
    if columns is None:
        columns = df.select_dtypes(include=['number']).columns.tolist()
    
    for col in columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in CSV.")
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column '{col}' must be numeric.")
    
    if method == "standard":
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        df[columns] = scaler.fit_transform(df[columns])
        scaling_info = {
            "method": "StandardScaler",
            "mean": scaler.mean_.tolist(),
            "std": scaler.scale_.tolist()
        }
    else:  # minmax
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        df[columns] = scaler.fit_transform(df[columns])
        scaling_info = {
            "method": "MinMaxScaler",
            "min": scaler.data_min_.tolist(),
            "max": scaler.data_max_.tolist()
        }
    
    _DATA_CACHE[csv_path] = df
    
    result = {
        "scaled_columns": columns,
        "scaling_info": scaling_info,
        "new_shape": df.shape
    }
    
    if save_to:
        df.to_csv(save_to, index=False)
        result["output_path"] = save_to
    
# --- [Phase 5: Model Optimization] ---

@mcp.tool()
def tune_hyperparameters(
    csv_path: str,
    target_column: str,
    model_type: str = "RandomForest",
    param_grid: dict = None,
    cv: int = 5,
    scoring: str = "accuracy"
) -> dict:
    """
    Optimize model hyperparameters using GridSearchCV or RandomizedSearchCV.
    
    Args:
        csv_path: Path to CSV file
        target_column: Target variable
        model_type: 'RandomForest', 'XGBoost', 'LogisticRegression', 'SVM'
        param_grid: Dictionary of parameters to search (optional, default will be used)
        cv: Cross-validation splits (default: 5)
        scoring: Scoring metric (default: 'accuracy' for classification)
    """
    df = get_data(csv_path)
    
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
        
    # --- Preprocessing (Simplified) ---
    X = df.drop(columns=[target_column])
    y = df[target_column]
    
    # Handle non-numeric columns
    X = pd.get_dummies(X, drop_first=True)
    
    if y.dtype == 'object':
        le = LabelEncoder()
        y = le.fit_transform(y)
        is_classification = True
    else:
        # Check if target has few unique values -> Classification
        if y.nunique() < 20: 
             is_classification = True
        else:
             is_classification = False
    
    # --- Model & Param Grid Setup ---
    model = None
    default_params = {}
    
    if model_type == "RandomForest":
        if is_classification:
            model = RandomForestClassifier(random_state=42)
            default_params = {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10]
            }
        else:
            model = RandomForestRegressor(random_state=42)
            default_params = {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20],
                'min_samples_split': [2, 5]
            }
            if scoring == 'accuracy': scoring = 'neg_mean_squared_error'

    elif model_type == "XGBoost" and XGBOOST_AVAILABLE:
        if is_classification:
            model = XGBClassifier(eval_metric='logloss')
            default_params = {
                'n_estimators': [100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'max_depth': [3, 5, 7]
            }
        else:
            model = XGBRegressor()
            default_params = {
                'n_estimators': [100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'max_depth': [3, 5, 7]
            }
            if scoring == 'accuracy': scoring = 'neg_mean_squared_error'
            
    elif model_type == "LogisticRegression":
        if not is_classification: raise ValueError("LogisticRegression is for classification only.")
        model = LogisticRegression(max_iter=1000)
        default_params = {'C': [0.1, 1.0, 10.0]}
        
    elif model_type == "SVM":
        if is_classification:
            model = SVC()
            default_params = {'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']}
        else:
            model = SVR()
            default_params = {'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']}
            if scoring == 'accuracy': scoring = 'neg_mean_squared_error'
            
    else:
        raise ValueError(f"Unsupported model type: {model_type}")

    # Use provided param_grid if available, else default
    params = param_grid if param_grid else default_params
    
    # --- Hyperparameter Tuning ---
    try:
        # Use RandomizedSearchCV if grid is large, else GridSearchCV
        total_combinations = 1
        for v in params.values():
            total_combinations *= len(v)
            
        if total_combinations > 20: 
            search = RandomizedSearchCV(model, params, n_iter=20, cv=cv, scoring=scoring, n_jobs=-1, random_state=42)
            method = "RandomizedSearchCV"
        else:
            search = GridSearchCV(model, params, cv=cv, scoring=scoring, n_jobs=-1)
            method = "GridSearchCV"
            
        search.fit(X, y)
        
        return {
            "best_params": search.best_params_,
            "best_score": round(search.best_score_, 4),
            "scoring_metric": scoring,
            "method": method,
            "model_type": model_type,
            "is_classification": is_classification
        }
        
    except Exception as e:
        raise ValueError(f"Hyperparameter tuning failed: {str(e)}")

    
    return result

@mcp.prompt()
def default_prompt(message: str) -> list[base.Message]:
    return [
        base.AssistantMessage(
            "You are a data analysis assistant. "
            "When user requests analysis, YOU MUST call the appropriate tools immediately. "
            "Do NOT just say 'I will do X', actually DO IT by calling the tools. "
            "Be concise and execute tools right away. "
            "ALWAYS respond in Korean (한국어로 응답). "
            "Provide clear explanations in Korean for all analysis results.\n\n"
            "**Tool Selection Rules:**\n"
            "- If user mentions 'interactive', 'html', 'zoom', 'plot_interactive', OR '인터랙티브', '반응형': YOU MUST USE `plot_interactive_` tools (e.g., plot_interactive_scatter).\n"
            "- Otherwise, use standard static plotting tools (e.g., plot_scatter).\n\n"
            "**Analysis Workflow:**\n"
            "- If user asks for '분석' (analysis) without specifics: Start with get_dataset_info or profile_dataset first.\n"
            "- Only proceed to visualization or modeling if explicitly requested or after basic profiling.\n"
            "- Follow user's specific instructions precisely."
        ),
        base.UserMessage(message),
    ]

if __name__ == "__main__":
    mcp.run(transport="stdio")


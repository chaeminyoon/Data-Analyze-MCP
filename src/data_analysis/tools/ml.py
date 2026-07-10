"""Phase 2 & 5: machine-learning tools (compare, evaluate, tune)."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC, SVR

from ..cache import get_data
from ..config import CLASSIFICATION_MAX_UNIQUE
from ..helpers import is_classification_target, require_columns, safe_name, save_current_figure
from ..server import mcp

try:
    from xgboost import XGBClassifier, XGBRegressor

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


def _prepare_xy(df: pd.DataFrame, target_column: str, feature_columns: list | None):
    """Split into X/y, drop NaN rows, and label-encode object features.

    Returns (X, y) where X is fully numeric.  Shared by compare/evaluate.
    """
    require_columns(df, target_column)
    X = df[feature_columns].copy() if feature_columns else df.drop(columns=[target_column]).copy()
    y = df[target_column].copy()

    data = pd.concat([X, y], axis=1).dropna()
    X, y = data[X.columns], data[target_column]

    for col in X.select_dtypes(include=["object"]).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    return X, y


@mcp.tool()
def compare_models(csv_path: str, target_column: str, feature_columns: list = None) -> dict:
    """Compare multiple ML models and return performance metrics."""
    df = get_data(csv_path).copy()
    X, y = _prepare_xy(df, target_column, feature_columns)

    is_classification = is_classification_target(y)
    if is_classification:
        y = LabelEncoder().fit_transform(y)
        models = {
            "RandomForest": RandomForestClassifier(random_state=42, n_estimators=100),
            "LogisticRegression": LogisticRegression(random_state=42, max_iter=1000),
        }
        if XGBOOST_AVAILABLE:
            models["XGBoost"] = XGBClassifier(random_state=42, eval_metric="logloss")
        metric_name = "accuracy"
    else:
        models = {
            "RandomForest": RandomForestRegressor(random_state=42, n_estimators=100),
            "LinearRegression": LinearRegression(),
        }
        if XGBOOST_AVAILABLE:
            models["XGBoost"] = XGBRegressor(random_state=42)
        metric_name = "rmse"

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        if is_classification:
            score = accuracy_score(y_test, y_pred)
        else:
            score = np.sqrt(mean_squared_error(y_test, y_pred))
        results[name] = {"score": round(float(score), 4), "metric": metric_name}

    if is_classification:
        best = max(results.items(), key=lambda kv: kv[1]["score"])
    else:
        best = min(results.items(), key=lambda kv: kv[1]["score"])

    return {
        "task_type": "classification" if is_classification else "regression",
        "models": results,
        "best_model": best[0],
        "best_score": best[1]["score"],
    }


def _build_estimator(algorithm: str, is_classification: bool):
    """Return an untrained estimator for ``algorithm`` and task type."""
    classifiers = {
        "RandomForest": lambda: RandomForestClassifier(random_state=42, n_estimators=100),
        "LogisticRegression": lambda: LogisticRegression(random_state=42, max_iter=1000),
    }
    regressors = {
        "RandomForest": lambda: RandomForestRegressor(random_state=42, n_estimators=100),
        "LinearRegression": LinearRegression,
    }
    if XGBOOST_AVAILABLE:
        classifiers["XGBoost"] = lambda: XGBClassifier(random_state=42, eval_metric="logloss")
        regressors["XGBoost"] = lambda: XGBRegressor(random_state=42)

    table = classifiers if is_classification else regressors
    task = "classification" if is_classification else "regression"
    if algorithm not in table:
        raise ValueError(f"Algorithm '{algorithm}' not supported for {task}.")
    return table[algorithm]()


@mcp.tool()
def evaluate_model(
    csv_path: str,
    target_column: str,
    feature_columns: list = None,
    algorithm: str = "RandomForest",
) -> dict:
    """Detailed model evaluation with metrics and visualizations."""
    df = get_data(csv_path).copy()
    X, y = _prepare_xy(df, target_column, feature_columns)

    is_classification = is_classification_target(y)
    if is_classification:
        y = LabelEncoder().fit_transform(y)
    model = _build_estimator(algorithm, is_classification)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    result = {
        "algorithm": algorithm,
        "task_type": "classification" if is_classification else "regression",
    }

    if is_classification:
        result["accuracy"] = round(accuracy_score(y_test, y_pred), 4)
        result["precision"] = round(
            precision_score(y_test, y_pred, average="weighted", zero_division=0), 4
        )
        result["recall"] = round(
            recall_score(y_test, y_pred, average="weighted", zero_division=0), 4
        )
        result["f1_score"] = round(
            f1_score(y_test, y_pred, average="weighted", zero_division=0), 4
        )

        plt.figure(figsize=(8, 6))
        sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt="d", cmap="Blues")
        plt.title(f"Confusion Matrix - {algorithm}")
        plt.ylabel("True Label")
        plt.xlabel("Predicted Label")
        result["confusion_matrix_path"] = save_current_figure(
            f"confusion_matrix_{safe_name(algorithm)}.png"
        )
    else:
        result["rmse"] = round(np.sqrt(mean_squared_error(y_test, y_pred)), 4)
        result["mae"] = round(mean_absolute_error(y_test, y_pred), 4)
        result["r2_score"] = round(r2_score(y_test, y_pred), 4)

    if hasattr(model, "feature_importances_"):
        importance = dict(zip(X.columns, model.feature_importances_))
        result["feature_importance"] = {
            k: round(float(v), 4)
            for k, v in sorted(importance.items(), key=lambda kv: kv[1], reverse=True)
        }

    return result


# Default hyper-parameter grids per model type.
_PARAM_GRIDS = {
    "RandomForest": {
        "n_estimators": [50, 100, 200],
        "max_depth": [None, 10, 20, 30],
        "min_samples_split": [2, 5, 10],
    },
    "XGBoost": {
        "n_estimators": [100, 200],
        "learning_rate": [0.01, 0.1, 0.3],
        "max_depth": [3, 5, 7],
    },
    "LogisticRegression": {"C": [0.1, 1.0, 10.0]},
    "SVM": {"C": [0.1, 1, 10], "kernel": ["linear", "rbf"]},
}


def _build_tuning_estimator(model_type: str, is_classification: bool):
    if model_type == "RandomForest":
        return (RandomForestClassifier if is_classification else RandomForestRegressor)(
            random_state=42
        )
    if model_type == "XGBoost":
        if not XGBOOST_AVAILABLE:
            raise ValueError("XGBoost is not installed.")
        return XGBClassifier(eval_metric="logloss") if is_classification else XGBRegressor()
    if model_type == "LogisticRegression":
        if not is_classification:
            raise ValueError("LogisticRegression is for classification only.")
        return LogisticRegression(max_iter=1000)
    if model_type == "SVM":
        return SVC() if is_classification else SVR()
    raise ValueError(f"Unsupported model type: {model_type}")


@mcp.tool()
def tune_hyperparameters(
    csv_path: str,
    target_column: str,
    model_type: str = "RandomForest",
    param_grid: dict = None,
    cv: int = 5,
    scoring: str = "accuracy",
) -> dict:
    """Optimize model hyperparameters using GridSearchCV or RandomizedSearchCV.

    Args:
        model_type: 'RandomForest', 'XGBoost', 'LogisticRegression', 'SVM'
        param_grid: Parameters to search (defaults are used if omitted)
        cv: Cross-validation splits
        scoring: Scoring metric (auto-switched to a regression metric when the
            target is continuous and the default 'accuracy' was left in place)
    """
    df = get_data(csv_path)
    require_columns(df, target_column)

    X = pd.get_dummies(df.drop(columns=[target_column]), drop_first=True)
    y = df[target_column]

    # dtype-agnostic: pandas 3 strings are 'str' dtype, not 'object'
    if not pd.api.types.is_numeric_dtype(y):
        y = LabelEncoder().fit_transform(y)
        is_classification = True
    else:
        is_classification = y.nunique() < 2 * CLASSIFICATION_MAX_UNIQUE

    model = _build_tuning_estimator(model_type, is_classification)
    if not is_classification and scoring == "accuracy":
        scoring = "neg_mean_squared_error"

    params = param_grid or _PARAM_GRIDS.get(model_type)
    if not params:
        raise ValueError(f"No parameter grid available for model type: {model_type}")

    try:
        total_combinations = 1
        for values in params.values():
            total_combinations *= len(values)

        if total_combinations > 20:
            search = RandomizedSearchCV(
                model, params, n_iter=20, cv=cv, scoring=scoring, n_jobs=-1, random_state=42
            )
            method = "RandomizedSearchCV"
        else:
            search = GridSearchCV(model, params, cv=cv, scoring=scoring, n_jobs=-1)
            method = "GridSearchCV"

        search.fit(X, y)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Hyperparameter tuning failed: {exc}") from exc

    return {
        "best_params": search.best_params_,
        "best_score": round(float(search.best_score_), 4),
        "scoring_metric": scoring,
        "method": method,
        "model_type": model_type,
        "is_classification": is_classification,
    }

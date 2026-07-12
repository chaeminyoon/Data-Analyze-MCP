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
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC, SVR

from .. import theming
from ..cache import get_data
from ..config import CLASSIFICATION_MAX_UNIQUE
from ..helpers import (
    is_classification_target,
    require_columns,
    safe_name,
    save_current_figure,
    string_columns,
)
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

    for col in string_columns(X):
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
        sns.heatmap(
            confusion_matrix(y_test, y_pred), annot=True, fmt="d",
            cmap=theming.sequential_cmap(),
        )
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


# --- [Model diagnostic charts] ----------------------------------------------
def _fit_for_diagnostics(csv_path, target_column, feature_columns, algorithm,
                         need_proba=False, need_regression=False):
    """Train/test split + fit, shared by the diagnostic chart tools."""
    df = get_data(csv_path).copy()
    X, y = _prepare_xy(df, target_column, feature_columns)
    is_classification = is_classification_target(y)
    if need_proba and not is_classification:
        raise ValueError(f"'{target_column}' is continuous — this chart needs a "
                         "classification target.")
    if need_regression and is_classification:
        raise ValueError(f"'{target_column}' looks categorical — this chart needs "
                         "a regression target.")

    classes = None
    if is_classification:
        encoder = LabelEncoder()
        y = encoder.fit_transform(y)
        classes = [str(c) for c in encoder.classes_]
    model = _build_estimator(algorithm, is_classification)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model.fit(X_train, y_train)
    return model, X, X_test, y_test, classes


@mcp.tool()
def plot_roc_pr(
    csv_path: str,
    target_column: str,
    feature_columns: list = None,
    algorithm: str = "RandomForest",
) -> dict:
    """ROC and Precision-Recall curves side by side, with AUC / AP scores.

    Binary targets get one curve per panel; multiclass targets get one-vs-rest
    curves (at most 8 classes). PR is included because ROC alone flatters
    models on imbalanced data.
    """
    model, _, X_test, y_test, classes = _fit_for_diagnostics(
        csv_path, target_column, feature_columns, algorithm, need_proba=True
    )
    if not hasattr(model, "predict_proba"):
        raise ValueError(f"{algorithm} does not expose predict_proba.")
    if len(classes) > 8:
        raise ValueError(f"{len(classes)} classes — one-vs-rest curves are "
                         "unreadable beyond 8. Reduce classes first.")
    proba = model.predict_proba(X_test)

    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(13, 5.5))
    try:
        palette = theming.palette()
        scores = {}
        binary = len(classes) == 2
        targets = [1] if binary else range(len(classes))
        for idx, k in enumerate(targets):
            y_bin = (np.asarray(y_test) == k).astype(int)
            p = proba[:, k]
            fpr, tpr, _ = roc_curve(y_bin, p)
            prec, rec, _ = precision_recall_curve(y_bin, p)
            roc_auc, ap = auc(fpr, tpr), average_precision_score(y_bin, p)
            label = classes[k] if not binary else classes[1]
            scores[label] = {"roc_auc": round(float(roc_auc), 4),
                             "average_precision": round(float(ap), 4)}
            color = palette[idx % len(palette)]
            ax_roc.plot(fpr, tpr, color=color, label=f"{label} (AUC {roc_auc:.3f})")
            ax_pr.plot(rec, prec, color=color, label=f"{label} (AP {ap:.3f})")

        chance_color = plt.rcParams.get("axes.edgecolor", "#c3c2b7")
        ax_roc.plot([0, 1], [0, 1], linestyle="--", linewidth=1.2,
                    color=chance_color, label="Chance")
        base_rate = float(np.mean(np.asarray(y_test) == (1 if binary else y_test)))
        if binary:
            base_rate = float(np.mean(y_test))
            ax_pr.axhline(base_rate, linestyle="--", linewidth=1.2,
                          color=chance_color, label=f"Base rate {base_rate:.2f}")
        ax_roc.set_xlabel("False positive rate")
        ax_roc.set_ylabel("True positive rate")
        ax_roc.set_title("ROC", loc="left")
        ax_pr.set_xlabel("Recall")
        ax_pr.set_ylabel("Precision")
        ax_pr.set_title("Precision-Recall", loc="left")
        for ax in (ax_roc, ax_pr):
            ax.legend(fontsize=9)
        fig.suptitle(f"{algorithm} — {target_column}", fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        path = save_current_figure(f"roc_pr_{safe_name(algorithm)}.png")
        return {"algorithm": algorithm, "classes": classes,
                "scores": scores, "plot_path": path}
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_calibration(
    csv_path: str,
    target_column: str,
    feature_columns: list = None,
    algorithm: str = "RandomForest",
    n_bins: int = 10,
) -> dict:
    """Calibration curve for a binary classifier — are the probabilities honest?

    A model can rank well (high AUC) while its probabilities are far off;
    if you act on thresholds, calibration is the chart that matters.
    """
    model, _, X_test, y_test, classes = _fit_for_diagnostics(
        csv_path, target_column, feature_columns, algorithm, need_proba=True
    )
    if len(classes) != 2:
        raise ValueError("Calibration curves need a binary target "
                         f"(got {len(classes)} classes).")
    if not hasattr(model, "predict_proba"):
        raise ValueError(f"{algorithm} does not expose predict_proba.")
    proba = model.predict_proba(X_test)[:, 1]
    frac_pos, mean_pred = calibration_curve(y_test, proba, n_bins=n_bins,
                                            strategy="quantile")

    plt.figure(figsize=(7, 6))
    try:
        chance_color = plt.rcParams.get("axes.edgecolor", "#c3c2b7")
        plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1.2,
                 color=chance_color, label="Perfectly calibrated")
        plt.plot(mean_pred, frac_pos, marker="o",
                 color=theming.palette()[0], label=algorithm)
        plt.xlabel("Predicted probability")
        plt.ylabel("Observed frequency")
        plt.title(f"Calibration — {algorithm} on {target_column}")
        plt.legend()
        path = save_current_figure(f"calibration_{safe_name(algorithm)}.png")
        gap = float(np.mean(np.abs(frac_pos - mean_pred)))
        return {"algorithm": algorithm, "n_bins": n_bins,
                "mean_calibration_gap": round(gap, 4), "plot_path": path}
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_feature_importance(
    csv_path: str,
    target_column: str,
    feature_columns: list = None,
    algorithm: str = "RandomForest",
    top_n: int = 15,
) -> dict:
    """Horizontal bar chart of feature importances (or |coefficients|).

    One hue only — the bars encode magnitude, not identity, so a rainbow
    here would be decoration. Values are direct-labeled.
    """
    model, X, _, _, _ = _fit_for_diagnostics(
        csv_path, target_column, feature_columns, algorithm
    )
    if hasattr(model, "feature_importances_"):
        values, kind = model.feature_importances_, "feature_importances"
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        values = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)
        kind = "abs_coefficients"
    else:
        raise ValueError(f"{algorithm} exposes neither feature_importances_ nor coef_.")

    order = np.argsort(values)[::-1][:top_n]
    names = [str(X.columns[i]) for i in order][::-1]
    vals = values[order][::-1]

    plt.figure(figsize=(9, max(3.5, 0.38 * len(names) + 1)))
    try:
        ax = plt.gca()
        ax.barh(names, vals, color=theming.palette()[0],
                edgecolor=theming.face_color(), linewidth=1.2)
        from ..helpers import add_bar_labels

        add_bar_labels(ax, fmt="{:,.3f}", orientation="horizontal")
        ax.set_xlabel(kind.replace("_", " "))
        ax.set_title(f"{kind.replace('_', ' ').title()} — {algorithm}", loc="left")
        path = save_current_figure(f"feature_importance_{safe_name(algorithm)}.png")
        return {
            "algorithm": algorithm, "kind": kind,
            "importances": {str(X.columns[i]): round(float(values[i]), 4) for i in order},
            "plot_path": path,
        }
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc


@mcp.tool()
def plot_residuals(
    csv_path: str,
    target_column: str,
    feature_columns: list = None,
    algorithm: str = "RandomForest",
) -> dict:
    """Residual diagnostics for a regression model: residual-vs-predicted +
    residual histogram. Curvature or a funnel shape in the left panel means
    the model is missing structure that R² alone won't reveal."""
    model, _, X_test, y_test, _ = _fit_for_diagnostics(
        csv_path, target_column, feature_columns, algorithm, need_regression=True
    )
    y_pred = model.predict(X_test)
    residuals = np.asarray(y_test) - y_pred

    fig, (ax_sc, ax_hist) = plt.subplots(
        1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.5, 1]}
    )
    try:
        primary = theming.palette()[0]
        zero_color = plt.rcParams.get("axes.edgecolor", "#c3c2b7")
        ax_sc.scatter(y_pred, residuals, s=28, alpha=0.55, color=primary,
                      edgecolors="none")
        ax_sc.axhline(0, linestyle="--", linewidth=1.2, color=zero_color)
        ax_sc.set_xlabel("Predicted")
        ax_sc.set_ylabel("Residual (actual - predicted)")
        ax_sc.set_title("Residuals vs predicted", loc="left")

        ax_hist.hist(residuals, bins=30, color=primary,
                     edgecolor=theming.face_color(), linewidth=0.8)
        ax_hist.set_xlabel("Residual")
        ax_hist.set_ylabel("Count")
        ax_hist.set_title("Residual distribution", loc="left")

        fig.suptitle(f"{algorithm} — {target_column}", fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        path = save_current_figure(f"residuals_{safe_name(algorithm)}.png")
        return {
            "algorithm": algorithm,
            "rmse": round(float(np.sqrt(np.mean(residuals ** 2))), 4),
            "mean_residual": round(float(np.mean(residuals)), 4),
            "plot_path": path,
        }
    except Exception as exc:  # noqa: BLE001
        plt.close()
        raise ValueError(f"Visualization failed: {exc}") from exc

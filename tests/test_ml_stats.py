"""ML and statistics tools on small synthetic data."""
import pytest

from data_analysis.tools import ml
from data_analysis.tools import statistics as st


def test_compare_models_classifies_string_target(churn_csv):
    """Regression: pandas 3 'str' dtype broke y.dtype == 'object' target checks."""
    result = ml.compare_models(churn_csv, "churn", feature_columns=["tenure", "charges"])
    assert result["task_type"] == "classification"
    assert result["best_model"] in result["models"]


def test_evaluate_model_metrics(churn_csv):
    result = ml.evaluate_model(churn_csv, "churn", feature_columns=["tenure", "charges"])
    assert {"accuracy", "precision", "recall", "f1_score"} <= result.keys()
    assert "feature_importance" in result


def test_tune_hyperparameters_returns_cleanly(house_csv):
    """Regression: v3.1 ended with unreachable `return result` (undefined name)."""
    result = ml.tune_hyperparameters(
        house_csv, "price", model_type="RandomForest",
        param_grid={"n_estimators": [10]}, cv=2,
    )
    assert result["best_params"] == {"n_estimators": 10}
    assert result["is_classification"] is False
    assert result["scoring_metric"] == "neg_mean_squared_error"


def test_statistics_suite(churn_csv):
    anova = st.test_anova(churn_csv, "charges", "contract")
    assert anova["test"] == "One-Way ANOVA" and anova["is_significant"]

    ttest = st.test_ttest(churn_csv, "charges", "contract")
    assert "p_value" in ttest

    chi2 = st.test_chi_square(churn_csv, "contract", "churn")
    assert chi2["degrees_of_freedom"] == 1

    ci = st.calculate_confidence_interval(churn_csv, "tenure")
    assert ci["lower_bound"] < ci["mean"] < ci["upper_bound"]


def test_statistics_input_validation(churn_csv):
    with pytest.raises(ValueError, match="must be numeric"):
        st.test_normality(churn_csv, "contract")
    with pytest.raises(ValueError, match="exactly 2 unique"):
        st.test_ttest(churn_csv, "charges", "tenure")
    with pytest.raises(ValueError):
        st.calculate_correlation(churn_csv, method="magic")

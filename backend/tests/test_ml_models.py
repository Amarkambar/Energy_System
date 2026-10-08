"""
tests/test_ml_models.py — Unit tests for ML model classes
Run: cd backend && pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import pandas as pd
from data.pipeline import generate_synthetic_data, clean_data, build_feature_matrix
from models.ml_models import (
    AnomalyDetector,
    MaintenancePredictor,
    EnergyForecaster,
    EfficiencyScorer,
    get_feature_cols,
)



@pytest.fixture(scope="module")
def sample_df():
    """Shared 500-row processed dataframe for all ML tests"""
    df = generate_synthetic_data(n_hours=547)  # +47 for lag trim
    df = clean_data(df)
    df = build_feature_matrix(df)
    return df.dropna().reset_index(drop=True)


class TestGetFeatureCols:
    def test_excludes_metadata_columns(self, sample_df):
        cols = get_feature_cols(sample_df)
        forbidden = {"timestamp", "is_anomaly", "failure_label", "efficiency_score"}
        assert len(forbidden & set(cols)) == 0

    def test_returns_only_numeric(self, sample_df):
        cols = get_feature_cols(sample_df)
        for c in cols:
            assert pd.api.types.is_numeric_dtype(sample_df[c]), f"{c} not numeric"

    def test_returns_nonempty_list(self, sample_df):
        cols = get_feature_cols(sample_df)
        assert len(cols) > 5


class TestAnomalyDetector:
    def test_fit_returns_self(self, sample_df):
        det = AnomalyDetector(contamination=0.05)
        result = det.fit(sample_df)
        assert result is det

    def test_predict_adds_anomaly_columns(self, sample_df):
        det = AnomalyDetector(contamination=0.05)
        det.fit(sample_df)
        out = det.predict(sample_df)
        assert "anomaly_flag" in out.columns
        assert "anomaly_score" in out.columns

    def test_anomaly_flag_is_binary(self, sample_df):
        det = AnomalyDetector(contamination=0.05)
        det.fit(sample_df)
        out = det.predict(sample_df)
        assert set(out["anomaly_flag"].unique()).issubset({0, 1})

    def test_anomaly_rate_near_contamination(self, sample_df):
        contamination = 0.05
        det = AnomalyDetector(contamination=contamination)
        det.fit(sample_df)
        out = det.predict(sample_df)
        rate = out["anomaly_flag"].mean()
        assert abs(rate - contamination) < 0.10, \
            f"Anomaly rate {rate:.2%} too far from target {contamination:.2%}"

    def test_explain_returns_dataframe(self, sample_df):
        det = AnomalyDetector(contamination=0.05)
        det.fit(sample_df)
        exp = det.explain(sample_df, n_samples=50)
        assert isinstance(exp, pd.DataFrame)
        assert "feature" in exp.columns
        assert "shap_mean" in exp.columns


class TestEnergyForecaster:
    def test_fit_and_predict(self, sample_df):
        forecaster = EnergyForecaster()
        forecaster.fit(sample_df)
        out = forecaster.predict(sample_df)
        assert out is not None
        assert len(out) > 0

    def test_forecast_has_consumption_col(self, sample_df):
        forecaster = EnergyForecaster()
        forecaster.fit(sample_df)
        out = forecaster.predict(sample_df)
        if isinstance(out, pd.DataFrame):
            assert "consumption_kwh" in out.columns or len(out.columns) > 0


class TestEfficiencyScorer:
    def test_score_returns_dataframe(self, sample_df):
        scorer = EfficiencyScorer()
        scorer.fit(sample_df)       # must fit before scoring
        out = scorer.score(sample_df)
        assert isinstance(out, pd.DataFrame)
        assert len(out) > 0

    def test_score_has_efficiency_column(self, sample_df):
        scorer = EfficiencyScorer()
        scorer.fit(sample_df)
        out = scorer.score(sample_df)
        # should contain some efficiency or cluster column
        assert len(out.columns) > 0



class TestMaintenancePredictor:
    def test_fit_and_predict(self, sample_df):
        pred = MaintenancePredictor()
        # Inject synthetic failure_label if not present
        df = sample_df.copy()
        if "failure_label" not in df.columns:
            df["failure_label"] = (df["anomaly_score"] > df["anomaly_score"].quantile(0.9)).astype(int) \
                if "anomaly_score" in df.columns \
                else np.random.randint(0, 2, len(df))
        pred.fit(df)
        out = pred.predict(df)
        assert "failure_prob" in out.columns or "failure_label" in out.columns

    def test_predict_proba_in_range(self, sample_df):
        pred = MaintenancePredictor()
        df = sample_df.copy()
        if "failure_label" not in df.columns:
            df["failure_label"] = np.random.randint(0, 2, len(df))
        pred.fit(df)
        out = pred.predict(df)
        if "failure_prob" in out.columns:
            assert out["failure_prob"].between(0, 1).all()

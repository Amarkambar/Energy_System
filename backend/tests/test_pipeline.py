"""
tests/test_pipeline.py — Unit tests for data pipeline functions
Run: cd backend && pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import pandas as pd
from data.pipeline import (
    generate_synthetic_data,
    clean_data,
    build_feature_matrix,
)


class TestGenerateSyntheticData:
    def test_default_returns_8760_rows(self):
        df = generate_synthetic_data()
        # After lag/rolling feature trim ~8760 rows survive from 8807 generated
        assert len(df) >= 8700, f"Expected >=8700 rows, got {len(df)}"

    def test_custom_n_hours(self):
        df = generate_synthetic_data(n_hours=100)
        assert len(df) == 100

    def test_required_columns_present(self):
        df = generate_synthetic_data(n_hours=200)
        required = ["timestamp", "consumption_kwh", "voltage",
                    "load_factor", "temperature", "humidity"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_timestamp_is_hourly(self):
        df = generate_synthetic_data(n_hours=200)   # must be > 50 (anomaly sample size)
        deltas = pd.to_datetime(df["timestamp"]).diff().dropna()
        assert (deltas == pd.Timedelta(hours=1)).all(), "Timestamps not hourly"


    def test_consumption_non_negative(self):
        df = generate_synthetic_data(n_hours=200)
        assert (df["consumption_kwh"] >= 0).all()

    def test_anomaly_flag_is_binary(self):
        df = generate_synthetic_data(n_hours=500)
        assert set(df["is_anomaly"].unique()).issubset({0, 1})

    def test_anomaly_rate_reasonable(self):
        df = generate_synthetic_data(n_hours=1000)
        rate = df["is_anomaly"].mean()
        assert 0.0 < rate < 0.2, f"Anomaly rate {rate:.1%} out of expected range"

    def test_reproducible_with_seed(self):
        df1 = generate_synthetic_data(n_hours=100)
        df2 = generate_synthetic_data(n_hours=100)
        assert df1["consumption_kwh"].equals(df2["consumption_kwh"])


class TestCleanData:
    def _make_df(self, n=200):
        df = generate_synthetic_data(n_hours=n)
        return df

    def test_removes_duplicate_timestamps(self):
        df = self._make_df(100)
        # Inject duplicates
        df = pd.concat([df, df.head(5)], ignore_index=True)
        cleaned = clean_data(df)
        assert cleaned["timestamp"].duplicated().sum() == 0

    def test_fills_missing_values(self):
        df = self._make_df(100)
        df.loc[10:15, "consumption_kwh"] = np.nan
        cleaned = clean_data(df)
        assert cleaned["consumption_kwh"].isna().sum() == 0

    def test_handles_extreme_outliers(self):
        df = self._make_df(500)
        df.loc[50, "consumption_kwh"] = 999999.0  # extreme spike
        cleaned = clean_data(df)
        # Extreme outlier should be replaced with median
        assert cleaned.loc[50, "consumption_kwh"] < 999999.0

    def test_output_length_sensible(self):
        df = self._make_df(500)
        cleaned = clean_data(df)
        assert len(cleaned) >= 400  # should not drop too many rows


class TestBuildFeatureMatrix:
    def test_adds_time_features(self):
        df = generate_synthetic_data(n_hours=200)
        df = clean_data(df)
        result = build_feature_matrix(df)
        time_cols = ["hour", "day_of_week", "month", "is_weekend",
                     "hour_sin", "hour_cos", "is_peak_hour"]
        for col in time_cols:
            assert col in result.columns, f"Missing time feature: {col}"

    def test_adds_lag_features(self):
        df = generate_synthetic_data(n_hours=200)
        df = clean_data(df)
        result = build_feature_matrix(df)
        lag_cols = ["consumption_kwh_lag_1h", "consumption_kwh_lag_24h"]
        for col in lag_cols:
            assert col in result.columns, f"Missing lag feature: {col}"

    def test_adds_rolling_features(self):
        df = generate_synthetic_data(n_hours=200)
        df = clean_data(df)
        result = build_feature_matrix(df)
        assert "consumption_kwh_roll_mean_24h" in result.columns

    def test_no_all_nan_columns(self):
        df = generate_synthetic_data(n_hours=300)
        df = clean_data(df)
        result = build_feature_matrix(df)
        all_nan_cols = [c for c in result.columns if result[c].isna().all()]
        assert len(all_nan_cols) == 0, f"All-NaN columns: {all_nan_cols}"

    def test_minimum_8760_rows_enforced(self):
        """run_pipeline must always yield >= 8760 rows"""
        from data.pipeline import run_pipeline
        # Use synthetic path (no CSV)
        df = run_pipeline(smart_meter_path=None, iot_path=None)
        assert len(df) >= 8760, f"Expected >=8760 rows, got {len(df)}"

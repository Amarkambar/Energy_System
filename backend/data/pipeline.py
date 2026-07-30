# data/pipeline.py — Ingestion, preprocessing & feature engineering

import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
from scipy import stats
from config import (
    PARQUET_PATH, WEATHER_API_KEY, WEATHER_CITY,
    LAG_FEATURES, ROLLING_WINDOWS
)


# ══════════════════════════════════════════════════════════
#  1. DATA INGESTION
# ══════════════════════════════════════════════════════════

def load_smart_meter_data(filepath: str) -> pd.DataFrame:
    """Load smart meter CSV — expects columns: timestamp, consumption_kwh, voltage, load_factor"""
    df = pd.read_csv(filepath, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"[Ingestion] Smart meter: {len(df)} rows loaded")
    return df


def load_iot_sensor_data(filepath: str) -> pd.DataFrame:
    """Load IoT sensor CSV — expects: timestamp, temperature, pressure, flow_rate"""
    df = pd.read_csv(filepath, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    print(f"[Ingestion] IoT sensors: {len(df)} rows loaded")
    return df


def fetch_weather_data(city: str = WEATHER_CITY, api_key: str = WEATHER_API_KEY) -> dict:
    """Fetch current weather from OpenWeatherMap API. Returns dummy data if key is unconfigured."""
    # FIX: Skip API call entirely when key is the default placeholder — saves latency + log noise
    if not api_key or api_key in ("your_openweather_key", "YOUR_API_KEY", ""):
        print("[Weather] API key not configured — using dummy data.")
        return {
            "timestamp":   datetime.now(),
            "temp_c":      25.0,
            "humidity":    60.0,
            "wind_speed":  10.0,
            "description": "clear sky (dummy)",
        }
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        return {
            "timestamp":   datetime.now(),
            "temp_c":      data["main"]["temp"],
            "humidity":    data["main"]["humidity"],
            "wind_speed":  data["wind"]["speed"],
            "description": data["weather"][0]["description"],
        }
    except Exception as e:
        print(f"[Weather] API error: {e}. Using dummy data.")
        return {
            "timestamp":   datetime.now(),
            "temp_c":      25.0,
            "humidity":    60.0,
            "wind_speed":  10.0,
            "description": "clear sky",
        }


def generate_synthetic_data(n_hours: int = 8760) -> pd.DataFrame:
    """
    Generate one year of synthetic hourly energy data.
    Useful for development / demo when real data is unavailable.
    """
    np.random.seed(42)
    timestamps = pd.date_range(start="2023-01-01", periods=n_hours, freq="h")

    # Base load with daily + seasonal cycles
    hour_of_day    = timestamps.hour
    day_of_year    = timestamps.dayofyear
    daily_cycle    = 50 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
    seasonal_cycle = 30 * np.sin(2 * np.pi * day_of_year / 365)

    consumption = np.array(
        200
        + daily_cycle
        + seasonal_cycle
        + np.random.normal(0, 15, n_hours)
    )

    # Inject anomalies (spikes)
    anomaly_idx = np.random.choice(n_hours, size=50, replace=False)
    consumption[anomaly_idx] += np.random.uniform(100, 300, 50)
    consumption = np.clip(consumption, 0, None)

    df = pd.DataFrame({
        "timestamp":       timestamps,
        "consumption_kwh": consumption,
        "voltage":         np.random.normal(230, 5, n_hours),
        "load_factor":     np.random.uniform(0.6, 0.95, n_hours),
        "temperature":     20 + seasonal_cycle / 3 + np.random.normal(0, 3, n_hours),
        "humidity":        np.random.uniform(40, 90, n_hours),
        "pressure":        np.random.uniform(1.0, 1.5, n_hours),
        "flow_rate":       np.random.uniform(50, 150, n_hours),
        "is_anomaly":      np.isin(np.arange(n_hours), anomaly_idx).astype(int),
    })
    print(f"[Synthetic] Generated {n_hours} hours of energy data")
    return df


# ══════════════════════════════════════════════════════════
#  2. PREPROCESSING
# ══════════════════════════════════════════════════════════

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values, duplicates, and outliers"""
    original_len = len(df)

    # Drop duplicates
    df = df.drop_duplicates(subset=["timestamp"])

    # Fill missing with forward-fill then back-fill
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].ffill().bfill()

    # Remove extreme outliers using Z-score (|z| > 4)
    for col in ["consumption_kwh", "voltage"]:
        if col in df.columns:
            valid_idx = df[col].dropna().index
            z = np.abs(stats.zscore(df.loc[valid_idx, col]))
            outlier_mask = z > 4
            df.loc[valid_idx[outlier_mask], col] = np.nan
            df[col] = df[col].fillna(df[col].median())

    print(f"[Cleaning] {original_len} → {len(df)} rows after cleaning")
    return df.reset_index(drop=True)


def normalize_data(df: pd.DataFrame, columns: list = None) -> tuple[pd.DataFrame, dict]:
    """Min-max normalize specified columns, return df + scaler params"""
    if columns is None:
        columns = ["consumption_kwh", "voltage", "load_factor",
                   "temperature", "humidity", "pressure", "flow_rate"]
    columns = [c for c in columns if c in df.columns]

    scaler_params = {}
    df_norm = df.copy()
    for col in columns:
        col_min, col_max = df[col].min(), df[col].max()
        df_norm[col] = (df[col] - col_min) / (col_max - col_min + 1e-8)
        scaler_params[col] = {"min": col_min, "max": col_max}

    print(f"[Normalize] Normalized {len(columns)} columns")
    return df_norm, scaler_params


# ══════════════════════════════════════════════════════════
#  3. FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════

def _ensure_datetime_column(df: pd.DataFrame, col: str = "timestamp") -> pd.DataFrame:
    """
    Robustly coerce a column to datetime64[ns], drop unparseable rows,
    and raise a clear error if the column is missing entirely.

    This guard must be called before ANY .dt accessor usage so that
    'Can only use .dt accessor with datetimelike values' is never raised.
    """
    if col not in df.columns:
        raise KeyError(
            f"[DateTime Guard] Column '{col}' not found. "
            f"Available columns: {list(df.columns)}"
        )

    # Already proper datetime — nothing to do
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        print(f"[DateTime Guard] '{col}' is already datetime64 — skipping coercion.")
        return df

    before = len(df)
    df = df.copy()

    # FIX: Requirement 1 — always convert with errors="coerce"
    df[col] = pd.to_datetime(df[col], errors="coerce")

    # FIX: Requirement 2 — drop rows where coercion produced NaT
    df = df.dropna(subset=[col])
    dropped = before - len(df)

    if dropped:
        print(f"[DateTime Guard] Dropped {dropped} rows with unparseable '{col}' values.")

    # FIX: Requirement 3 — final dtype assertion before any .dt use
    if not pd.api.types.is_datetime64_any_dtype(df[col]):
        raise TypeError(
            f"[DateTime Guard] '{col}' is still {df[col].dtype} after coercion. "
            "Cannot proceed with .dt operations."
        )

    print(f"[DateTime Guard] '{col}' confirmed as {df[col].dtype}. {len(df)} rows remain.")
    return df.reset_index(drop=True)


# FIX: Requirement 4 — fully corrected add_time_features()
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract calendar/time features from the timestamp column.

    Fixes applied
    -------------
    1. Calls _ensure_datetime_column() before any .dt access.
    2. Returns df (was missing — caused build_feature_matrix to receive None).
    3. Adds is_weekend feature (Saturday=5, Sunday=6).
    4. Adds cyclical sin/cos encodings for hour and month so the model
       understands that hour 23 and hour 0 are adjacent.
    """
    # FIX: guard before any .dt usage
    df = _ensure_datetime_column(df, col="timestamp")
    df = df.copy()

    # Core calendar features
    df["hour"]        = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek   # 0=Mon … 6=Sun
    df["day_of_year"] = df["timestamp"].dt.dayofyear
    df["month"]       = df["timestamp"].dt.month
    df["year"]        = df["timestamp"].dt.year
    df["quarter"]     = df["timestamp"].dt.quarter
    df["week_of_year"] = df["timestamp"].dt.isocalendar().week.astype(int)

    # FIX: is_weekend (requirement 4)
    df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)

    # Advanced: cyclical encodings prevent hour-23 / hour-0 discontinuity
    df["hour_sin"]    = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"]    = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"]     = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"]     = np.cos(2 * np.pi * df["day_of_week"] / 7)

    # Peak-hour flag (7–9 AM and 5–8 PM are typical energy peaks)
    df["is_peak_hour"] = df["hour"].isin([7, 8, 9, 17, 18, 19, 20]).astype(int)

    print(f"[Features] Time features added: {len(df)} rows retained")
    # FIX: return df (the original bug — this was missing entirely)
    return df


def add_lag_features(df: pd.DataFrame, target_col: str = "consumption_kwh") -> pd.DataFrame:
    """Add lag features for time series modeling"""
    df = df.copy()
    for lag in LAG_FEATURES:
        df[f"{target_col}_lag_{lag}h"] = df[target_col].shift(lag)
    print(f"[Features] Lag features added: {LAG_FEATURES}")
    return df


def add_rolling_features(df: pd.DataFrame, target_col: str = "consumption_kwh") -> pd.DataFrame:
    """Add rolling mean, std, min, max features"""
    df = df.copy()
    for window in ROLLING_WINDOWS:
        df[f"{target_col}_roll_mean_{window}h"] = df[target_col].rolling(window).mean()
        df[f"{target_col}_roll_std_{window}h"]  = df[target_col].rolling(window).std()
        df[f"{target_col}_roll_max_{window}h"]  = df[target_col].rolling(window).max()
    print(f"[Features] Rolling features added: {ROLLING_WINDOWS}")
    return df


def add_fft_features(df: pd.DataFrame, target_col: str = "consumption_kwh", n_components: int = 5) -> pd.DataFrame:
    """Add top-N FFT frequency components as features"""
    df = df.copy()
    signal = df[target_col].fillna(df[target_col].median()).values
    fft_vals = np.abs(np.fft.rfft(signal))
    top_idx = np.argsort(fft_vals)[-n_components:][::-1]
    for i, idx in enumerate(top_idx):
        df[f"fft_component_{i+1}"] = np.cos(2 * np.pi * idx * np.arange(len(df)) / len(df))
    print(f"[Features] FFT features added: top {n_components} components")
    return df


def add_consumption_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Add domain-specific energy ratios"""
    df = df.copy()
    if "consumption_kwh" in df.columns and "temperature" in df.columns:
        df["consumption_per_degree"] = df["consumption_kwh"] / (df["temperature"].abs() + 1)
    if "consumption_kwh" in df.columns and "load_factor" in df.columns:
        df["apparent_power"] = df["consumption_kwh"] / (df["load_factor"] + 1e-8)
    return df


# FIX: Requirement 5 — debug dtype logging before feature engineering
def _log_dtypes(df: pd.DataFrame, stage: str = "") -> None:
    """
    Print all column dtypes.  Called before feature engineering so that
    dtype mismatches are caught early and are easy to diagnose.
    """
    header = f"[DTypes] {'— ' + stage + ' —' if stage else ''}"
    print(f"\n{header}")
    print(df.dtypes.to_string())
    print(f"  Shape : {df.shape}")

    # Highlight any object columns that might harbour hidden datetime strings
    obj_cols = df.select_dtypes(include="object").columns.tolist()
    if obj_cols:
        print(f"  ⚠  object-dtype columns (potential datetime strings): {obj_cols}")
    print()


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Run full feature engineering pipeline"""

    # FIX: Requirement 5 — log dtypes before any feature step
    _log_dtypes(df, stage="before feature engineering")

    df = add_time_features(df)     # now correctly returns df
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_fft_features(df)
    df = add_consumption_ratios(df)
    df = df.dropna().reset_index(drop=True)

    _log_dtypes(df, stage="after feature engineering")
    print(f"[Features] Final matrix: {df.shape[0]} rows × {df.shape[1]} columns")
    return df


# ══════════════════════════════════════════════════════════
#  4. STORAGE
# ══════════════════════════════════════════════════════════

def save_to_parquet(df: pd.DataFrame, path: str = PARQUET_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    print(f"[Storage] Saved {len(df)} rows to {path}")


def load_from_parquet(path: str = PARQUET_PATH) -> pd.DataFrame:
    df = pd.read_parquet(path)
    print(f"[Storage] Loaded {len(df)} rows from {path}")
    return df


# ══════════════════════════════════════════════════════════
#  5. MAIN PIPELINE RUNNER
# ══════════════════════════════════════════════════════════

def run_pipeline(
    smart_meter_path: str = None,
    iot_path: str = None,
    use_real_data: bool = True,
) -> pd.DataFrame:
    """
    Full pipeline: ingest → clean → normalize → feature engineering → save

    Args:
        smart_meter_path: Path to real sensor CSV file
        iot_path:         Path to IoT sensor CSV file
        use_real_data:    If True, attempts real data ingestion with validation

    Returns:
        Processed DataFrame ready for ML training
    """

    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    df = None

    if smart_meter_path and os.path.exists(smart_meter_path) and use_real_data:
        try:
            print("[Pipeline] Attempting to load real sensor data with validation...")
            from data.real_data_ingestion import RealDataIngestor

            ingestor   = RealDataIngestor()
            validation = ingestor.validate_csv(smart_meter_path)

            if validation["is_valid"]:
                print("[Pipeline] ✓ Validation passed")
                df = ingestor.load_real_sensor_data(
                    smart_meter_path,
                    clean=True,
                    resample_freq="1H",
                )
                print(f"[Pipeline] ✓ Loaded {len(df)} rows of real sensor data")

                # FIX: Requirement 6 — use validation["stats"]["date_range"]
                # (the old code referenced a non-existent top-level "date_range" key)
                if "stats" in validation and "date_range" in validation["stats"]:
                    dr = validation["stats"]["date_range"]
                    print(f"[Pipeline]   Date range: {dr}")

                if iot_path and os.path.exists(iot_path):
                    iot = load_iot_sensor_data(iot_path)
                    df  = pd.merge(df, iot, on="timestamp", how="left")
                    print("[Pipeline] ✓ Merged IoT sensor data")
            else:
                print(f"[Pipeline] ✗ Validation failed: {validation['errors']}")
                print("[Pipeline] → Falling back to basic CSV loading...")
                df = load_smart_meter_data(smart_meter_path)

        except Exception as e:
            print(f"[Pipeline] ✗ Real data ingestion failed: {e}")
            print("[Pipeline] → Falling back to basic CSV loading...")
            try:
                df = load_smart_meter_data(smart_meter_path)
            except Exception:
                df = None

    elif smart_meter_path and os.path.exists(smart_meter_path):
        print("[Pipeline] Loading CSV without validation...")
        df = load_smart_meter_data(smart_meter_path)
        if iot_path and os.path.exists(iot_path):
            iot = load_iot_sensor_data(iot_path)
            df  = pd.merge(df, iot, on="timestamp", how="left")

    if df is None or len(df) == 0:
        print("[Pipeline] No valid data found. Generating synthetic data...")
        df = generate_synthetic_data()

    # ── Step 2: Clean ─────────────────────────────────────────────────────────
    if "data_source" not in df.columns or df["data_source"].iloc[0] != "real_sensor":
        df = clean_data(df)

    # ── Step 3: Feature engineering ───────────────────────────────────────────
    df = build_feature_matrix(df)

    # ── Step 4: Persist ───────────────────────────────────────────────────────
    save_to_parquet(df)

    return df


if __name__ == "__main__":
    df = run_pipeline()
    print(df.head())
    print(f"\nColumns: {list(df.columns)}")
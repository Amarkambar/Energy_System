"""
ML Accuracy Report — reads from the live pipeline cache.
Run: venv\Scripts\python ml_accuracy_report.py
"""
import pickle, sys, os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")

print("\n" + "="*60)
print("  ML MODEL ACCURACY REPORT")
print("="*60)

# ── Load cache ──────────────────────────────────────────────
try:
    df       = pd.read_parquet(os.path.join(CACHE_DIR, "pipeline_df.parquet"))
    preds    = pd.read_parquet(os.path.join(CACHE_DIR, "pipeline_pred.parquet"))
    forecast = pd.read_parquet(os.path.join(CACHE_DIR, "pipeline_forecast.parquet"))
    with open(os.path.join(CACHE_DIR, "pipeline_models.pkl"), "rb") as f:
        models = pickle.load(f)
    print(f"\n  Data loaded: {len(df)} rows, {len(df.columns)} features\n")
except Exception as e:
    print(f"  ERROR loading cache: {e}")
    print("  Run the pipeline first from the dashboard.")
    sys.exit(1)

sep = "-"*60

# ══════════════════════════════════════════════════════════
# 1. FORECASTING MODEL (XGBoost Regressor)
# ══════════════════════════════════════════════════════════
print(sep)
print("  1. ENERGY FORECASTER  (XGBoost Regressor)")
print(sep)
try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    forecaster = models.get("forecaster")
    if forecaster and hasattr(forecaster, "feature_cols"):
        X = df[forecaster.feature_cols].fillna(0).values
        y = df["consumption_kwh"].values
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        y_pred = forecaster.model.predict(forecaster.scaler.transform(X_test))

        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mape = np.mean(np.abs((y_test - y_pred) / np.maximum(np.abs(y_test), 1e-6))) * 100
        r2   = r2_score(y_test, y_pred)

        print(f"  MAE   (Mean Absolute Error)     : {mae:.4f} kWh")
        print(f"  RMSE  (Root Mean Sq. Error)     : {rmse:.4f} kWh")
        print(f"  MAPE  (Mean Abs % Error)        : {mape:.2f}%")
        print(f"  R²    (Coefficient of Det.)     : {r2:.4f}")
        acc = max(0, (1 - mape/100)*100)
        print(f"  Accuracy (100 - MAPE)           : {acc:.2f}%")
    else:
        print("  Forecaster model not found in cache.")
except Exception as e:
    print(f"  ERROR: {e}")

# ══════════════════════════════════════════════════════════
# 2. ANOMALY DETECTION MODEL (Isolation Forest)
# ══════════════════════════════════════════════════════════
print(f"\n{sep}")
print("  2. ANOMALY DETECTOR  (Isolation Forest)")
print(sep)
try:
    if "anomaly_flag" in preds.columns:
        anomaly_rate = float(preds["anomaly_flag"].mean() * 100)
        total        = len(preds)
        flagged      = int(preds["anomaly_flag"].sum())
        print(f"  Total records analysed          : {total:,}")
        print(f"  Anomalies detected              : {flagged:,}  ({anomaly_rate:.2f}%)")
        print(f"  Normal readings                 : {total - flagged:,}  ({100-anomaly_rate:.2f}%)")

    if "anomaly_score" in preds.columns:
        scores = preds["anomaly_score"]
        print(f"  Avg anomaly score               : {scores.mean():.4f}")
        print(f"  Max anomaly score               : {scores.max():.4f}")

    # SHAP feature importance (top 5)
    anomaly_model = models.get("anomaly")
    if anomaly_model and hasattr(anomaly_model, "explain"):
        try:
            shap_df = anomaly_model.explain(df, n_samples=300)
            print(f"\n  Top 5 features driving anomalies:")
            for _, row in shap_df.head(5).iterrows():
                print(f"    {row['feature']:<35} SHAP: {row['shap_mean']:.4f}")
        except Exception as se:
            print(f"  SHAP: {se}")
except Exception as e:
    print(f"  ERROR: {e}")

# ══════════════════════════════════════════════════════════
# 3. MAINTENANCE PREDICTION MODEL (Random Forest Classifier)
# ══════════════════════════════════════════════════════════
print(f"\n{sep}")
print("  3. MAINTENANCE PREDICTOR  (Random Forest Classifier)")
print(sep)
try:
    from sklearn.model_selection import cross_val_score

    maint_model = models.get("maintenance")
    if maint_model and hasattr(maint_model, "model"):
        # CV score stored during training
        if hasattr(maint_model, "_cv_score") and maint_model._cv_score is not None:
            print(f"  Cross-Val Accuracy (5-fold)     : {maint_model._cv_score*100:.2f}%")

        if "health_status" in preds.columns:
            vc = preds["health_status"].value_counts()
            total = len(preds)
            print(f"\n  Health Status Distribution:")
            for label, count in vc.items():
                bar = "█" * int(count / total * 30)
                print(f"    {label:<12} {count:>6,}  ({count/total*100:5.1f}%)  {bar}")

        if "maintenance_urgency" in preds.columns:
            mu = preds["maintenance_urgency"]
            print(f"\n  Maintenance Urgency:")
            print(f"    Mean score                    : {mu.mean():.1f}%")
            print(f"    High urgency (>70%)           : {(mu > 70).sum():,} records")
            print(f"    Critical (>85%)               : {(mu > 85).sum():,} records")

        # Feature importance
        if hasattr(maint_model, "get_feature_importance"):
            imp = maint_model.get_feature_importance()
            print(f"\n  Top 5 predictive features:")
            for _, row in imp.head(5).iterrows():
                bar = "▓" * int(row['importance'] * 50)
                print(f"    {row['feature']:<35} {row['importance']:.4f}  {bar}")
    else:
        print("  Maintenance model not found.")
except Exception as e:
    print(f"  ERROR: {e}")

# ══════════════════════════════════════════════════════════
# 4. EFFICIENCY CLUSTERING MODEL (K-Means)
# ══════════════════════════════════════════════════════════
print(f"\n{sep}")
print("  4. EFFICIENCY CLASSIFIER  (K-Means Clustering)")
print(sep)
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score

    eff_model = models.get("efficiency")
    if eff_model and hasattr(eff_model, "kmeans"):
        n_clusters = int(eff_model.kmeans.n_clusters)
        print(f"  Number of clusters              : {n_clusters}")

        if "efficiency_label" in preds.columns:
            vc = preds["efficiency_label"].value_counts()
            total = len(preds)
            print(f"\n  Efficiency Label Distribution:")
            for label, count in vc.items():
                bar = "█" * int(count / total * 30)
                print(f"    {label:<20} {count:>6,}  ({count/total*100:5.1f}%)  {bar}")

        # Silhouette score
        cols = [c for c in getattr(eff_model, "feature_cols", []) if c in preds.columns]
        if cols:
            X_eff = StandardScaler().fit_transform(preds[cols].fillna(0))
            labels = eff_model.kmeans.predict(X_eff)
            if len(set(labels)) > 1:
                sil = silhouette_score(X_eff, labels, sample_size=min(2000, len(X_eff)))
                quality = "Excellent" if sil > 0.7 else "Good" if sil > 0.5 else "Fair" if sil > 0.25 else "Poor"
                print(f"\n  Silhouette Score                : {sil:.4f}  ({quality})")
                print(f"  (1.0 = perfect clusters, 0 = overlapping, -1 = wrong clusters)")
    else:
        print("  Efficiency model not found.")
except Exception as e:
    print(f"  ERROR: {e}")

# ══════════════════════════════════════════════════════════
# 5. OVERALL PIPELINE SUMMARY
# ══════════════════════════════════════════════════════════
print(f"\n{sep}")
print("  5. OVERALL PIPELINE SUMMARY")
print(sep)
try:
    print(f"  Dataset rows                    : {len(df):,}")
    print(f"  Feature columns                 : {len(df.columns)}")
    print(f"  Prediction rows                 : {len(preds):,}")
    print(f"  Forecast horizon                : {len(forecast)} hours")
    if "anomaly_flag" in preds.columns:
        normal_pct = (1 - preds["anomaly_flag"].mean()) * 100
        print(f"  Data quality (non-anomaly %)    : {normal_pct:.1f}%")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "="*60 + "\n")

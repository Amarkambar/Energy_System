# main.py — Entry point for the Energy Diagnostics project

import os
import sys
import argparse

def run_pipeline():
    print("\n" + "="*55)
    print("  STEP 1: DATA PIPELINE")
    print("="*55)
    from data.pipeline import run_pipeline as _run
    df = _run()
    return df

def run_models(df):
    print("\n" + "="*55)
    print("  STEP 2: TRAINING AI/ML MODELS")
    print("="*55)
    from models.ml_models import train_all_models, run_all_predictions
    models = train_all_models(df)
    predictions, forecast = run_all_predictions(df, models)
    print(f"\n  Predictions shape : {predictions.shape}")
    print(f"  Forecast shape    : {forecast.shape}")
    return models, predictions, forecast

def run_alerts(df, predictions):
    print("\n" + "="*55)
    print("  STEP 3: ALERTS + RECOMMENDATIONS")
    print("="*55)
    from alerts.alerts_engine import AlertEngine, RecommendationEngine

    alert_engine = AlertEngine()
    alerts_df = alert_engine.check_dataframe(predictions.tail(500))
    summary = alert_engine.get_alert_summary()
    print(f"\n  Alert summary: {summary}")

    rec_engine = RecommendationEngine()
    recs = rec_engine.generate(df, predictions)
    print(f"\n  Recommendations generated: {len(recs)}")
    for r in recs:
        print(f"  [{r['priority'].upper():8s}] {r['category']}: {r['recommendation'][:70]}...")
    return alerts_df, recs

def launch_dashboard():
    print("\n" + "="*55)
    print("  STEP 4: LAUNCHING DASHBOARD")
    print("="*55)
    print("  Starting Streamlit on http://localhost:8501")
    os.system("streamlit run dashboard/app.py --server.port 8501")

def main():
    parser = argparse.ArgumentParser(description="Energy Diagnostics — AI-powered system")
    parser.add_argument("--mode", choices=["full", "pipeline", "models", "alerts", "dashboard"],
                        default="full", help="Which component to run")
    args = parser.parse_args()

    print("\n" + "★"*55)
    print("  ENERGY DIAGNOSTICS — AI-Powered System")
    print("★"*55)

    if args.mode in ("full", "pipeline", "models", "alerts"):
        df = run_pipeline()

    if args.mode in ("full", "models", "alerts"):
        models, predictions, forecast = run_models(df)

    if args.mode in ("full", "alerts"):
        alerts_df, recs = run_alerts(df, predictions)

    if args.mode in ("full", "dashboard"):
        launch_dashboard()
    elif args.mode != "dashboard":
        print("\n" + "="*55)
        print("  ✅ COMPLETE — Run 'python main.py --mode dashboard' to launch UI")
        print("="*55)

if __name__ == "__main__":
    main()

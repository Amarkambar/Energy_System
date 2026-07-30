# models/auto_retrain.py — Automatic Model Retraining System

import os
import time
import pickle
import threading
import schedule
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from config import MODEL_DIR


class AutoRetrainer:
    """
    Automatic model retraining system.
    
    Monitors for new data and retrains models when thresholds are met.
    Compares new model performance against the old model and only
    replaces if the new model performs better.
    """
    
    def __init__(
        self,
        data_threshold: int = 100,
        performance_margin: float = 0.02,
        check_interval_minutes: int = 60
    ):
        """
        Initialize AutoRetrainer.
        
        Args:
            data_threshold: Minimum new rows required to trigger retraining
            performance_margin: Required improvement margin (e.g., 0.02 = 2% better)
            check_interval_minutes: How often to check for new data
        """
        self.data_threshold = data_threshold
        self.performance_margin = performance_margin
        self.check_interval_minutes = check_interval_minutes
        
        self.last_training_rows = 0
        self.last_training_time: Optional[datetime] = None
        self.training_history: list = []
        self.is_running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
        # Model registry
        self.models: Dict[str, Any] = {}
        self.model_metrics: Dict[str, Dict[str, float]] = {}
        
        # Callbacks
        self.on_retrain_start: Optional[Callable] = None
        self.on_retrain_complete: Optional[Callable] = None
        self.on_model_updated: Optional[Callable] = None
    
    def register_model(
        self,
        name: str,
        model: Any,
        metrics: Dict[str, float],
        training_func: Callable
    ):
        """
        Register a model for automatic retraining.
        
        Args:
            name: Model identifier
            model: The trained model object
            metrics: Current model metrics (e.g., {'mae': 5.2, 'rmse': 8.1})
            training_func: Function to train the model, signature: func(df) -> (model, metrics)
        """
        self.models[name] = {
            "model": model,
            "training_func": training_func,
            "registered_at": datetime.now()
        }
        self.model_metrics[name] = metrics
        print(f"[AutoRetrainer] Registered model: {name}")
    
    def check_retrain_needed(self, current_rows: int) -> bool:
        """
        Check if retraining is needed based on new data.
        
        Args:
            current_rows: Current number of rows in dataset
        
        Returns:
            True if retraining should be triggered
        """
        new_rows = current_rows - self.last_training_rows
        
        if new_rows >= self.data_threshold:
            print(f"[AutoRetrainer] Retrain trigger: {new_rows} new rows (threshold: {self.data_threshold})")
            return True
        
        return False
    
    def evaluate_model(
        self,
        model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
        task_type: str = "regression"
    ) -> Dict[str, float]:
        """
        Evaluate a model on test data.
        
        Args:
            model: Model to evaluate
            X_test: Test features
            y_test: Test targets
            task_type: 'regression' or 'classification'
        
        Returns:
            Dictionary of metrics
        """
        y_pred = model.predict(X_test)
        
        if task_type == "regression":
            mae = float(np.mean(np.abs(y_pred - y_test)))
            rmse = float(np.sqrt(np.mean((y_pred - y_test) ** 2)))
            mape = float(np.mean(np.abs((y_pred - y_test) / (y_test + 1e-8)))) * 100
            
            # R² score
            ss_res = np.sum((y_test - y_pred) ** 2)
            ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
            r2 = float(1 - (ss_res / (ss_tot + 1e-8)))
            
            return {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "mape": round(mape, 2),
                "r2": round(r2, 4)
            }
        else:
            from sklearn.metrics import accuracy_score, f1_score
            accuracy = float(accuracy_score(y_test, y_pred))
            f1 = float(f1_score(y_test, y_pred, average='weighted'))
            
            return {
                "accuracy": round(accuracy, 4),
                "f1_score": round(f1, 4)
            }
    
    def compare_models(
        self,
        old_metrics: Dict[str, float],
        new_metrics: Dict[str, float],
        primary_metric: str = "mae",
        lower_is_better: bool = True
    ) -> Dict[str, Any]:
        """
        Compare old and new model metrics.
        
        Args:
            old_metrics: Metrics from current model
            new_metrics: Metrics from newly trained model
            primary_metric: Main metric to compare
            lower_is_better: Whether lower values are better
        
        Returns:
            Comparison result with decision
        """
        old_val = old_metrics.get(primary_metric, float('inf') if lower_is_better else 0)
        new_val = new_metrics.get(primary_metric, float('inf') if lower_is_better else 0)
        
        if lower_is_better:
            improvement = (old_val - new_val) / (old_val + 1e-8)
            is_better = new_val < old_val * (1 - self.performance_margin)
        else:
            improvement = (new_val - old_val) / (old_val + 1e-8)
            is_better = new_val > old_val * (1 + self.performance_margin)
        
        return {
            "old_metrics": old_metrics,
            "new_metrics": new_metrics,
            "primary_metric": primary_metric,
            "old_value": old_val,
            "new_value": new_val,
            "improvement": round(improvement * 100, 2),
            "improvement_pct": f"{round(improvement * 100, 2)}%",
            "is_better": is_better,
            "decision": "REPLACE" if is_better else "KEEP_OLD",
            "margin_threshold": f"{self.performance_margin * 100}%"
        }
    
    def retrain_model(
        self,
        name: str,
        df: pd.DataFrame,
        X_test: np.ndarray = None,
        y_test: np.ndarray = None,
        task_type: str = "regression",
        primary_metric: str = "mae"
    ) -> Dict[str, Any]:
        """
        Retrain a specific model and compare with current version.
        
        Args:
            name: Model name
            df: Full training data
            X_test: Test features for evaluation
            y_test: Test targets for evaluation
            task_type: 'regression' or 'classification'
            primary_metric: Metric to use for comparison
        
        Returns:
            Retraining result dictionary
        """
        if name not in self.models:
            return {"error": f"Model '{name}' not registered"}
        
        model_info = self.models[name]
        training_func = model_info["training_func"]
        old_metrics = self.model_metrics.get(name, {})
        
        # Callback: retraining started
        if self.on_retrain_start:
            self.on_retrain_start(name)
        
        start_time = time.time()
        
        try:
            # Train new model
            new_model, new_metrics = training_func(df)
            training_time = time.time() - start_time
            
            # If test data provided, evaluate both models
            if X_test is not None and y_test is not None:
                old_model = model_info["model"]
                old_eval = self.evaluate_model(old_model, X_test, y_test, task_type)
                new_eval = self.evaluate_model(new_model, X_test, y_test, task_type)
                
                comparison = self.compare_models(
                    old_eval, new_eval, primary_metric,
                    lower_is_better=(primary_metric in ["mae", "rmse", "mape"])
                )
            else:
                # Use provided metrics for comparison
                comparison = self.compare_models(
                    old_metrics, new_metrics, primary_metric,
                    lower_is_better=(primary_metric in ["mae", "rmse", "mape"])
                )
            
            result = {
                "model_name": name,
                "status": "success",
                "training_time_seconds": round(training_time, 2),
                "comparison": comparison,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update model if better
            if comparison["is_better"]:
                self.models[name]["model"] = new_model
                self.models[name]["updated_at"] = datetime.now()
                self.model_metrics[name] = new_metrics
                result["action"] = "MODEL_REPLACED"
                
                # Callback: model updated
                if self.on_model_updated:
                    self.on_model_updated(name, new_model, comparison)
                
                print(f"[AutoRetrainer] Model '{name}' replaced (improvement: {comparison['improvement_pct']})")
            else:
                result["action"] = "MODEL_KEPT"
                print(f"[AutoRetrainer] Model '{name}' kept (new model not significantly better)")
            
            # Record in history
            self.training_history.append(result)
            
            # Callback: retraining complete
            if self.on_retrain_complete:
                self.on_retrain_complete(name, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "model_name": name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.training_history.append(error_result)
            return error_result
    
    def retrain_all(
        self,
        df: pd.DataFrame,
        test_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Retrain all registered models.
        
        Args:
            df: Full training data
            test_split: Fraction of data to use for testing
        
        Returns:
            Summary of all retraining results
        """
        results = {}
        updated_count = 0
        
        self.last_training_rows = len(df)
        self.last_training_time = datetime.now()
        
        for name in self.models:
            result = self.retrain_model(name, df)
            results[name] = result
            if result.get("action") == "MODEL_REPLACED":
                updated_count += 1
        
        return {
            "total_models": len(self.models),
            "models_updated": updated_count,
            "models_kept": len(self.models) - updated_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def start_scheduler(self, data_loader: Callable):
        """
        Start automatic retraining scheduler.
        
        Args:
            data_loader: Function that returns current dataframe
        """
        if self.is_running:
            print("[AutoRetrainer] Scheduler already running")
            return
        
        def check_and_retrain():
            try:
                df = data_loader()
                if self.check_retrain_needed(len(df)):
                    print(f"[AutoRetrainer] Triggering automatic retrain...")
                    self.retrain_all(df)
            except Exception as e:
                print(f"[AutoRetrainer] Scheduler error: {e}")
        
        schedule.every(self.check_interval_minutes).minutes.do(check_and_retrain)
        
        self.is_running = True
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)
        
        self._scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self._scheduler_thread.start()
        
        print(f"[AutoRetrainer] Scheduler started (checking every {self.check_interval_minutes} min)")
    
    def stop_scheduler(self):
        """Stop the automatic retraining scheduler."""
        self.is_running = False
        schedule.clear()
        print("[AutoRetrainer] Scheduler stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the auto-retrainer."""
        return {
            "is_running": self.is_running,
            "registered_models": list(self.models.keys()),
            "last_training_rows": self.last_training_rows,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "data_threshold": self.data_threshold,
            "performance_margin": f"{self.performance_margin * 100}%",
            "check_interval_minutes": self.check_interval_minutes,
            "training_history_count": len(self.training_history)
        }
    
    def get_training_history(self, limit: int = 10) -> list:
        """Get recent training history."""
        return self.training_history[-limit:]
    
    def get_model_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of current model metrics."""
        return self.model_metrics.copy()
    
    def get_comparison_json(self) -> Dict[str, Any]:
        """Get comparison data formatted for frontend visualization."""
        comparison_data = []
        
        for name, metrics in self.model_metrics.items():
            model_info = self.models.get(name, {})
            comparison_data.append({
                "model": name,
                "metrics": metrics,
                "registered_at": model_info.get("registered_at", datetime.now()).isoformat(),
                "updated_at": model_info.get("updated_at", model_info.get("registered_at", datetime.now())).isoformat()
            })
        
        # Get recent training results
        recent_history = self.training_history[-5:] if self.training_history else []
        
        return {
            "models": comparison_data,
            "recent_training": recent_history,
            "status": self.get_status()
        }


class DataDriftDetector:
    """
    Detects data drift to trigger model retraining.
    Uses statistical tests to compare training and new data distributions.
    """
    
    def __init__(self, drift_threshold: float = 0.1):
        """
        Initialize drift detector.
        
        Args:
            drift_threshold: P-value threshold below which drift is detected
        """
        self.drift_threshold = drift_threshold
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
    
    def set_baseline(self, df: pd.DataFrame, feature_cols: list = None):
        """
        Set baseline statistics from training data.
        
        Args:
            df: Training dataframe
            feature_cols: Columns to monitor (None = all numeric)
        """
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in feature_cols:
            self.baseline_stats[col] = {
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "median": float(df[col].median()),
                "q25": float(df[col].quantile(0.25)),
                "q75": float(df[col].quantile(0.75))
            }
        
        print(f"[DriftDetector] Baseline set for {len(feature_cols)} features")
    
    def detect_drift(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect drift in new data compared to baseline.
        
        Args:
            df: New data to check
        
        Returns:
            Drift detection results
        """
        if not self.baseline_stats:
            return {"error": "Baseline not set"}
        
        drift_results = {}
        drifted_features = []
        
        for col, baseline in self.baseline_stats.items():
            if col not in df.columns:
                continue
            
            current = df[col].dropna()
            
            # Simple drift detection using mean shift
            mean_diff = abs(current.mean() - baseline["mean"])
            std_baseline = baseline["std"] if baseline["std"] > 0 else 1
            z_score = mean_diff / std_baseline
            
            # Check if significant drift
            is_drifted = z_score > 2.0  # More than 2 standard deviations
            
            drift_results[col] = {
                "baseline_mean": baseline["mean"],
                "current_mean": float(current.mean()),
                "mean_shift": float(mean_diff),
                "z_score": float(z_score),
                "is_drifted": is_drifted
            }
            
            if is_drifted:
                drifted_features.append(col)
        
        overall_drift = len(drifted_features) / len(self.baseline_stats) if self.baseline_stats else 0
        
        return {
            "total_features": len(self.baseline_stats),
            "drifted_features": drifted_features,
            "n_drifted": len(drifted_features),
            "drift_ratio": round(overall_drift, 3),
            "drift_detected": overall_drift > self.drift_threshold,
            "details": drift_results
        }


# Singleton instance for global access
_auto_retrainer: Optional[AutoRetrainer] = None


def get_auto_retrainer() -> AutoRetrainer:
    """Get or create the global AutoRetrainer instance."""
    global _auto_retrainer
    if _auto_retrainer is None:
        _auto_retrainer = AutoRetrainer()
    return _auto_retrainer


if __name__ == "__main__":
    # Test auto-retraining
    print("=== AutoRetrainer Test ===\n")
    
    # Create test data
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "feature1": np.random.randn(n),
        "feature2": np.random.randn(n),
        "target": np.random.randn(n)
    })
    
    # Mock training function
    def mock_train(data):
        from sklearn.linear_model import Ridge
        model = Ridge()
        X = data[["feature1", "feature2"]].values
        y = data["target"].values
        model.fit(X, y)
        return model, {"mae": 0.8, "rmse": 1.0}
    
    # Test AutoRetrainer
    retrainer = AutoRetrainer(data_threshold=100)
    
    # Register mock model
    from sklearn.linear_model import Ridge
    mock_model = Ridge()
    mock_model.fit(df[["feature1", "feature2"]], df["target"])
    
    retrainer.register_model(
        "test_model",
        mock_model,
        {"mae": 1.0, "rmse": 1.2},
        mock_train
    )
    
    # Check status
    print(f"Status: {retrainer.get_status()}")
    
    # Test retrain
    result = retrainer.retrain_model("test_model", df)
    print(f"\nRetrain result: {result}")
    
    # Test drift detection
    print("\n=== Drift Detection Test ===\n")
    
    drift_detector = DataDriftDetector()
    drift_detector.set_baseline(df)
    
    # Create drifted data
    df_drifted = df.copy()
    df_drifted["feature1"] = df_drifted["feature1"] + 3  # Shift mean
    
    drift_result = drift_detector.detect_drift(df_drifted)
    print(f"Drift detected: {drift_result['drift_detected']}")
    print(f"Drifted features: {drift_result['drifted_features']}")

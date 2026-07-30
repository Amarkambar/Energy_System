# models/metrics_calculator.py — Comprehensive ML Metrics Calculator
# Provides detailed accuracy metrics: MAE, RMSE, MAPE, R², F1-score, etc.

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    roc_curve, auc, precision_recall_curve, average_precision_score,
    roc_auc_score
)
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import label_binarize
import warnings
warnings.filterwarnings("ignore")


class MetricsCalculator:
    """
    Unified metrics calculator for regression and classification models.
    Provides publication-ready metrics tables and visualization data.
    """
    
    @staticmethod
    def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calculate comprehensive regression metrics.
        
        Returns:
            Dict with MAE, MSE, RMSE, MAPE, R², Adjusted R², Max Error
        """
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()
        
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        
        # MAPE (handle zero values)
        mask = y_true != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = np.nan
        
        # Symmetric MAPE (sMAPE)
        smape = np.mean(2 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred) + 1e-8)) * 100
        
        r2 = r2_score(y_true, y_pred)
        
        # Adjusted R² (assuming n features, we approximate)
        n = len(y_true)
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - 2) if n > 2 else r2
        
        # Additional metrics
        max_error = np.max(np.abs(y_true - y_pred))
        median_ae = np.median(np.abs(y_true - y_pred))
        
        # Explained variance
        explained_var = 1 - np.var(y_true - y_pred) / np.var(y_true) if np.var(y_true) > 0 else 0
        
        return {
            "mae": round(mae, 4),
            "mse": round(mse, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 2) if not np.isnan(mape) else None,
            "smape": round(smape, 2),
            "r2": round(r2, 4),
            "adjusted_r2": round(adj_r2, 4),
            "max_error": round(max_error, 4),
            "median_ae": round(median_ae, 4),
            "explained_variance": round(explained_var, 4),
            "n_samples": n
        }
    
    @staticmethod
    def classification_metrics(
        y_true: np.ndarray, 
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive classification metrics.
        
        Returns:
            Dict with accuracy, precision, recall, F1, confusion matrix, etc.
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        
        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        
        # Determine if binary or multiclass
        unique_classes = np.unique(np.concatenate([y_true, y_pred]))
        n_classes = len(unique_classes)
        is_binary = n_classes == 2
        
        average = 'binary' if is_binary else 'weighted'
        
        precision = precision_score(y_true, y_pred, average=average, zero_division=0)
        recall = recall_score(y_true, y_pred, average=average, zero_division=0)
        f1 = f1_score(y_true, y_pred, average=average, zero_division=0)
        
        # Per-class metrics
        precision_per_class = precision_score(y_true, y_pred, average=None, zero_division=0)
        recall_per_class = recall_score(y_true, y_pred, average=None, zero_division=0)
        f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        cm_normalized = cm.astype('float') / (cm.sum(axis=1)[:, np.newaxis] + 1e-8)
        
        # Specificity (for each class)
        specificities = []
        for i in range(len(cm)):
            tn = np.sum(cm) - np.sum(cm[i, :]) - np.sum(cm[:, i]) + cm[i, i]
            fp = np.sum(cm[:, i]) - cm[i, i]
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            specificities.append(specificity)
        
        result = {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "specificity": round(np.mean(specificities), 4),
            "n_classes": n_classes,
            "n_samples": len(y_true),
            "confusion_matrix": cm.tolist(),
            "confusion_matrix_normalized": np.round(cm_normalized, 4).tolist(),
            "per_class_metrics": {
                "precision": [round(p, 4) for p in precision_per_class],
                "recall": [round(r, 4) for r in recall_per_class],
                "f1_score": [round(f, 4) for f in f1_per_class],
                "specificity": [round(s, 4) for s in specificities],
                "support": [int(np.sum(y_true == c)) for c in unique_classes]
            },
            "classes": [str(c) for c in unique_classes]
        }
        
        # ROC-AUC if probabilities provided
        if y_prob is not None:
            result["roc_data"] = MetricsCalculator.compute_roc_curves(y_true, y_prob, unique_classes)
            result["pr_data"] = MetricsCalculator.compute_pr_curves(y_true, y_prob, unique_classes)
        
        return result
    
    @staticmethod
    def compute_roc_curves(
        y_true: np.ndarray, 
        y_prob: np.ndarray,
        classes: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compute ROC curves and AUC for each class (one-vs-rest).
        """
        n_classes = len(classes)
        y_prob = np.asarray(y_prob)
        
        # Binarize labels for multi-class
        if n_classes > 2:
            y_bin = label_binarize(y_true, classes=classes)
        else:
            y_bin = (y_true == classes[1]).astype(int).reshape(-1, 1)
            if y_prob.ndim == 2 and y_prob.shape[1] == 2:
                y_prob = y_prob[:, 1].reshape(-1, 1)
            elif y_prob.ndim == 1:
                y_prob = y_prob.reshape(-1, 1)
        
        roc_data = {"curves": [], "auc_scores": {}}
        
        for i, cls in enumerate(classes):
            if i < y_bin.shape[1] and i < y_prob.shape[1]:
                fpr, tpr, thresholds = roc_curve(y_bin[:, i], y_prob[:, i])
                roc_auc = auc(fpr, tpr)
                
                # Downsample for JSON efficiency
                step = max(1, len(fpr) // 100)
                roc_data["curves"].append({
                    "class": str(cls),
                    "fpr": [round(f, 4) for f in fpr[::step]],
                    "tpr": [round(t, 4) for t in tpr[::step]],
                    "auc": round(roc_auc, 4)
                })
                roc_data["auc_scores"][str(cls)] = round(roc_auc, 4)
        
        # Macro-average AUC
        if len(roc_data["auc_scores"]) > 0:
            roc_data["macro_auc"] = round(np.mean(list(roc_data["auc_scores"].values())), 4)
        
        return roc_data
    
    @staticmethod
    def compute_pr_curves(
        y_true: np.ndarray,
        y_prob: np.ndarray,
        classes: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compute Precision-Recall curves and Average Precision for each class.
        """
        n_classes = len(classes)
        y_prob = np.asarray(y_prob)
        
        if n_classes > 2:
            y_bin = label_binarize(y_true, classes=classes)
        else:
            y_bin = (y_true == classes[1]).astype(int).reshape(-1, 1)
            if y_prob.ndim == 2 and y_prob.shape[1] == 2:
                y_prob = y_prob[:, 1].reshape(-1, 1)
            elif y_prob.ndim == 1:
                y_prob = y_prob.reshape(-1, 1)
        
        pr_data = {"curves": [], "ap_scores": {}}
        
        for i, cls in enumerate(classes):
            if i < y_bin.shape[1] and i < y_prob.shape[1]:
                precision, recall, thresholds = precision_recall_curve(y_bin[:, i], y_prob[:, i])
                ap = average_precision_score(y_bin[:, i], y_prob[:, i])
                
                step = max(1, len(precision) // 100)
                pr_data["curves"].append({
                    "class": str(cls),
                    "precision": [round(p, 4) for p in precision[::step]],
                    "recall": [round(r, 4) for r in recall[::step]],
                    "ap": round(ap, 4)
                })
                pr_data["ap_scores"][str(cls)] = round(ap, 4)
        
        if len(pr_data["ap_scores"]) > 0:
            pr_data["macro_ap"] = round(np.mean(list(pr_data["ap_scores"].values())), 4)
        
        return pr_data
    
    @staticmethod
    def cross_validation_metrics(
        model,
        X: np.ndarray,
        y: np.ndarray,
        cv: int = 5,
        scoring: str = 'neg_mean_squared_error',
        is_time_series: bool = False
    ) -> Dict[str, Any]:
        """
        Perform cross-validation and return metrics with confidence intervals.
        """
        if is_time_series:
            cv_splitter = TimeSeriesSplit(n_splits=cv)
        else:
            cv_splitter = cv
        
        scores = cross_val_score(model, X, y, cv=cv_splitter, scoring=scoring)
        
        # Convert negative scores if needed
        if scoring.startswith('neg_'):
            scores = -scores
        
        return {
            "cv_scores": [round(s, 4) for s in scores],
            "mean": round(np.mean(scores), 4),
            "std": round(np.std(scores), 4),
            "min": round(np.min(scores), 4),
            "max": round(np.max(scores), 4),
            "ci_95_lower": round(np.mean(scores) - 1.96 * np.std(scores) / np.sqrt(len(scores)), 4),
            "ci_95_upper": round(np.mean(scores) + 1.96 * np.std(scores) / np.sqrt(len(scores)), 4),
            "n_folds": cv
        }
    
    @staticmethod
    def format_metrics_table(metrics_list: List[Dict], model_names: List[str]) -> pd.DataFrame:
        """
        Format multiple model metrics into a comparison table.
        """
        rows = []
        for name, metrics in zip(model_names, metrics_list):
            row = {"Model": name}
            row.update(metrics)
            rows.append(row)
        
        df = pd.DataFrame(rows)
        return df


class ModelComparator:
    """
    Compare multiple models on the same dataset.
    """
    
    def __init__(self):
        self.results = {}
        self.best_model = None
        self.comparison_df = None
    
    def add_result(
        self,
        model_name: str,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        task_type: str = "regression",
        training_time: float = None,
        model_params: Dict = None
    ):
        """Add a model's predictions for comparison."""
        
        if task_type == "regression":
            metrics = MetricsCalculator.regression_metrics(y_true, y_pred)
        else:
            metrics = MetricsCalculator.classification_metrics(y_true, y_pred, y_prob)
        
        self.results[model_name] = {
            "metrics": metrics,
            "task_type": task_type,
            "training_time": training_time,
            "model_params": model_params,
            "y_true": y_true,
            "y_pred": y_pred,
            "y_prob": y_prob
        }
    
    def get_comparison_table(self, task_type: str = "regression") -> pd.DataFrame:
        """
        Generate a comparison table for all models.
        """
        rows = []
        for name, data in self.results.items():
            if data["task_type"] != task_type:
                continue
            
            row = {"Model": name}
            row.update(data["metrics"])
            if data["training_time"]:
                row["Training Time (s)"] = round(data["training_time"], 2)
            rows.append(row)
        
        self.comparison_df = pd.DataFrame(rows)
        return self.comparison_df
    
    def get_best_model(self, metric: str = "rmse", lower_is_better: bool = True) -> str:
        """
        Find the best model based on a specific metric.
        """
        if self.comparison_df is None:
            self.get_comparison_table()
        
        if metric not in self.comparison_df.columns:
            raise ValueError(f"Metric '{metric}' not found in comparison table")
        
        if lower_is_better:
            best_idx = self.comparison_df[metric].idxmin()
        else:
            best_idx = self.comparison_df[metric].idxmax()
        
        self.best_model = self.comparison_df.loc[best_idx, "Model"]
        return self.best_model
    
    def get_visualization_data(self) -> Dict[str, Any]:
        """
        Get data formatted for frontend visualization.
        """
        if not self.results:
            return {}
        
        # Determine task type from first result
        first_result = list(self.results.values())[0]
        task_type = first_result["task_type"]
        
        if task_type == "regression":
            metrics_to_plot = ["mae", "rmse", "mape", "r2"]
        else:
            metrics_to_plot = ["accuracy", "precision", "recall", "f1_score"]
        
        # Bar chart data
        bar_data = []
        for name, data in self.results.items():
            entry = {"model": name}
            for metric in metrics_to_plot:
                if metric in data["metrics"]:
                    entry[metric] = data["metrics"][metric]
            bar_data.append(entry)
        
        # Radar chart data (normalized 0-1)
        radar_data = {"labels": metrics_to_plot, "datasets": []}
        for name, data in self.results.items():
            values = []
            for metric in metrics_to_plot:
                val = data["metrics"].get(metric, 0)
                # Normalize (R² is already 0-1, others need scaling)
                if metric == "r2":
                    values.append(max(0, val))
                elif metric in ["accuracy", "precision", "recall", "f1_score"]:
                    values.append(val)
                elif metric == "mape":
                    values.append(max(0, 1 - val / 100))  # Lower is better
                else:
                    values.append(val)
            radar_data["datasets"].append({"model": name, "values": values})
        
        return {
            "bar_chart": bar_data,
            "radar_chart": radar_data,
            "comparison_table": self.comparison_df.to_dict("records") if self.comparison_df is not None else []
        }
    
    def get_comparison_json(self) -> Dict[str, Any]:
        """
        Get complete comparison data in JSON-friendly format for frontend.
        Includes all metrics, rankings, and chart data.
        """
        if not self.results:
            return {"error": "No results added", "models": []}
        
        # Build comparison table if not exists
        if self.comparison_df is None:
            first_task = list(self.results.values())[0]["task_type"]
            self.get_comparison_table(first_task)
        
        # Get visualization data
        viz_data = self.get_visualization_data()
        
        # Build detailed model data
        models_data = []
        for name, data in self.results.items():
            model_entry = {
                "name": name,
                "task_type": data["task_type"],
                "metrics": data["metrics"],
                "training_time": data.get("training_time"),
                "params": data.get("model_params")
            }
            
            # Add confusion matrix for classification
            if data["task_type"] == "classification" and "confusion_matrix" in data["metrics"]:
                model_entry["confusion_matrix"] = {
                    "matrix": data["metrics"]["confusion_matrix"],
                    "matrix_normalized": data["metrics"].get("confusion_matrix_normalized"),
                    "classes": data["metrics"].get("classes", [])
                }
            
            # Add ROC data if available
            if "roc_data" in data["metrics"]:
                model_entry["roc_curves"] = data["metrics"]["roc_data"]
            
            # Add PR data if available
            if "pr_data" in data["metrics"]:
                model_entry["pr_curves"] = data["metrics"]["pr_data"]
            
            models_data.append(model_entry)
        
        # Calculate rankings for each metric
        rankings = self._calculate_rankings()
        
        return {
            "models": models_data,
            "comparison_table": viz_data.get("comparison_table", []),
            "bar_chart_data": viz_data.get("bar_chart", []),
            "radar_chart_data": viz_data.get("radar_chart", {}),
            "rankings": rankings,
            "best_model": self.best_model,
            "summary": {
                "n_models": len(self.results),
                "task_type": list(self.results.values())[0]["task_type"] if self.results else None
            }
        }
    
    def _calculate_rankings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Calculate model rankings for each metric."""
        if not self.results:
            return {}
        
        first_result = list(self.results.values())[0]
        task_type = first_result["task_type"]
        
        if task_type == "regression":
            metrics = ["mae", "rmse", "mape", "r2"]
            lower_better = {"mae": True, "rmse": True, "mape": True, "r2": False}
        else:
            metrics = ["accuracy", "precision", "recall", "f1_score"]
            lower_better = {m: False for m in metrics}
        
        rankings = {}
        for metric in metrics:
            metric_values = []
            for name, data in self.results.items():
                val = data["metrics"].get(metric)
                if val is not None:
                    metric_values.append({"model": name, "value": val})
            
            # Sort by metric value
            is_lower = lower_better.get(metric, True)
            metric_values.sort(key=lambda x: x["value"], reverse=not is_lower)
            
            # Add rank
            for i, item in enumerate(metric_values):
                item["rank"] = i + 1
            
            rankings[metric] = metric_values
        
        return rankings


# Utility function for quick metrics
def quick_regression_report(y_true, y_pred, model_name: str = "Model") -> str:
    """Print a formatted regression metrics report."""
    metrics = MetricsCalculator.regression_metrics(y_true, y_pred)
    
    report = f"""
╔══════════════════════════════════════════════════════════╗
║  {model_name:^52}  ║
╠══════════════════════════════════════════════════════════╣
║  MAE:     {metrics['mae']:>10.4f}    R²:        {metrics['r2']:>10.4f}  ║
║  RMSE:    {metrics['rmse']:>10.4f}    Adj R²:    {metrics['adjusted_r2']:>10.4f}  ║
║  MAPE:    {metrics['mape']:>10.2f}%   Max Error: {metrics['max_error']:>10.4f}  ║
║  Samples: {metrics['n_samples']:>10}                              ║
╚══════════════════════════════════════════════════════════╝
"""
    print(report)
    return report


def quick_classification_report(y_true, y_pred, model_name: str = "Model") -> str:
    """Print a formatted classification metrics report."""
    metrics = MetricsCalculator.classification_metrics(y_true, y_pred)
    
    report = f"""
╔══════════════════════════════════════════════════════════╗
║  {model_name:^52}  ║
╠══════════════════════════════════════════════════════════╣
║  Accuracy:    {metrics['accuracy']:>10.4f}    F1 Score:  {metrics['f1_score']:>10.4f}  ║
║  Precision:   {metrics['precision']:>10.4f}    Recall:    {metrics['recall']:>10.4f}  ║
║  Specificity: {metrics['specificity']:>10.4f}    Classes:   {metrics['n_classes']:>10}  ║
║  Samples:     {metrics['n_samples']:>10}                              ║
╚══════════════════════════════════════════════════════════╝
"""
    print(report)
    return report


if __name__ == "__main__":
    # Test regression metrics
    np.random.seed(42)
    y_true = np.random.uniform(100, 500, 1000)
    y_pred = y_true + np.random.normal(0, 20, 1000)
    
    print("=== Regression Metrics Test ===")
    metrics = MetricsCalculator.regression_metrics(y_true, y_pred)
    print(metrics)
    quick_regression_report(y_true, y_pred, "XGBoost Forecaster")
    
    # Test classification metrics
    y_true_cls = np.random.choice(["healthy", "warning", "critical"], 500)
    y_pred_cls = y_true_cls.copy()
    # Add some noise
    noise_idx = np.random.choice(500, 50, replace=False)
    y_pred_cls[noise_idx] = np.random.choice(["healthy", "warning", "critical"], 50)
    
    print("\n=== Classification Metrics Test ===")
    cls_metrics = MetricsCalculator.classification_metrics(y_true_cls, y_pred_cls)
    print(f"Accuracy: {cls_metrics['accuracy']}")
    print(f"Confusion Matrix:\n{np.array(cls_metrics['confusion_matrix'])}")
    quick_classification_report(y_true_cls, y_pred_cls, "Random Forest Classifier")

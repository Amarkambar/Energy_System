# models/hyperparameter_tuning.py — Optuna-based Hyperparameter Optimization

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Callable
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, f1_score
import warnings
import json
import os
warnings.filterwarnings("ignore")

try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("[Warning] Optuna not installed. Install with: pip install optuna")


class HyperparameterTuner:
    """
    Automated hyperparameter tuning using Optuna.
    Supports XGBoost, Random Forest, LSTM, and other models.
    """
    
    def __init__(
        self,
        n_trials: int = 50,
        timeout: int = 600,
        cv_folds: int = 5,
        random_state: int = 42,
        direction: str = "minimize"
    ):
        if not OPTUNA_AVAILABLE:
            raise ImportError("Optuna is required. Install with: pip install optuna")
        
        self.n_trials = n_trials
        self.timeout = timeout
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.direction = direction
        
        self.study = None
        self.best_params = None
        self.best_score = None
        self.optimization_history = []
    
    def _xgboost_objective(self, trial, X, y, is_time_series=False):
        """Objective function for XGBoost hyperparameter tuning."""
        try:
            from xgboost import XGBRegressor
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor as XGBRegressor
        
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "random_state": self.random_state,
            "n_jobs": -1
        }
        
        model = XGBRegressor(**params)
        
        if is_time_series:
            cv = TimeSeriesSplit(n_splits=self.cv_folds)
        else:
            cv = self.cv_folds
        
        scores = cross_val_score(
            model, X, y, cv=cv,
            scoring="neg_mean_squared_error"
        )
        
        return -scores.mean()  # Return MSE (lower is better)
    
    def _random_forest_classifier_objective(self, trial, X, y):
        """Objective function for Random Forest classifier."""
        from sklearn.ensemble import RandomForestClassifier
        
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
            "class_weight": trial.suggest_categorical("class_weight", ["balanced", None]),
            "random_state": self.random_state,
            "n_jobs": -1
        }
        
        model = RandomForestClassifier(**params)
        
        scores = cross_val_score(
            model, X, y, cv=self.cv_folds,
            scoring="f1_weighted"
        )
        
        return scores.mean()  # Return F1 (higher is better)
    
    def _lstm_objective(self, trial, X_train, y_train, X_val, y_val):
        """Objective function for LSTM hyperparameter tuning."""
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        
        # Hyperparameters to tune
        hidden_size = trial.suggest_int("hidden_size", 32, 256)
        num_layers = trial.suggest_int("num_layers", 1, 3)
        dropout = trial.suggest_float("dropout", 0.1, 0.5)
        learning_rate = trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True)
        batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
        
        # Build model
        class SimpleLSTM(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                                   batch_first=True, dropout=dropout if num_layers > 1 else 0)
                self.fc = nn.Linear(hidden_size, 1)
            
            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = SimpleLSTM(X_train.shape[2], hidden_size, num_layers, dropout).to(device)
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        
        # Data loaders
        train_data = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
        train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
        
        # Train for limited epochs
        model.train()
        for epoch in range(20):  # Quick training for tuning
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                optimizer.zero_grad()
                output = model(batch_X)
                loss = criterion(output, batch_y)
                loss.backward()
                optimizer.step()
        
        # Validate
        model.eval()
        with torch.no_grad():
            X_val_tensor = torch.FloatTensor(X_val).to(device)
            y_pred = model(X_val_tensor).cpu().numpy()
        
        mse = mean_squared_error(y_val, y_pred)
        return mse
    
    def tune_xgboost(
        self,
        X: np.ndarray,
        y: np.ndarray,
        is_time_series: bool = True
    ) -> Dict[str, Any]:
        """
        Tune XGBoost regressor hyperparameters.
        """
        print(f"[Optuna] Tuning XGBoost ({self.n_trials} trials)...")
        
        self.study = optuna.create_study(
            direction="minimize",
            sampler=TPESampler(seed=self.random_state)
        )
        
        self.study.optimize(
            lambda trial: self._xgboost_objective(trial, X, y, is_time_series),
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=True
        )
        
        self.best_params = self.study.best_params
        self.best_score = self.study.best_value
        self._record_history()
        
        print(f"[Optuna] Best MSE: {self.best_score:.4f}")
        print(f"[Optuna] Best params: {self.best_params}")
        
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "n_trials": len(self.study.trials),
            "optimization_history": self.optimization_history
        }
    
    def tune_random_forest_classifier(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Dict[str, Any]:
        """
        Tune Random Forest classifier hyperparameters.
        """
        print(f"[Optuna] Tuning Random Forest Classifier ({self.n_trials} trials)...")
        
        self.study = optuna.create_study(
            direction="maximize",  # F1 score
            sampler=TPESampler(seed=self.random_state)
        )
        
        self.study.optimize(
            lambda trial: self._random_forest_classifier_objective(trial, X, y),
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=True
        )
        
        self.best_params = self.study.best_params
        self.best_score = self.study.best_value
        self._record_history()
        
        print(f"[Optuna] Best F1: {self.best_score:.4f}")
        print(f"[Optuna] Best params: {self.best_params}")
        
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "n_trials": len(self.study.trials),
            "optimization_history": self.optimization_history
        }
    
    def tune_lstm(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, Any]:
        """
        Tune LSTM hyperparameters.
        """
        print(f"[Optuna] Tuning LSTM ({self.n_trials} trials)...")
        
        self.study = optuna.create_study(
            direction="minimize",
            sampler=TPESampler(seed=self.random_state)
        )
        
        self.study.optimize(
            lambda trial: self._lstm_objective(trial, X_train, y_train, X_val, y_val),
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=True
        )
        
        self.best_params = self.study.best_params
        self.best_score = self.study.best_value
        self._record_history()
        
        print(f"[Optuna] Best MSE: {self.best_score:.4f}")
        print(f"[Optuna] Best params: {self.best_params}")
        
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "n_trials": len(self.study.trials),
            "optimization_history": self.optimization_history
        }
    
    def _record_history(self):
        """Record optimization history for visualization."""
        if self.study is None:
            return
        
        self.optimization_history = []
        for i, trial in enumerate(self.study.trials):
            self.optimization_history.append({
                "trial": i + 1,
                "value": trial.value if trial.value is not None else None,
                "params": trial.params,
                "state": str(trial.state)
            })
    
    def get_visualization_data(self) -> Dict[str, Any]:
        """Get data for frontend visualization."""
        if self.study is None:
            return {}
        
        # Optimization history chart data
        history_data = []
        best_so_far = float("inf") if self.direction == "minimize" else float("-inf")
        
        for trial in self.study.trials:
            if trial.value is None:
                continue
            
            if self.direction == "minimize":
                best_so_far = min(best_so_far, trial.value)
            else:
                best_so_far = max(best_so_far, trial.value)
            
            history_data.append({
                "trial": trial.number + 1,
                "value": round(trial.value, 6),
                "best_so_far": round(best_so_far, 6)
            })
        
        # Parameter importance (if available)
        try:
            importance = optuna.importance.get_param_importances(self.study)
            param_importance = [
                {"param": k, "importance": round(v, 4)}
                for k, v in importance.items()
            ]
        except Exception:
            param_importance = []
        
        return {
            "history": history_data,
            "param_importance": param_importance,
            "best_params": self.best_params,
            "best_score": round(self.best_score, 6) if self.best_score else None,
            "n_trials": len(self.study.trials)
        }
    
    def save_results(self, path: str):
        """Save tuning results to JSON."""
        results = {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "optimization_history": self.optimization_history
        }
        
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"[Optuna] Results saved to {path}")


class GridSearchTuner:
    """
    Fallback grid search tuner when Optuna is not available.
    """
    
    def __init__(self, cv_folds: int = 5, random_state: int = 42):
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.best_params = None
        self.best_score = None
        self.results = []
    
    def tune_xgboost(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Simple grid search for XGBoost."""
        from sklearn.model_selection import GridSearchCV
        try:
            from xgboost import XGBRegressor
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor as XGBRegressor
        
        param_grid = {
            "n_estimators": [100, 300, 500],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.8, 1.0]
        }
        
        print("[GridSearch] Tuning XGBoost...")
        
        grid_search = GridSearchCV(
            XGBRegressor(random_state=self.random_state, n_jobs=-1),
            param_grid,
            cv=TimeSeriesSplit(n_splits=self.cv_folds),
            scoring="neg_mean_squared_error",
            n_jobs=-1,
            verbose=1
        )
        
        grid_search.fit(X, y)
        
        self.best_params = grid_search.best_params_
        self.best_score = -grid_search.best_score_
        
        print(f"[GridSearch] Best MSE: {self.best_score:.4f}")
        print(f"[GridSearch] Best params: {self.best_params}")
        
        return {
            "best_params": self.best_params,
            "best_score": self.best_score
        }


def tune_all_models(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Tune hyperparameters for all models.
    """
    from models.ml_models import get_feature_cols
    
    print("\n" + "=" * 50)
    print("HYPERPARAMETER TUNING (Optuna)")
    print("=" * 50)
    
    results = {}
    
    # Prepare data
    feature_cols = get_feature_cols(df)
    X = df[feature_cols].fillna(0).values
    y_reg = df["consumption_kwh"].values
    
    # Create classification labels for maintenance
    score = (
        (df["consumption_kwh"] > df["consumption_kwh"].quantile(0.85)).astype(int) * 2 +
        (df.get("voltage", pd.Series([230]*len(df))).between(225, 235) == False).astype(int) +
        (df.get("temperature", pd.Series([25]*len(df))) > 35).astype(int)
    )
    y_cls = pd.cut(score, bins=[-1, 0, 2, 10], labels=[0, 1, 2]).astype(int).values
    
    if OPTUNA_AVAILABLE:
        tuner = HyperparameterTuner(n_trials=30, timeout=300)
        
        # Tune XGBoost
        print("\n[1/2] Tuning XGBoost Forecaster...")
        results["xgboost"] = tuner.tune_xgboost(X, y_reg, is_time_series=True)
        
        # Tune Random Forest
        print("\n[2/2] Tuning Random Forest Classifier...")
        tuner2 = HyperparameterTuner(n_trials=30, timeout=300)
        results["random_forest"] = tuner2.tune_random_forest_classifier(X, y_cls)
    else:
        tuner = GridSearchTuner()
        results["xgboost"] = tuner.tune_xgboost(X, y_reg)
    
    # Save results
    os.makedirs("models/saved", exist_ok=True)
    with open("models/saved/hyperparameter_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n[Tuning] All hyperparameters tuned!")
    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")
    from data.pipeline import run_pipeline
    
    df = run_pipeline()
    results = tune_all_models(df)
    
    print("\n=== Final Results ===")
    for model, res in results.items():
        print(f"\n{model}:")
        print(f"  Best Score: {res.get('best_score')}")
        print(f"  Best Params: {res.get('best_params')}")

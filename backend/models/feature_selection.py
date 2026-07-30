# models/feature_selection.py — Feature Selection & PCA for Energy Diagnostics

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any
from sklearn.feature_selection import (
    SelectKBest, f_regression, f_classif, mutual_info_regression,
    RFE, VarianceThreshold
)
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")


class FeatureSelector:
    """
    Feature selection utilities for energy data.
    Supports SelectKBest, RFE, and Variance Threshold methods.
    """
    
    def __init__(self):
        self.selected_features: List[str] = []
        self.feature_scores: Dict[str, float] = {}
        self.scaler = StandardScaler()
    
    def select_k_best(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        k: int = 10,
        score_func: str = "f_regression"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Select top K features using univariate statistical tests.
        
        Args:
            X: Feature dataframe
            y: Target variable
            k: Number of features to select
            score_func: Scoring function ('f_regression', 'f_classif', 'mutual_info')
        
        Returns:
            Tuple of (selected features DataFrame, metadata dict)
        """
        # Handle NaN values
        X_clean = X.fillna(0)
        y_clean = y.fillna(y.mean() if y.dtype in [np.float64, np.float32] else y.mode()[0])
        
        # Select scoring function
        if score_func == "f_regression":
            scorer = f_regression
        elif score_func == "f_classif":
            scorer = f_classif
        elif score_func == "mutual_info":
            scorer = mutual_info_regression
        else:
            scorer = f_regression
        
        # Adjust k if greater than number of features
        k = min(k, X_clean.shape[1])
        
        selector = SelectKBest(score_func=scorer, k=k)
        X_selected = selector.fit_transform(X_clean, y_clean)
        
        # Get feature scores and names
        scores = selector.scores_
        mask = selector.get_support()
        
        self.selected_features = list(X.columns[mask])
        self.feature_scores = dict(zip(X.columns, scores))
        
        # Sort features by score
        sorted_features = sorted(
            self.feature_scores.items(),
            key=lambda x: x[1] if not np.isnan(x[1]) else 0,
            reverse=True
        )
        
        metadata = {
            "method": "SelectKBest",
            "score_func": score_func,
            "k": k,
            "n_features_in": X.shape[1],
            "n_features_out": len(self.selected_features),
            "selected_features": self.selected_features,
            "feature_scores": [
                {"feature": f, "score": round(float(s), 4) if not np.isnan(s) else 0}
                for f, s in sorted_features
            ],
            "top_features": sorted_features[:k]
        }
        
        return X[self.selected_features], metadata
    
    def rfe_selection(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        estimator,
        n_features_to_select: int = 10,
        step: int = 1
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Recursive Feature Elimination (RFE) using a given estimator.
        
        Args:
            X: Feature dataframe
            y: Target variable
            estimator: Sklearn estimator with feature_importances_ or coef_
            n_features_to_select: Number of features to keep
            step: Number of features to remove at each iteration
        
        Returns:
            Tuple of (selected features DataFrame, metadata dict)
        """
        X_clean = X.fillna(0)
        y_clean = y.fillna(y.mean() if y.dtype in [np.float64, np.float32] else y.mode()[0])
        
        n_features_to_select = min(n_features_to_select, X_clean.shape[1])
        
        rfe = RFE(
            estimator=estimator,
            n_features_to_select=n_features_to_select,
            step=step
        )
        rfe.fit(X_clean, y_clean)
        
        mask = rfe.support_
        rankings = rfe.ranking_
        
        self.selected_features = list(X.columns[mask])
        self.feature_scores = dict(zip(X.columns, 1 / rankings))
        
        # Get feature rankings
        feature_rankings = sorted(
            zip(X.columns, rankings),
            key=lambda x: x[1]
        )
        
        metadata = {
            "method": "RFE",
            "estimator": type(estimator).__name__,
            "n_features_in": X.shape[1],
            "n_features_out": len(self.selected_features),
            "selected_features": self.selected_features,
            "feature_rankings": [
                {"feature": f, "rank": int(r)}
                for f, r in feature_rankings
            ]
        }
        
        return X[self.selected_features], metadata
    
    def variance_threshold(
        self,
        X: pd.DataFrame,
        threshold: float = 0.01
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Remove low-variance features.
        
        Args:
            X: Feature dataframe
            threshold: Variance threshold (features with variance below this are removed)
        
        Returns:
            Tuple of (filtered features DataFrame, metadata dict)
        """
        X_clean = X.fillna(0)
        
        # Scale first to make variance comparable
        X_scaled = self.scaler.fit_transform(X_clean)
        
        selector = VarianceThreshold(threshold=threshold)
        selector.fit(X_scaled)
        
        mask = selector.get_support()
        variances = selector.variances_
        
        self.selected_features = list(X.columns[mask])
        removed_features = list(X.columns[~mask])
        
        feature_variances = sorted(
            zip(X.columns, variances),
            key=lambda x: x[1],
            reverse=True
        )
        
        metadata = {
            "method": "VarianceThreshold",
            "threshold": threshold,
            "n_features_in": X.shape[1],
            "n_features_out": len(self.selected_features),
            "n_removed": len(removed_features),
            "selected_features": self.selected_features,
            "removed_features": removed_features,
            "feature_variances": [
                {"feature": f, "variance": round(float(v), 6)}
                for f, v in feature_variances
            ]
        }
        
        return X[self.selected_features], metadata
    
    def get_feature_importance_json(self) -> List[Dict[str, Any]]:
        """Return feature scores in JSON-friendly format for frontend."""
        sorted_scores = sorted(
            self.feature_scores.items(),
            key=lambda x: x[1] if not np.isnan(x[1]) else 0,
            reverse=True
        )
        return [
            {"feature": f, "importance": round(float(s), 4) if not np.isnan(s) else 0}
            for f, s in sorted_scores
        ]


class PCAReducer:
    """
    Principal Component Analysis for dimensionality reduction.
    Provides explained variance analysis and component interpretation.
    """
    
    def __init__(self):
        self.pca: Optional[PCA] = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.n_components: int = 0
        self.explained_variance_ratio_: Optional[np.ndarray] = None
        self.components_: Optional[np.ndarray] = None
    
    def fit_transform(
        self,
        X: pd.DataFrame,
        n_components: Optional[int] = None,
        variance_threshold: float = 0.95
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Fit PCA and transform data.
        
        Args:
            X: Feature dataframe
            n_components: Number of components (if None, auto-select based on variance)
            variance_threshold: Cumulative variance threshold for auto-selection
        
        Returns:
            Tuple of (transformed data, metadata dict)
        """
        X_clean = X.fillna(0)
        self.feature_names = list(X.columns)
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X_clean)
        
        # If n_components not specified, find optimal based on variance threshold
        if n_components is None:
            # First fit with all components
            temp_pca = PCA()
            temp_pca.fit(X_scaled)
            cumsum = np.cumsum(temp_pca.explained_variance_ratio_)
            n_components = int(np.argmax(cumsum >= variance_threshold) + 1)
            n_components = max(1, min(n_components, X_scaled.shape[1]))
        
        self.n_components = min(n_components, X_scaled.shape[1])
        
        # Fit PCA
        self.pca = PCA(n_components=self.n_components)
        X_transformed = self.pca.fit_transform(X_scaled)
        
        self.explained_variance_ratio_ = self.pca.explained_variance_ratio_
        self.components_ = self.pca.components_
        
        metadata = self._build_metadata()
        
        return X_transformed, metadata
    
    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transform new data using fitted PCA."""
        if self.pca is None:
            raise ValueError("PCA not fitted. Call fit_transform first.")
        
        X_clean = X.fillna(0)
        X_scaled = self.scaler.transform(X_clean)
        return self.pca.transform(X_scaled)
    
    def get_explained_variance(self) -> Dict[str, Any]:
        """Get explained variance data for visualization."""
        if self.pca is None:
            return {"error": "PCA not fitted"}
        
        individual = self.explained_variance_ratio_
        cumulative = np.cumsum(individual)
        
        return {
            "n_components": self.n_components,
            "total_variance_explained": round(float(cumulative[-1]), 4),
            "individual_variance": [
                {
                    "component": f"PC{i+1}",
                    "variance_ratio": round(float(v), 4),
                    "variance_percent": round(float(v) * 100, 2)
                }
                for i, v in enumerate(individual)
            ],
            "cumulative_variance": [
                {
                    "component": f"PC{i+1}",
                    "cumulative_ratio": round(float(c), 4),
                    "cumulative_percent": round(float(c) * 100, 2)
                }
                for i, c in enumerate(cumulative)
            ]
        }
    
    def get_component_loadings(self, top_n: int = 5) -> Dict[str, Any]:
        """
        Get feature loadings for each principal component.
        Shows which original features contribute most to each PC.
        """
        if self.pca is None or self.components_ is None:
            return {"error": "PCA not fitted"}
        
        loadings = []
        for i, component in enumerate(self.components_):
            # Get absolute loadings sorted
            abs_loadings = np.abs(component)
            top_indices = np.argsort(abs_loadings)[::-1][:top_n]
            
            top_features = [
                {
                    "feature": self.feature_names[idx],
                    "loading": round(float(component[idx]), 4),
                    "abs_loading": round(float(abs_loadings[idx]), 4)
                }
                for idx in top_indices
            ]
            
            loadings.append({
                "component": f"PC{i+1}",
                "variance_explained": round(float(self.explained_variance_ratio_[i]) * 100, 2),
                "top_features": top_features
            })
        
        return {"component_loadings": loadings}
    
    def _build_metadata(self) -> Dict[str, Any]:
        """Build comprehensive metadata dictionary."""
        variance_data = self.get_explained_variance()
        loadings_data = self.get_component_loadings()
        
        return {
            "method": "PCA",
            "n_features_in": len(self.feature_names),
            "n_components": self.n_components,
            **variance_data,
            **loadings_data
        }
    
    def get_visualization_data(self) -> Dict[str, Any]:
        """Get data formatted for frontend charts."""
        if self.pca is None:
            return {}
        
        variance_data = self.get_explained_variance()
        
        # Scree plot data
        scree_data = [
            {
                "component": f"PC{i+1}",
                "individual": round(float(v) * 100, 2),
                "cumulative": round(float(c) * 100, 2)
            }
            for i, (v, c) in enumerate(zip(
                self.explained_variance_ratio_,
                np.cumsum(self.explained_variance_ratio_)
            ))
        ]
        
        # Component loadings heatmap data
        loadings_matrix = []
        for i, component in enumerate(self.components_):
            for j, loading in enumerate(component):
                loadings_matrix.append({
                    "component": f"PC{i+1}",
                    "feature": self.feature_names[j][:15],  # Truncate long names
                    "loading": round(float(loading), 3)
                })
        
        return {
            "scree_plot": scree_data,
            "loadings_matrix": loadings_matrix,
            "summary": {
                "n_components": self.n_components,
                "total_variance": round(float(np.sum(self.explained_variance_ratio_)) * 100, 2),
                "n_features_original": len(self.feature_names)
            }
        }


def auto_feature_selection(
    X: pd.DataFrame,
    y: pd.Series,
    task_type: str = "regression",
    target_n_features: int = 15
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Automatic feature selection combining multiple methods.
    
    Args:
        X: Feature dataframe
        y: Target variable
        task_type: 'regression' or 'classification'
        target_n_features: Target number of features
    
    Returns:
        Tuple of (selected features DataFrame, combined metadata)
    """
    selector = FeatureSelector()
    
    # Step 1: Remove low variance features
    X_var, var_meta = selector.variance_threshold(X, threshold=0.01)
    
    # Step 2: Select K best
    score_func = "f_regression" if task_type == "regression" else "f_classif"
    k = min(target_n_features, X_var.shape[1])
    X_final, kbest_meta = selector.select_k_best(X_var, y, k=k, score_func=score_func)
    
    combined_meta = {
        "auto_selection": True,
        "task_type": task_type,
        "steps": [
            {"step": 1, "method": "VarianceThreshold", **var_meta},
            {"step": 2, "method": "SelectKBest", **kbest_meta}
        ],
        "final_features": list(X_final.columns),
        "n_features_original": X.shape[1],
        "n_features_final": X_final.shape[1]
    }
    
    return X_final, combined_meta


if __name__ == "__main__":
    # Test feature selection
    np.random.seed(42)
    n_samples = 1000
    
    # Create test data
    X = pd.DataFrame({
        "consumption_kwh": np.random.uniform(100, 500, n_samples),
        "temperature": np.random.uniform(15, 35, n_samples),
        "humidity": np.random.uniform(30, 90, n_samples),
        "voltage": np.random.normal(230, 5, n_samples),
        "hour": np.random.randint(0, 24, n_samples),
        "is_weekend": np.random.randint(0, 2, n_samples),
        "lag_1": np.random.uniform(100, 500, n_samples),
        "lag_24": np.random.uniform(100, 500, n_samples),
        "rolling_mean_6": np.random.uniform(100, 500, n_samples),
        "constant_feature": np.ones(n_samples),  # Should be removed
    })
    y = X["consumption_kwh"] + np.random.normal(0, 10, n_samples)
    
    print("=== Feature Selection Tests ===\n")
    
    # Test SelectKBest
    selector = FeatureSelector()
    X_sel, meta = selector.select_k_best(X, y, k=5)
    print(f"SelectKBest - Selected: {meta['selected_features']}")
    print(f"Top 3 scores: {meta['top_features'][:3]}\n")
    
    # Test Variance Threshold
    X_var, var_meta = selector.variance_threshold(X, threshold=0.01)
    print(f"VarianceThreshold - Removed: {var_meta['removed_features']}")
    print(f"Kept: {len(var_meta['selected_features'])} features\n")
    
    # Test PCA
    print("=== PCA Tests ===\n")
    pca_reducer = PCAReducer()
    X_pca, pca_meta = pca_reducer.fit_transform(X, n_components=5)
    print(f"PCA - Components: {pca_meta['n_components']}")
    print(f"Total variance explained: {pca_meta['total_variance_explained']:.2%}")
    
    variance_data = pca_reducer.get_explained_variance()
    for comp in variance_data['individual_variance']:
        print(f"  {comp['component']}: {comp['variance_percent']:.1f}%")
    
    print("\n=== Auto Selection ===\n")
    X_auto, auto_meta = auto_feature_selection(X, y, target_n_features=6)
    print(f"Auto-selected features: {auto_meta['final_features']}")

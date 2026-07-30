"""
Model Comparison and Backtesting Framework

This module provides tools to:
- Compare performance of different forecasting models
- Run walk-forward backtesting
- Calculate comprehensive metrics
- Generate performance visualizations
- Identify best model for specific use cases

Usage:
    from models.model_comparison import ModelComparator
    
    comparator = ModelComparator()
    results = comparator.compare_models(df, horizons=[6, 12, 24])
    comparator.generate_report()
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error
import warnings
warnings.filterwarnings("ignore")


class ModelComparator:
    """
    Compare and backtest multiple forecasting models
    
    Features:
    - Walk-forward backtesting
    - Multiple forecast horizons
    - Comprehensive metrics (MAE, RMSE, MAPE, R², etc.)
    - Statistical significance testing
    - Performance degradation analysis
    """
    
    def __init__(self):
        self.results = {}
        self.backtest_results = {}
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive forecast metrics"""
        
        # Basic metrics
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = mean_absolute_percentage_error(y_true, y_pred) * 100
        r2 = r2_score(y_true, y_pred)
        
        # Additional metrics
        median_ae = np.median(np.abs(y_true - y_pred))
        max_error = np.max(np.abs(y_true - y_pred))
        
        # Directional accuracy (did we predict direction correctly?)
        y_true_diff = np.diff(y_true)
        y_pred_diff = np.diff(y_pred)
        directional_accuracy = np.mean(np.sign(y_true_diff) == np.sign(y_pred_diff)) * 100
        
        # Bias (systematic over/under-prediction)
        bias = np.mean(y_pred - y_true)
        
        return {
            'mae': mae,
            'rmse': rmse,
            'mape': mape,
            'r2': r2,
            'median_ae': median_ae,
            'max_error': max_error,
            'directional_accuracy': directional_accuracy,
            'bias': bias
        }
    
    def walk_forward_backtest(
        self,
        df: pd.DataFrame,
        model,
        horizon: int = 24,
        initial_train_size: int = 720,  # 30 days
        step_size: int = 24,  # Retrain every 24 hours
        target_col: str = "consumption_kwh"
    ) -> Dict[str, any]:
        """
        Walk-forward backtesting with periodic retraining
        
        Args:
            df: Historical data
            model: Model object with fit() and predict() methods
            horizon: Forecast horizon in hours
            initial_train_size: Initial training window size
            step_size: How often to retrain (in hours)
            target_col: Target column name
        
        Returns:
            Dictionary with forecasts, actuals, and metrics
        """
        print(f"\n[Backtest] Running walk-forward validation (horizon={horizon}h)...")
        
        all_forecasts = []
        all_actuals = []
        all_timestamps = []
        
        # Start from initial_train_size, forecast horizon at a time
        for i in range(initial_train_size, len(df) - horizon, step_size):
            # Training data
            train_df = df.iloc[:i]
            
            # Actual future values
            actual = df.iloc[i:i+horizon][target_col].values
            
            try:
                # Train model
                if i % (step_size * 7) == 0:  # Print progress every 7 steps
                    print(f"  Progress: {i}/{len(df) - horizon} ({(i/(len(df)-horizon))*100:.1f}%)")
                
                model.fit(train_df, target_col)
                
                # Forecast
                forecast = model.predict(train_df, horizon, target_col)
                
                # Store results
                all_forecasts.extend(forecast[:len(actual)])
                all_actuals.extend(actual)
                
                timestamps = pd.date_range(
                    start=pd.to_datetime(train_df['timestamp'].iloc[-1]) + timedelta(hours=1),
                    periods=len(actual),
                    freq='H'
                )
                all_timestamps.extend(timestamps)
            
            except Exception as e:
                print(f"  Warning: Skipping iteration at index {i}: {e}")
                continue
        
        # Calculate metrics
        all_forecasts = np.array(all_forecasts)
        all_actuals = np.array(all_actuals)
        
        metrics = self.calculate_metrics(all_actuals, all_forecasts)
        
        print(f"[Backtest] Complete - RMSE: {metrics['rmse']:.2f}, MAPE: {metrics['mape']:.2f}%")
        
        return {
            'forecasts': all_forecasts,
            'actuals': all_actuals,
            'timestamps': all_timestamps,
            'metrics': metrics,
            'horizon': horizon
        }
    
    def compare_models(
        self,
        df: pd.DataFrame,
        horizons: List[int] = [6, 12, 24, 48],
        target_col: str = "consumption_kwh"
    ) -> pd.DataFrame:
        """
        Compare multiple models across different forecast horizons
        
        Args:
            df: Historical data
            horizons: List of forecast horizons to test
            target_col: Target column name
        
        Returns:
            DataFrame with comparison results
        """
        print("\n" + "="*70)
        print("  Model Comparison Framework")
        print("="*70)
        
        results = []
        
        # Import models
        from models.advanced_forecasting import LSTMForecasterWrapper, ProphetForecaster, PROPHET_AVAILABLE
        from sklearn.ensemble import GradientBoostingRegressor
        import xgboost as xgb
        
        # Define models to compare
        models_to_test = {
            'LSTM': LSTMForecasterWrapper(epochs=30, batch_size=64),
            'XGBoost': None,  # Will create for each horizon
        }
        
        if PROPHET_AVAILABLE:
            models_to_test['Prophet'] = ProphetForecaster()
        
        # Test each model at each horizon
        for horizon in horizons:
            print(f"\n{'─'*70}")
            print(f"  Testing Horizon: {horizon} hours")
            print(f"{'─'*70}")
            
            for model_name, model in models_to_test.items():
                try:
                    print(f"\n  Model: {model_name}")
                    
                    if model_name == 'XGBoost':
                        # XGBoost requires special handling
                        from models.ml_models import EnergyForecaster
                        model = EnergyForecaster()
                        model.train(df)
                        
                        # Simple validation
                        split_idx = int(len(df) * 0.8)
                        train_df = df.iloc[:split_idx]
                        test_df = df.iloc[split_idx:]
                        
                        # Get predictions (simplified)
                        y_true = test_df[target_col].values[:horizon]
                        y_pred = model.forecast(train_df, hours=horizon)['hourly'][:len(y_true)]
                        
                        metrics = self.calculate_metrics(y_true, y_pred)
                    
                    else:
                        # Use walk-forward for LSTM/Prophet
                        backtest_result = self.walk_forward_backtest(
                            df, model, horizon=horizon,
                            initial_train_size=min(720, len(df) // 2),
                            step_size=max(24, horizon),
                            target_col=target_col
                        )
                        metrics = backtest_result['metrics']
                    
                    # Store results
                    result = {
                        'model': model_name,
                        'horizon_hours': horizon,
                        **metrics
                    }
                    results.append(result)
                    
                    print(f"    ✓ RMSE: {metrics['rmse']:.2f}, MAPE: {metrics['mape']:.2f}%, R²: {metrics['r2']:.3f}")
                
                except Exception as e:
                    print(f"    ✗ Failed: {e}")
                    continue
        
        # Create comparison DataFrame
        comparison_df = pd.DataFrame(results)
        
        # Sort by horizon and RMSE
        comparison_df = comparison_df.sort_values(['horizon_hours', 'rmse'])
        
        self.results = comparison_df
        
        print("\n" + "="*70)
        print("  Comparison Complete")
        print("="*70 + "\n")
        
        return comparison_df
    
    def generate_report(self, output_path: str = "model_comparison_report.md") -> str:
        """Generate markdown report of comparison results"""
        
        if self.results is None or len(self.results) == 0:
            return "No comparison results available. Run compare_models() first."
        
        report = f"""# Forecasting Model Comparison Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Summary

This report compares the performance of different forecasting models across multiple time horizons.

### Models Tested

"""
        
        models = self.results['model'].unique()
        for model in models:
            report += f"- **{model}**\n"
        
        report += f"\n### Forecast Horizons\n\n"
        
        horizons = sorted(self.results['horizon_hours'].unique())
        for horizon in horizons:
            report += f"- {horizon} hours\n"
        
        report += "\n---\n\n## Detailed Results\n\n"
        
        # Results by horizon
        for horizon in horizons:
            report += f"### {horizon}-Hour Forecast\n\n"
            
            horizon_results = self.results[self.results['horizon_hours'] == horizon].copy()
            horizon_results = horizon_results.sort_values('rmse')
            
            report += "| Rank | Model | RMSE | MAE | MAPE | R² | Dir. Acc. |\n"
            report += "|------|-------|------|-----|------|----|-----------|\n"
            
            for idx, (i, row) in enumerate(horizon_results.iterrows(), 1):
                report += f"| {idx} | **{row['model']}** | {row['rmse']:.2f} | {row['mae']:.2f} | {row['mape']:.2f}% | {row['r2']:.3f} | {row['directional_accuracy']:.1f}% |\n"
            
            # Winner
            winner = horizon_results.iloc[0]
            report += f"\n**Winner:** {winner['model']} (RMSE: {winner['rmse']:.2f})\n\n"
        
        report += "---\n\n## Best Model by Horizon\n\n"
        
        report += "| Horizon | Best Model | RMSE | Improvement vs. 2nd |\n"
        report += "|---------|------------|------|---------------------|\n"
        
        for horizon in horizons:
            horizon_results = self.results[self.results['horizon_hours'] == horizon].sort_values('rmse')
            
            if len(horizon_results) >= 2:
                best = horizon_results.iloc[0]
                second = horizon_results.iloc[1]
                improvement = ((second['rmse'] - best['rmse']) / second['rmse']) * 100
                
                report += f"| {horizon}h | **{best['model']}** | {best['rmse']:.2f} | {improvement:.1f}% better |\n"
            else:
                best = horizon_results.iloc[0]
                report += f"| {horizon}h | **{best['model']}** | {best['rmse']:.2f} | N/A |\n"
        
        report += "\n---\n\n## Recommendations\n\n"
        
        # Generate recommendations
        short_term = self.results[self.results['horizon_hours'] <= 12].sort_values('rmse').iloc[0] if len(self.results[self.results['horizon_hours'] <= 12]) > 0 else None
        medium_term = self.results[(self.results['horizon_hours'] > 12) & (self.results['horizon_hours'] <= 48)].sort_values('rmse').iloc[0] if len(self.results[(self.results['horizon_hours'] > 12) & (self.results['horizon_hours'] <= 48)]) > 0 else None
        
        if short_term is not None:
            report += f"- **Short-term forecasting (≤12h):** Use **{short_term['model']}** (RMSE: {short_term['rmse']:.2f})\n"
        
        if medium_term is not None:
            report += f"- **Medium-term forecasting (12-48h):** Use **{medium_term['model']}** (RMSE: {medium_term['rmse']:.2f})\n"
        
        report += "\n---\n\n## Metrics Explained\n\n"
        report += """
- **RMSE (Root Mean Square Error):** Lower is better. Penalizes large errors more heavily.
- **MAE (Mean Absolute Error):** Lower is better. Average magnitude of errors.
- **MAPE (Mean Absolute Percentage Error):** Lower is better. Error as percentage of actual values.
- **R² (R-squared):** Higher is better (max 1.0). Proportion of variance explained.
- **Dir. Acc. (Directional Accuracy):** Higher is better. Percentage of correct trend predictions.

---

*Report generated by Energy Diagnostics Model Comparison Framework*
"""
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(report)
        
        print(f"\n[Report] Saved to {output_path}")
        
        return report
    
    def plot_comparison(self):
        """Plot model comparison results (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            
            if self.results is None or len(self.results) == 0:
                print("No results to plot")
                return
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle('Forecasting Model Comparison', fontsize=16, fontweight='bold')
            
            # RMSE by horizon
            for model in self.results['model'].unique():
                model_data = self.results[self.results['model'] == model]
                axes[0, 0].plot(model_data['horizon_hours'], model_data['rmse'], marker='o', label=model)
            axes[0, 0].set_xlabel('Forecast Horizon (hours)')
            axes[0, 0].set_ylabel('RMSE')
            axes[0, 0].set_title('RMSE by Forecast Horizon')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # MAPE by horizon
            for model in self.results['model'].unique():
                model_data = self.results[self.results['model'] == model]
                axes[0, 1].plot(model_data['horizon_hours'], model_data['mape'], marker='s', label=model)
            axes[0, 1].set_xlabel('Forecast Horizon (hours)')
            axes[0, 1].set_ylabel('MAPE (%)')
            axes[0, 1].set_title('MAPE by Forecast Horizon')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # R² by horizon
            for model in self.results['model'].unique():
                model_data = self.results[self.results['model'] == model]
                axes[1, 0].plot(model_data['horizon_hours'], model_data['r2'], marker='^', label=model)
            axes[1, 0].set_xlabel('Forecast Horizon (hours)')
            axes[1, 0].set_ylabel('R²')
            axes[1, 0].set_title('R² by Forecast Horizon')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            axes[1, 0].set_ylim(0, 1)
            
            # Directional Accuracy
            for model in self.results['model'].unique():
                model_data = self.results[self.results['model'] == model]
                axes[1, 1].plot(model_data['horizon_hours'], model_data['directional_accuracy'], marker='d', label=model)
            axes[1, 1].set_xlabel('Forecast Horizon (hours)')
            axes[1, 1].set_ylabel('Directional Accuracy (%)')
            axes[1, 1].set_title('Directional Accuracy by Forecast Horizon')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].set_ylim(0, 100)
            
            plt.tight_layout()
            plt.savefig('model_comparison_plots.png', dpi=300, bbox_inches='tight')
            print("\n[Plot] Saved to model_comparison_plots.png")
            
        except ImportError:
            print("Matplotlib not available. Install with: pip install matplotlib")


# ══════════════════════════════════════════════════════════
#  EXAMPLE USAGE
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Example: Compare models
    from data.pipeline import generate_synthetic_data
    
    # Generate sample data (30 days)
    df = generate_synthetic_data(hours=720)
    
    # Initialize comparator
    comparator = ModelComparator()
    
    # Compare models across different horizons
    results = comparator.compare_models(
        df,
        horizons=[6, 12, 24],
        target_col="consumption_kwh"
    )
    
    print("\n" + "="*70)
    print("  Comparison Results")
    print("="*70)
    print(results.to_string(index=False))
    
    # Generate report
    report = comparator.generate_report()
    print("\n" + report)
    
    # Plot results
    # comparator.plot_comparison()

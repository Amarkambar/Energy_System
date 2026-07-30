"""
Real Sensor Data Ingestion Pipeline

This module handles ingestion, validation, and processing of real industrial
sensor data from CSV files, replacing synthetic data generation.

Features:
- CSV validation (required columns, data types, completeness)
- Data quality checks (missing values, outliers, frequency)
- Automatic data profiling and statistics
- Compatibility with existing ML pipeline
- Support for multiple sensor types (smart meters, IoT sensors, weather)

Usage:
    from data.real_data_ingestion import RealDataIngestor
    
    ingestor = RealDataIngestor()
    
    # Validate CSV before ingestion
    validation = ingestor.validate_csv("sensor_data.csv")
    if validation["is_valid"]:
        df = ingestor.load_real_sensor_data("sensor_data.csv")
        # Continue with ML pipeline...
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RealDataIngestor:
    """Handles ingestion and validation of real industrial sensor data"""
    
    # Required columns for energy monitoring
    REQUIRED_COLUMNS = {
        "smart_meter": ["timestamp", "consumption_kwh"],
        "iot_sensor": ["timestamp", "temperature"],
        "full": ["timestamp", "consumption_kwh", "voltage"]
    }
    
    # Optional columns (will use if available)
    OPTIONAL_COLUMNS = [
        "voltage", "current", "power_factor", "load_factor",
        "temperature", "humidity", "pressure",
        "equipment_id", "plant_id", "sensor_id"
    ]
    
    def __init__(self):
        self.data_dir = Path("data/real")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.validation_log = []
    
    def validate_csv(self, filepath: str, data_type: str = "smart_meter") -> Dict:
        """
        Validate CSV file before ingestion
        
        Args:
            filepath: Path to CSV file
            data_type: Type of data ("smart_meter", "iot_sensor", "full")
        
        Returns:
            Dictionary with validation results:
            {
                "is_valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "stats": Dict (if valid)
            }
        """
        errors = []
        warnings = []
        stats = {}
        
        try:
            # Read CSV
            df = pd.read_csv(filepath)
            stats["total_rows"] = len(df)
            stats["total_columns"] = len(df.columns)
            
            # Check required columns
            required = self.REQUIRED_COLUMNS.get(data_type, self.REQUIRED_COLUMNS["smart_meter"])
            missing_cols = [col for col in required if col not in df.columns]
            
            if missing_cols:
                errors.append(f"Missing required columns: {missing_cols}")
                return {"is_valid": False, "errors": errors, "warnings": warnings}
            
            # Validate timestamp column
            if "timestamp" in df.columns:
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    stats["date_range"] = {
                        "start": str(df["timestamp"].min()),
                        "end": str(df["timestamp"].max()),
                        "duration_days": (df["timestamp"].max() - df["timestamp"].min()).days
                    }
                    
                    # Check for gaps
                    df_sorted = df.sort_values("timestamp")
                    time_diffs = df_sorted["timestamp"].diff()
                    median_interval = time_diffs.median()
                    
                    # Find large gaps (> 2x median interval)
                    large_gaps = time_diffs[time_diffs > median_interval * 2]
                    if len(large_gaps) > 0:
                        warnings.append(f"Found {len(large_gaps)} time gaps > 2x median interval")
                    
                    stats["median_interval"] = str(median_interval)
                    stats["sampling_frequency"] = self._infer_frequency(median_interval)
                    
                except Exception as e:
                    errors.append(f"Invalid timestamp format: {e}")
            
            # Validate numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            stats["numeric_columns"] = numeric_cols
            
            for col in required:
                if col == "timestamp":
                    continue
                    
                if col in df.columns:
                    # Check for missing values
                    missing_pct = (df[col].isna().sum() / len(df)) * 100
                    if missing_pct > 0:
                        if missing_pct > 20:
                            errors.append(f"Column '{col}' has {missing_pct:.1f}% missing values (>20% threshold)")
                        else:
                            warnings.append(f"Column '{col}' has {missing_pct:.1f}% missing values")
                    
                    # Check for negative values in consumption/voltage
                    if col in ["consumption_kwh", "voltage", "power"]:
                        negative_count = (df[col] < 0).sum()
                        if negative_count > 0:
                            errors.append(f"Column '{col}' has {negative_count} negative values (invalid)")
                    
                    # Check for constant values
                    if df[col].nunique() == 1:
                        warnings.append(f"Column '{col}' has constant value (no variation)")
                    
                    # Basic stats
                    if col in numeric_cols:
                        stats[f"{col}_stats"] = {
                            "min": float(df[col].min()),
                            "max": float(df[col].max()),
                            "mean": float(df[col].mean()),
                            "std": float(df[col].std()),
                            "missing_pct": float(missing_pct)
                        }
            
            # Check for duplicates
            duplicate_count = df.duplicated().sum()
            if duplicate_count > 0:
                warnings.append(f"Found {duplicate_count} duplicate rows")
                stats["duplicates"] = duplicate_count
            
            # Check data size (minimum 1 week for meaningful patterns)
            if "timestamp" in df.columns:
                duration_days = stats["date_range"]["duration_days"]
                if duration_days < 7:
                    warnings.append(f"Data covers only {duration_days} days. Recommend minimum 7 days for ML training.")
                elif duration_days < 30:
                    warnings.append(f"Data covers {duration_days} days. Recommend 30+ days for seasonal patterns.")
            
            # Check for outliers
            outlier_summary = self._detect_outliers(df, numeric_cols)
            if outlier_summary:
                stats["outliers"] = outlier_summary
                warnings.append(f"Found outliers in {len(outlier_summary)} columns (see stats)")
            
            is_valid = len(errors) == 0
            
            result = {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "stats": stats
            }
            
            # Log validation
            self.validation_log.append({
                "timestamp": datetime.now(),
                "filepath": filepath,
                "result": result
            })
            
            return result
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Failed to read CSV: {str(e)}"],
                "warnings": [],
                "stats": {}
            }
    
    def load_real_sensor_data(
        self,
        filepath: str,
        validate: bool = True,
        clean: bool = True,
        resample_freq: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load real sensor data from CSV
        
        Args:
            filepath: Path to CSV file
            validate: Run validation checks before loading
            clean: Apply automatic cleaning (remove duplicates, fill missing)
            resample_freq: Resample to fixed frequency (e.g., "1H", "15min")
        
        Returns:
            Cleaned DataFrame ready for ML pipeline
        """
        logger.info(f"Loading real sensor data from: {filepath}")
        
        # Validate first
        if validate:
            validation = self.validate_csv(filepath)
            if not validation["is_valid"]:
                raise ValueError(f"CSV validation failed: {validation['errors']}")
            
            if validation["warnings"]:
                logger.warning(f"Validation warnings: {validation['warnings']}")
        
        # Load CSV
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Convert timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
        
        # Clean data
        if clean:
            df = self._clean_data(df)
        
        # Resample if requested
        if resample_freq and "timestamp" in df.columns:
            df = self._resample_data(df, resample_freq)
        
        # Add metadata columns
        df["data_source"] = "real_sensor"
        df["ingestion_time"] = datetime.now()
        
        # Save to real data directory
        output_path = self.data_dir / f"processed_{Path(filepath).name}"
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved processed data to: {output_path}")
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply automatic data cleaning"""
        logger.info("Cleaning data...")
        
        original_rows = len(df)
        
        # Remove duplicates
        df = df.drop_duplicates()
        if len(df) < original_rows:
            logger.info(f"  Removed {original_rows - len(df)} duplicate rows")
        
        # Handle missing values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                # Forward fill for time series
                df[col] = df[col].fillna(method='ffill')
                # Backward fill for remaining
                df[col] = df[col].fillna(method='bfill')
                logger.info(f"  Filled {missing_count} missing values in '{col}'")
        
        # Remove outliers (Z-score > 5)
        for col in numeric_cols:
            if col in ["consumption_kwh", "voltage", "temperature"]:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outliers = (z_scores > 5).sum()
                if outliers > 0:
                    # Clip extreme outliers
                    df[col] = df[col].clip(
                        lower=df[col].quantile(0.001),
                        upper=df[col].quantile(0.999)
                    )
                    logger.info(f"  Clipped {outliers} outliers in '{col}'")
        
        return df
    
    def _resample_data(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """Resample data to fixed frequency"""
        logger.info(f"Resampling to {freq}...")
        
        df = df.set_index("timestamp")
        
        # Numeric columns: mean aggregation
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        df_resampled = df[numeric_cols].resample(freq).mean()
        
        # Forward fill any gaps (updated syntax)
        df_resampled = df_resampled.ffill()
        
        df_resampled = df_resampled.reset_index()
        
        logger.info(f"  Resampled from {len(df)} to {len(df_resampled)} rows")
        
        return df_resampled
    
    def _detect_outliers(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict:
        """Detect outliers using Z-score method"""
        outlier_summary = {}
        
        for col in numeric_cols:
            if col in df.columns and df[col].notna().sum() > 0:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_count = (z_scores > 3).sum()
                
                if outlier_count > 0:
                    outlier_summary[col] = {
                        "count": int(outlier_count),
                        "percentage": float((outlier_count / len(df)) * 100)
                    }
        
        return outlier_summary
    
    def _infer_frequency(self, median_interval: timedelta) -> str:
        """Infer sampling frequency from median interval"""
        seconds = median_interval.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)}s (sub-minute)"
        elif seconds < 3600:
            return f"{int(seconds/60)}min"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h (hourly)"
        else:
            return f"{int(seconds/86400)}d (daily)"
    
    def generate_data_quality_report(self, filepath: str) -> str:
        """
        Generate comprehensive data quality report
        
        Args:
            filepath: Path to CSV file
        
        Returns:
            Markdown-formatted report
        """
        validation = self.validate_csv(filepath)
        
        report = f"""# Data Quality Report
        
**File:** `{filepath}`  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Validation Status

**Status:** {'✅ PASS' if validation['is_valid'] else '❌ FAIL'}

### Errors
"""
        
        if validation["errors"]:
            for error in validation["errors"]:
                report += f"- ❌ {error}\n"
        else:
            report += "- None\n"
        
        report += "\n### Warnings\n"
        
        if validation["warnings"]:
            for warning in validation["warnings"]:
                report += f"- ⚠️  {warning}\n"
        else:
            report += "- None\n"
        
        report += "\n---\n\n## Dataset Statistics\n\n"
        
        stats = validation.get("stats", {})
        
        if "total_rows" in stats:
            report += f"**Total Rows:** {stats['total_rows']:,}\n"
            report += f"**Total Columns:** {stats['total_columns']}\n\n"
        
        if "date_range" in stats:
            dr = stats["date_range"]
            report += f"**Date Range:**\n"
            report += f"- Start: {dr['start']}\n"
            report += f"- End: {dr['end']}\n"
            report += f"- Duration: {dr['duration_days']} days\n\n"
        
        if "sampling_frequency" in stats:
            report += f"**Sampling Frequency:** {stats['sampling_frequency']}\n"
            report += f"**Median Interval:** {stats['median_interval']}\n\n"
        
        report += "### Column Statistics\n\n"
        
        for key, value in stats.items():
            if key.endswith("_stats"):
                col_name = key.replace("_stats", "")
                report += f"**{col_name}:**\n"
                report += f"- Min: {value['min']:.2f}\n"
                report += f"- Max: {value['max']:.2f}\n"
                report += f"- Mean: {value['mean']:.2f}\n"
                report += f"- Std Dev: {value['std']:.2f}\n"
                report += f"- Missing: {value['missing_pct']:.1f}%\n\n"
        
        if "outliers" in stats:
            report += "### Outliers Detected\n\n"
            for col, outlier_info in stats["outliers"].items():
                report += f"- **{col}:** {outlier_info['count']} outliers ({outlier_info['percentage']:.2f}%)\n"
        
        report += "\n---\n\n## Recommendations\n\n"
        
        if validation["is_valid"]:
            report += "✅ Dataset is ready for ML training\n\n"
            
            if stats.get("date_range", {}).get("duration_days", 0) < 30:
                report += "- ⚠️  Consider collecting more data (30+ days recommended)\n"
            
            if stats.get("outliers"):
                report += "- ⚠️  Review outliers before training (may affect model accuracy)\n"
        else:
            report += "❌ Fix errors before proceeding with ML training\n"
        
        return report
    
    def compare_with_synthetic(self, real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict:
        """
        Compare real sensor data with synthetic data
        
        Args:
            real_df: Real sensor DataFrame
            synthetic_df: Synthetic data DataFrame
        
        Returns:
            Dictionary with comparison metrics
        """
        comparison = {}
        
        # Compare distributions
        for col in ["consumption_kwh", "voltage", "temperature"]:
            if col in real_df.columns and col in synthetic_df.columns:
                comparison[col] = {
                    "real_mean": float(real_df[col].mean()),
                    "synthetic_mean": float(synthetic_df[col].mean()),
                    "real_std": float(real_df[col].std()),
                    "synthetic_std": float(synthetic_df[col].std()),
                    "distribution_similarity": self._calculate_kl_divergence(
                        real_df[col].values,
                        synthetic_df[col].values
                    )
                }
        
        return comparison
    
    @staticmethod
    def _calculate_kl_divergence(p: np.ndarray, q: np.ndarray, bins: int = 50) -> float:
        """Calculate KL divergence between two distributions"""
        try:
            # Create histograms
            range_min = min(p.min(), q.min())
            range_max = max(p.max(), q.max())
            
            p_hist, _ = np.histogram(p, bins=bins, range=(range_min, range_max), density=True)
            q_hist, _ = np.histogram(q, bins=bins, range=(range_min, range_max), density=True)
            
            # Add small epsilon to avoid log(0)
            epsilon = 1e-10
            p_hist = p_hist + epsilon
            q_hist = q_hist + epsilon
            
            # Normalize
            p_hist = p_hist / p_hist.sum()
            q_hist = q_hist / q_hist.sum()
            
            # Calculate KL divergence
            kl_div = np.sum(p_hist * np.log(p_hist / q_hist))
            
            return float(kl_div)
        except:
            return -1.0  # Error calculating


# ── Example usage ──

if __name__ == "__main__":
    # Example: Validate and load real sensor data
    
    ingestor = RealDataIngestor()
    
    # Validate CSV
    validation = ingestor.validate_csv("sample_sensor_data.csv")
    
    print("Validation Result:", validation["is_valid"])
    print("Errors:", validation["errors"])
    print("Warnings:", validation["warnings"])
    
    if validation["is_valid"]:
        # Load data
        df = ingestor.load_real_sensor_data(
            "sample_sensor_data.csv",
            clean=True,
            resample_freq="1H"  # Resample to hourly
        )
        
        print(f"\nLoaded {len(df)} rows")
        print(df.head())
        
        # Generate quality report
        report = ingestor.generate_data_quality_report("sample_sensor_data.csv")
        print("\n" + report)

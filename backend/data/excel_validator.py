# data/excel_validator.py — Excel file validator for Live Excel Sync Engine
#
# Required by excel_sync.py:
#   self._validator = ExcelValidator()
#   result = self._validator.validate_excel(path)   → {"is_valid", "df", "errors", "warnings", "stats"}
#   ExcelValidator.create_sample_template(path)     → writes energy_live.xlsx template

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Required / optional columns ───────────────────────────────────────────────
REQUIRED_COLUMNS = ["timestamp", "consumption_kwh"]
OPTIONAL_COLUMNS = [
    "voltage", "load_factor", "temperature",
    "humidity", "pressure", "flow_rate",
    "current", "power_factor", "equipment_id",
]


class ExcelValidator:
    """
    Validates energy_live.xlsx files before they are fed into the ML pipeline.

    Public API (used by ExcelSyncEngine):
        validate_excel(path)          → dict
        create_sample_template(path)  → None  (classmethod)
    """

    # ── validate_excel ────────────────────────────────────────────────────────

    def validate_excel(self, filepath: Path | str) -> Dict[str, Any]:
        """
        Load and validate an Excel file.

        Returns
        -------
        {
            "is_valid":  bool,
            "df":        pd.DataFrame | None,
            "errors":    List[str],
            "warnings":  List[str],
            "stats":     dict,
        }
        """
        filepath = Path(filepath)
        errors:   List[str] = []
        warnings: List[str] = []
        stats:    Dict[str, Any] = {}

        # ── 1. File existence & size ──────────────────────────────────────────
        if not filepath.exists():
            return self._fail([f"File not found: {filepath}"])

        try:
            size_bytes = filepath.stat().st_size
        except OSError as exc:
            return self._fail([f"Cannot stat file: {exc}"])

        if size_bytes == 0:
            return self._fail(["Excel file is empty (0 bytes)"])

        stats["file_size_kb"] = round(size_bytes / 1024, 1)

        # ── 2. Read workbook ─────────────────────────────────────────────────
        try:
            df = pd.read_excel(filepath, engine="openpyxl")
        except Exception as exc:
            return self._fail([f"Cannot open Excel file: {exc}"])

        if df.empty:
            return self._fail(["Excel file contains no data rows"])

        stats["total_rows"]    = len(df)
        stats["total_columns"] = len(df.columns)

        # ── 3. Required columns ───────────────────────────────────────────────
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            return self._fail([f"Missing required columns: {missing}"])

        # ── 4. Timestamp validation ───────────────────────────────────────────
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            bad_ts = df["timestamp"].isna().sum()
            if bad_ts > 0:
                errors.append(f"{bad_ts} rows have unparseable timestamps — they will be dropped")
            df = df.dropna(subset=["timestamp"])

            if df.empty:
                return self._fail(["All timestamps are invalid — no usable rows remain"])

            df = df.sort_values("timestamp").reset_index(drop=True)
            stats["date_range"] = {
                "start":         str(df["timestamp"].min()),
                "end":           str(df["timestamp"].max()),
                "duration_days": (df["timestamp"].max() - df["timestamp"].min()).days,
            }

            # Gap detection
            diffs  = df["timestamp"].diff().dropna()
            median = diffs.median()
            gaps   = diffs[diffs > median * 2]
            if len(gaps) > 0:
                warnings.append(f"Found {len(gaps)} time gaps larger than 2× median interval")
            stats["median_interval"]    = str(median)
            stats["sampling_frequency"] = self._infer_frequency(median)

        except Exception as exc:
            errors.append(f"Timestamp processing error: {exc}")

        # ── 5. Numeric column checks ──────────────────────────────────────────
        for col in REQUIRED_COLUMNS:
            if col == "timestamp":
                continue
            if col not in df.columns:
                continue

            missing_pct = df[col].isna().mean() * 100
            if missing_pct > 20:
                errors.append(
                    f"Column '{col}' has {missing_pct:.1f}% missing values (threshold: 20%)"
                )
            elif missing_pct > 0:
                warnings.append(f"Column '{col}' has {missing_pct:.1f}% missing values")

            # Negative value check
            if col in ("consumption_kwh", "voltage"):
                neg = (df[col].dropna() < 0).sum()
                if neg > 0:
                    errors.append(f"Column '{col}' has {neg} negative values (invalid)")

            # Constant-value check
            if df[col].nunique(dropna=True) <= 1:
                warnings.append(f"Column '{col}' has no variation (constant value)")

            # Per-column stats
            if pd.api.types.is_numeric_dtype(df[col]):
                stats[f"{col}_stats"] = {
                    "min":         float(df[col].min()),
                    "max":         float(df[col].max()),
                    "mean":        round(float(df[col].mean()), 3),
                    "std":         round(float(df[col].std()), 3),
                    "missing_pct": round(missing_pct, 2),
                }

        # ── 6. Outlier summary (Z-score > 3) ──────────────────────────────────
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_summary: Dict[str, Any] = {}
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) < 10:
                continue
            z = np.abs((col_data - col_data.mean()) / (col_data.std() + 1e-8))
            n_out = int((z > 3).sum())
            if n_out > 0:
                outlier_summary[col] = {
                    "count":      n_out,
                    "percentage": round(n_out / len(df) * 100, 2),
                }
        if outlier_summary:
            stats["outliers"] = outlier_summary
            warnings.append(f"Outliers detected in {len(outlier_summary)} column(s)")

        # ── 7. Duplicate rows ─────────────────────────────────────────────────
        dupes = df.duplicated(subset=["timestamp"]).sum()
        if dupes > 0:
            warnings.append(f"{dupes} duplicate timestamps found (will be deduplicated)")
            stats["duplicates"] = int(dupes)

        # ── 8. Minimum data volume ────────────────────────────────────────────
        if len(df) < 24:
            errors.append(
                f"Only {len(df)} rows — need at least 24 hours of data for ML training"
            )

        is_valid = len(errors) == 0
        logger.info(
            f"[ExcelValidator] {'PASS' if is_valid else 'FAIL'} — "
            f"{len(df)} rows, {len(errors)} errors, {len(warnings)} warnings"
        )

        return {
            "is_valid": is_valid,
            "df":       df if is_valid else None,
            "errors":   errors,
            "warnings": warnings,
            "stats":    stats,
        }

    # ── create_sample_template ────────────────────────────────────────────────

    @classmethod
    def create_sample_template(cls, output_path: Path | str) -> None:
        """
        Write a minimal energy_live.xlsx template so users know the expected
        column layout. Called by ExcelSyncEngine when the watch file is missing.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        n = 168  # one week of hourly data
        timestamps = pd.date_range(
            start=datetime.now().replace(minute=0, second=0, microsecond=0),
            periods=n,
            freq="h",
        )
        np.random.seed(0)
        hour       = timestamps.hour
        daily      = 50 * np.sin(2 * np.pi * (hour - 6) / 24)
        base       = 200 + daily + np.random.normal(0, 10, n)

        df = pd.DataFrame({
            "timestamp":       timestamps,
            "consumption_kwh": np.clip(base, 0, None).round(2),
            "voltage":         np.random.normal(230, 3, n).round(1),
            "load_factor":     np.random.uniform(0.65, 0.92, n).round(3),
            "temperature":     (20 + daily / 10 + np.random.normal(0, 2, n)).round(1),
            "humidity":        np.random.uniform(40, 80, n).round(1),
        })

        try:
            df.to_excel(output_path, index=False, engine="openpyxl")
            logger.info(f"[ExcelValidator] Sample template created at {output_path}")
        except Exception as exc:
            logger.warning(f"[ExcelValidator] Could not write template: {exc}")

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fail(errors: List[str]) -> Dict[str, Any]:
        return {"is_valid": False, "df": None,
                "errors": errors, "warnings": [], "stats": {}}

    @staticmethod
    def _infer_frequency(median_interval: pd.Timedelta) -> str:
        seconds = median_interval.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s (sub-minute)"
        elif seconds < 3600:
            return f"{int(seconds / 60)}min"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h (hourly)"
        else:
            return f"{int(seconds / 86400)}d (daily)"


# ── Quick self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile, os
    tmp = Path(tempfile.mkdtemp()) / "energy_live.xlsx"
    ExcelValidator.create_sample_template(tmp)
    result = ExcelValidator().validate_excel(tmp)
    print(f"is_valid : {result['is_valid']}")
    print(f"rows     : {len(result['df'])}")
    print(f"warnings : {result['warnings']}")
    os.unlink(tmp)
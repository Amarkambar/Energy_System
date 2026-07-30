"""
excel_sync.py — Live Excel Synchronisation Engine

Monitors backend/data/real/energy_live.xlsx using Python Watchdog.
When the file changes, automatically runs the full ML pipeline and updates
the dashboard cache — no manual upload required.

Architecture:
    ExcelSyncEngine
    ├── start()               — launches Watchdog Observer thread
    ├── stop()                — graceful shutdown
    ├── get_status()          — returns SyncState dict (for FastAPI /api/sync/status)
    ├── trigger_manual()      — force a re-process (for FastAPI /api/sync/trigger)
    └── _ExcelFileHandler     — internal Watchdog event handler
           └── on_modified()  → debounce → _process_excel()
                                   ├── _load_and_validate()
                                   ├── _run_pipeline_steps()
                                   └── _update_api_cache()

Debounce logic:
    Excel saves can fire multiple filesystem events in quick succession
    (temp-file creation, rename, final write).  A 2-second threading.Timer
    absorbs burst events so the pipeline runs only once per logical save.

Logging:
    Root logger + rotating file handler at backend/data/sync.log (5 MB × 3 backups).
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import traceback

from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

# Add backend root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Project imports
from data.excel_validator import ExcelValidator
# ── Watchdog ──────────────────────────────────────────────────────────────────
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None                    # type: ignore
    FileSystemEventHandler = object    # type: ignore

# ── Project-local imports ─────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from data.excel_validator import ExcelValidator

# ── Constants ─────────────────────────────────────────────────────────────────
WATCH_FILENAME   = "energy_live.xlsx"
WATCH_DIR        = Path(__file__).parent / "real"
WATCH_FILE       = WATCH_DIR / WATCH_FILENAME
DEBOUNCE_SECONDS = 2.0          # wait this long after last event before processing
LOG_PATH         = Path(__file__).parent / "sync.log"
LOG_MAX_BYTES    = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT = 3

# ── Logging setup ─────────────────────────────────────────────────────────────

def _configure_sync_logger() -> logging.Logger:
    log = logging.getLogger("excel_sync")
    log.setLevel(logging.DEBUG)
    if log.handlers:
        return log  # already configured

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(ch)

    # Rotating file handler
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            LOG_PATH, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception as exc:
        log.warning(f"[Sync] Could not create file log handler: {exc}")

    return log


sync_logger = _configure_sync_logger()

# ── SyncState dataclass ───────────────────────────────────────────────────────

@dataclass
class SyncState:
    """Thread-safe snapshot of the sync engine's current state."""
    file_status:          str = "initialising"   # initialising | watching | processing | ok | error | missing
    pipeline_status:      str = "idle"            # idle | running | completed | failed
    last_update:          Optional[str] = None    # ISO-8601 string or None
    last_attempt:         Optional[str] = None
    rows_processed:       int = 0
    columns_processed:    int = 0
    processing_duration_s: float = 0.0
    error_message:        str = ""
    error_code:           str = ""               # MISSING_FILE | CORRUPTED_FILE | INVALID_COLUMNS | PIPELINE_FAILURE | OK
    warnings:             List[str] = field(default_factory=list)
    validation_stats:     Dict[str, Any] = field(default_factory=dict)
    watch_path:           str = str(WATCH_FILE)
    watchdog_active:      bool = False
    total_sync_count:     int = 0                # successful syncs since startup

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Internal Watchdog handler ─────────────────────────────────────────────────

class _ExcelFileHandler(FileSystemEventHandler):
    """
    Watches a directory and triggers the sync engine whenever
    the target Excel file is modified or created.
    """

    def __init__(self, engine: "ExcelSyncEngine") -> None:
        super().__init__()
        self._engine = engine
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    # Watchdog calls this for every filesystem event in the watched directory
    def on_modified(self, event):
        self._handle_event(event)

    def on_created(self, event):
        self._handle_event(event)

    def _handle_event(self, event) -> None:
        if event.is_directory:
            return
        src = Path(getattr(event, "src_path", ""))
        if src.name != WATCH_FILENAME:
            return

        sync_logger.debug(f"[Handler] Filesystem event on {src.name} — scheduling debounce")
        self._schedule_debounce()

    def _schedule_debounce(self) -> None:
        """Cancel any pending timer and restart a fresh one."""
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                DEBOUNCE_SECONDS,
                self._engine._process_excel,
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()
            sync_logger.debug(f"[Handler] Debounce timer reset ({DEBOUNCE_SECONDS}s)")


# ── Main sync engine ──────────────────────────────────────────────────────────

class ExcelSyncEngine:
    """
    Production-ready live Excel synchronisation engine.

    Usage (called from api.py startup):
        engine = ExcelSyncEngine(pipeline_cache=_pipeline_cache,
                                  save_cache_fn=_save_pipeline_to_disk)
        engine.start()

    Thread safety:
        State mutations are protected by self._state_lock.
        The API cache dict is updated atomically via dict.update().
    """

    def __init__(
        self,
        pipeline_cache: Dict,
        save_cache_fn,
    ) -> None:
        """
        Args:
            pipeline_cache:  The shared _pipeline_cache dict from api.py
            save_cache_fn:   The _save_pipeline_to_disk() function from api.py
        """
        self._pipeline_cache = pipeline_cache
        self._save_cache_fn  = save_cache_fn
        self._state          = SyncState()
        self._state_lock     = threading.Lock()
        self._observer: Optional[Observer] = None
        self._handler: Optional[_ExcelFileHandler] = None
        self._processing_lock = threading.Lock()   # prevent concurrent pipeline runs
        self._validator = ExcelValidator()

        # Ensure watch directory and sample template exist
        WATCH_DIR.mkdir(parents=True, exist_ok=True)
        if not WATCH_FILE.exists():
            sync_logger.info("[Sync] energy_live.xlsx not found — creating sample template")
            try:
                ExcelValidator.create_sample_template(WATCH_FILE)
            except Exception as exc:
                sync_logger.warning(f"[Sync] Could not create template: {exc}")

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch the Watchdog observer. Safe to call multiple times."""
        if not WATCHDOG_AVAILABLE:
            sync_logger.error(
                "[Sync] watchdog package not installed. "
                "Run: pip install watchdog>=4.0.0"
            )
            self._set_state(
                file_status="error",
                error_message="watchdog package not installed",
                error_code="MISSING_DEPENDENCY",
            )
            return

        if self._observer and self._observer.is_alive():
            sync_logger.warning("[Sync] Observer already running — ignoring start()")
            return

        sync_logger.info(f"[Sync] Starting file watcher on: {WATCH_DIR}")
        self._handler  = _ExcelFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(WATCH_DIR), recursive=False)
        self._observer.daemon = True
        self._observer.start()

        self._set_state(
            file_status="watching" if WATCH_FILE.exists() else "missing",
            pipeline_status="idle",
            watchdog_active=True,
        )
        sync_logger.info(
            f"[Sync] ✅ Watchdog active — monitoring {WATCH_FILE}"
        )

        # Run once on startup if file already exists (load last known state)
        if WATCH_FILE.exists():
            t = threading.Thread(target=self._process_excel, daemon=True, name="sync-startup")
            t.start()

    def stop(self) -> None:
        """Graceful shutdown of the Watchdog observer."""
        if self._observer:
            sync_logger.info("[Sync] Stopping file watcher…")
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._set_state(file_status="stopped", watchdog_active=False)
        sync_logger.info("[Sync] File watcher stopped")

    def get_status(self) -> Dict[str, Any]:
        """Return a serialisable snapshot of the current state (for FastAPI)."""
        with self._state_lock:
            return self._state.to_dict()

    def trigger_manual(self) -> Dict[str, str]:
        """
        Manually force a re-process of the current Excel file.
        Returns immediately; processing happens in a background thread.
        """
        if not WATCH_FILE.exists():
            return {"status": "error", "message": f"{WATCH_FILE} does not exist"}

        if self._state.pipeline_status == "running":
            return {"status": "busy", "message": "Pipeline is already running — please wait"}

        sync_logger.info("[Sync] Manual trigger received")
        t = threading.Thread(target=self._process_excel, daemon=True, name="sync-manual")
        t.start()
        return {"status": "started", "message": "Processing started in background"}

    # ── Core processing ───────────────────────────────────────────────────────

    def _process_excel(self) -> None:
        """
        Full processing cycle triggered by a file-change event:
          1. Load & validate Excel
          2. Clean data
          3. Feature engineering
          4. Train ML models
          5. Generate predictions + forecast
          6. Run alert engine
          7. Generate recommendations
          8. Update API cache
        """
        # Prevent concurrent runs (e.g. manual trigger + watchdog event)
        if not self._processing_lock.acquire(blocking=False):
            sync_logger.warning("[Sync] Processing already in progress — skipping")
            return

        attempt_time = datetime.now().isoformat(timespec="seconds")
        self._set_state(
            pipeline_status="running",
            file_status="processing",
            last_attempt=attempt_time,
            error_message="",
            error_code="",
        )
        sync_logger.info("=" * 60)
        sync_logger.info(f"[Sync] ▶ Processing started — {attempt_time}")
        t_start = time.monotonic()

        try:
            # ── Step 1: Load & validate ───────────────────────────────────────
            sync_logger.info(f"[Sync] Step 1/7 — Loading {WATCH_FILE.name}")
            df, validation = self._load_and_validate()

            # ── Step 2: Clean ─────────────────────────────────────────────────
            sync_logger.info("[Sync] Step 2/7 — Cleaning data")
            from data.pipeline import clean_data
            rows_before = len(df)
            df = clean_data(df)
            sync_logger.info(f"[Sync]   {rows_before} → {len(df)} rows after cleaning")

            # ── Step 3: Feature engineering ───────────────────────────────────
            sync_logger.info("[Sync] Step 3/7 — Feature engineering")
            from data.pipeline import build_feature_matrix, save_to_parquet
            df = build_feature_matrix(df)
            sync_logger.info(f"[Sync]   Feature matrix: {df.shape[0]} rows × {df.shape[1]} columns")

            # Persist processed data in the standard parquet format
            save_to_parquet(df)

            # ── Step 4: Train models ──────────────────────────────────────────
            sync_logger.info("[Sync] Step 4/7 — Training ML models")
            from models.ml_models import train_all_models
            models = train_all_models(df)
            sync_logger.info("[Sync]   Models trained: anomaly, forecaster, maintenance, efficiency")

            # ── Step 5: Predictions + forecast ────────────────────────────────
            sync_logger.info("[Sync] Step 5/7 — Generating predictions & forecast")
            from models.ml_models import run_all_predictions
            predictions, forecast = run_all_predictions(df, models)
            sync_logger.info(
                f"[Sync]   Predictions: {len(predictions)} rows | "
                f"Forecast: {len(forecast)} steps"
            )

            # ── Step 6: Alert engine ──────────────────────────────────────────
            sync_logger.info("[Sync] Step 6/7 — Running alert engine")
            from alerts.alerts_engine import AlertEngine
            alert_engine = AlertEngine()
            alerts_df    = alert_engine.check_dataframe(predictions.tail(500))
            alert_summary = alert_engine.get_alert_summary()
            sync_logger.info(f"[Sync]   Alerts: {len(alerts_df)} triggered")

            # ── Step 7: Recommendations ───────────────────────────────────────
            sync_logger.info("[Sync] Step 7/7 — Generating recommendations")
            from alerts.alerts_engine import RecommendationEngine
            rec_engine = RecommendationEngine()
            recs        = rec_engine.generate(df, predictions)
            sync_logger.info(f"[Sync]   Recommendations: {len(recs)} generated")

            # ── Update cache ──────────────────────────────────────────────────
            duration = time.monotonic() - t_start
            self._update_api_cache(
                df=df,
                predictions=predictions,
                forecast=forecast,
                models=models,
                alerts_df=alerts_df,
                alert_summary=alert_summary,
                recs=recs,
            )

            self._set_state(
                file_status="ok",
                pipeline_status="completed",
                last_update=datetime.now().isoformat(timespec="seconds"),
                rows_processed=len(df),
                columns_processed=len(df.columns),
                processing_duration_s=round(duration, 2),
                error_message="",
                error_code="OK",
                warnings=validation.get("warnings", []),
                validation_stats=validation.get("stats", {}),
                total_sync_count=self._state.total_sync_count + 1,
            )

            sync_logger.info(
                f"[Sync] ✅ Completed in {duration:.1f}s | "
                f"{len(df)} rows | sync #{self._state.total_sync_count}"
            )

        except _ValidationError as exc:
            duration = time.monotonic() - t_start
            sync_logger.error(f"[Sync] ❌ Validation failed: {exc}")
            self._set_state(
                file_status="error",
                pipeline_status="failed",
                error_message=str(exc),
                error_code=exc.code,
                processing_duration_s=round(duration, 2),
            )

        except Exception as exc:
            duration = time.monotonic() - t_start
            tb = traceback.format_exc()
            sync_logger.error(f"[Sync] ❌ Pipeline failure: {exc}\n{tb}")
            self._set_state(
                file_status="error",
                pipeline_status="failed",
                error_message=f"Pipeline failure: {exc}",
                error_code="PIPELINE_FAILURE",
                processing_duration_s=round(duration, 2),
            )

        finally:
            self._processing_lock.release()
            sync_logger.info("[Sync] ◀ Processing cycle ended")
            sync_logger.info("=" * 60)

    def _load_and_validate(self):
        """
        Load energy_live.xlsx and run the Excel validator.
        Raises _ValidationError on any problem so the main try/except
        can categorise errors cleanly.
        """
        if not WATCH_FILE.exists():
            raise _ValidationError(
                f"Excel file not found: {WATCH_FILE}",
                code="MISSING_FILE",
            )

        # File size sanity check (reject 0-byte / locked files)
        try:
            size = WATCH_FILE.stat().st_size
        except OSError as exc:
            raise _ValidationError(f"Cannot stat file: {exc}", code="CORRUPTED_FILE")

        if size == 0:
            raise _ValidationError("Excel file is empty (0 bytes)", code="CORRUPTED_FILE")

        # A brief wait to let Excel finish writing before we read
        time.sleep(0.3)

        result = self._validator.validate_excel(WATCH_FILE)

        if not result["is_valid"]:
            errors = result["errors"]
            # Classify error type
            if any("not found" in e.lower() for e in errors):
                code = "MISSING_FILE"
            elif any("cannot open" in e.lower() or "corrupt" in e.lower() for e in errors):
                code = "CORRUPTED_FILE"
            elif any("missing required column" in e.lower() for e in errors):
                code = "INVALID_COLUMNS"
            else:
                code = "CORRUPTED_FILE"
            raise _ValidationError("; ".join(errors), code=code)

        df = result["df"]
        if df is None or df.empty:
            raise _ValidationError("Validator returned empty DataFrame", code="CORRUPTED_FILE")

        sync_logger.info(
            f"[Sync]   Validation PASS — {len(df)} rows, "
            f"{len(result['warnings'])} warnings"
        )
        return df, result

    def _update_api_cache(
        self, *, df, predictions, forecast, models, alerts_df, alert_summary, recs
    ) -> None:
        """Atomically update the shared pipeline cache used by FastAPI endpoints."""
        import pandas as pd
        new_cache = {
            "ready":         True,
            "df":            df,
            "predictions":   predictions,
            "forecast":      forecast,
            "models":        models,
            "alerts_df":     alerts_df,
            "alert_summary": alert_summary,
            "recs":          recs,
        }
        self._pipeline_cache.update(new_cache)
        try:
            self._save_cache_fn(new_cache)
            sync_logger.info("[Sync] Cache saved to disk")
        except Exception as exc:
            sync_logger.warning(f"[Sync] Could not save cache to disk: {exc}")

    # ── State helpers ─────────────────────────────────────────────────────────

    def _set_state(self, **kwargs) -> None:
        """Thread-safe state update."""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)

    # ── Log reader (for /api/sync/logs) ──────────────────────────────────────

    @staticmethod
    def read_log_tail(n_lines: int = 100) -> List[str]:
        """Return the last `n_lines` from sync.log (newest last)."""
        if not LOG_PATH.exists():
            return ["[Sync] Log file not yet created"]
        try:
            with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return [l.rstrip() for l in lines[-n_lines:]]
        except Exception as exc:
            return [f"[Sync] Error reading log: {exc}"]


# ── Internal exception ────────────────────────────────────────────────────────

class _ValidationError(Exception):
    """Raised when Excel content fails validation, carries an error code."""

    def __init__(self, message: str, code: str = "UNKNOWN") -> None:
        super().__init__(message)
        self.code = code

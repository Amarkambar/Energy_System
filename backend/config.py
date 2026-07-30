# config.py — Central configuration for Energy Diagnostics project

import os
from dotenv import load_dotenv

# Load .env with explicit path (works regardless of CWD)
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_CONFIG_DIR, ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH, override=True)
else:
    load_dotenv()  # fallback: search CWD and parent directories

# ── Database ──────────────────────────────────────────────
DB_URL = os.getenv("DB_URL", "sqlite:///energy_diagnostics.db")
# FIX: Use absolute path so the file is always saved inside backend/data/,
# regardless of which directory the server is launched from.
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PARQUET_PATH = os.path.join(_CONFIG_DIR, "data", "energy_data.parquet")

# ── Kafka / MQTT ──────────────────────────────────────────
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC  = os.getenv("KAFKA_TOPIC",  "energy_stream")
MQTT_BROKER  = os.getenv("MQTT_BROKER",  "localhost:1883")
MQTT_TOPIC   = os.getenv("MQTT_TOPIC",   "sensors/energy")

# ── Weather API ───────────────────────────────────────────
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "your_openweather_key")
WEATHER_CITY    = os.getenv("WEATHER_CITY",    "Mumbai")

# ── Alert thresholds ──────────────────────────────────────
ALERT_CONSUMPTION_THRESHOLD = 500   # kWh — spike alert
ALERT_ANOMALY_SCORE_THRESHOLD = 0.7 # ML anomaly confidence
ALERT_EMAIL_RECIPIENTS = ["admin@example.com"]

# ── SMTP (for email alerts) ───────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "your@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_password")

# ── Model paths ───────────────────────────────────────────
# FIX: Use absolute paths so model save/load works regardless of CWD.
MODEL_DIR           = os.path.join(_CONFIG_DIR, "models", "saved")
ANOMALY_MODEL_PATH  = os.path.join(MODEL_DIR, "anomaly_model.pkl")
FORECAST_MODEL_PATH = os.path.join(MODEL_DIR, "forecast_model.pkl")
MAINT_MODEL_PATH    = os.path.join(MODEL_DIR, "maintenance_model.pkl")
CLUSTER_MODEL_PATH  = os.path.join(MODEL_DIR, "cluster_model.pkl")
ENSEMBLE_MODEL_PATH = os.path.join(MODEL_DIR, "ensemble_model.pkl")

# ── Feature engineering settings ─────────────────────────
LAG_FEATURES     = [1, 2, 3, 6, 12, 24]   # hours
ROLLING_WINDOWS  = [6, 12, 24, 48]         # hours
FORECAST_HORIZON = 24                       # hours ahead

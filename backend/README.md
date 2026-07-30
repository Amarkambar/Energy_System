# ⚡ Energy Diagnostics — AI-Powered Data Science Project

A complete, production-grade energy diagnostics system using AI/ML for
anomaly detection, demand forecasting, predictive maintenance, real-time alerts,
and an interactive Streamlit dashboard.

---

## 📁 Project Structure

```
energy_diagnostics/
├── main.py                    # Entry point (run everything)
├── config.py                  # All settings & thresholds
├── requirements.txt           # Dependencies
│
├── data/
│   └── pipeline.py            # Ingestion → Cleaning → Feature Engineering → Storage
│
├── models/
│   ├── ml_models.py           # Anomaly, Forecasting, Maintenance, Efficiency models
│   └── saved/                 # Trained model files (.pkl)
│
├── alerts/
│   └── alerts_engine.py       # Alert rules + Email notifications + Recommendations
│
├── dashboard/
│   └── app.py                 # Streamlit live dashboard
│
└── notebooks/                 # Jupyter notebooks for EDA
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure settings

Copy `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

**Important**: Configure SMTP for email notifications (password reset, alerts)

```env
# See SMTP_SETUP.md for detailed configuration guide
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_gmail_app_password  # See SMTP_SETUP.md

WEATHER_API_KEY=your_openweather_api_key  # Optional
DB_URL=sqlite:///energy_diagnostics.db
```

**Test your email configuration**:

```bash
python test_email.py
```

### 3. Run full pipeline

```bash
python main.py --mode full
```

### 4. Launch dashboard only

```bash
python main.py --mode dashboard
# OR directly:
streamlit run dashboard/app.py
```

### 5. Run individual components

```bash
python main.py --mode pipeline    # Data pipeline only
python main.py --mode models      # Train ML models only
python main.py --mode alerts      # Alerts + recommendations only
```

---

## 🧠 AI/ML Models

| Model                  | Algorithm                  | Purpose                             |
| ---------------------- | -------------------------- | ----------------------------------- |
| Anomaly Detection      | Isolation Forest + SHAP    | Detect unusual consumption patterns |
| Demand Forecasting     | XGBoost / GradientBoosting | Predict next 24h energy demand      |
| Predictive Maintenance | Random Forest Classifier   | Classify equipment health           |
| Efficiency Scoring     | K-Means Clustering         | Score operational efficiency        |

---

## 📊 Features

- **Data Pipeline**: Smart meter + IoT + Weather data ingestion, cleaning, normalization
- **Feature Engineering**: Lag features, rolling statistics, FFT frequency components, time encodings
- **Real-time Monitoring**: Rule-based + ML-triggered alerts with email notifications
- **AI Recommendations**: 7 categories of auto-generated energy-saving suggestions
- **Explainable AI**: SHAP values show _why_ the model flagged an anomaly
- **Live Dashboard**: Streamlit app with KPIs, charts, forecasts, alerts, and download

---

## 📦 Datasets (Free & Public)

| Dataset                        | Link                                                                                    |
| ------------------------------ | --------------------------------------------------------------------------------------- |
| UCI Energy Efficiency          | https://archive.ics.uci.edu/ml/datasets/energy+efficiency                               |
| ASHRAE Energy Predictor        | https://www.kaggle.com/c/ashrae-energy-prediction                                       |
| Open Power System Data         | https://open-power-system-data.org/                                                     |
| UCI Individual Household Power | https://archive.ics.uci.edu/ml/datasets/individual+household+electric+power+consumption |

> If no dataset is provided, the system auto-generates 1 year of synthetic hourly data for demo.

---

## 🔧 Tech Stack

| Layer          | Tools                                   |
| -------------- | --------------------------------------- |
| Data           | Pandas, NumPy, PyArrow, SciPy           |
| ML             | Scikit-learn, XGBoost, PyTorch, Prophet |
| Explainability | SHAP                                    |
| Streaming      | Kafka-Python, Paho-MQTT                 |
| Dashboard      | Streamlit, Plotly                       |
| Storage        | SQLite / TimescaleDB, Parquet           |
| API            | FastAPI, Uvicorn                        |
| Deployment     | Docker                                  |

---

## 🌟 What Makes This Project Different

1. **Explainable AI** — SHAP values for every anomaly prediction
2. **Multi-model ensemble** — 4 specialized models working together
3. **AI-generated recommendations** — Goes beyond detection to actionable insights
4. **Full data pipeline** — From raw sensor data to production-ready features
5. **Real-time monitoring** — ML-triggered alerts, not just static thresholds
6. **Synthetic data generator** — Works out-of-the-box without any dataset

---

Built with ❤️ | Energy Diagnostics Data Science Project

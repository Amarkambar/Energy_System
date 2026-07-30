# Energy_System

An AI-powered industrial energy monitoring and diagnostics platform built with **FastAPI** (Python) and **React** (TypeScript).

## Features

- ⚡ **Real-time energy monitoring** — consumption, voltage, load factor
- 🔍 **Anomaly Detection** — Isolation Forest + SHAP explainability
- 📈 **Demand Forecasting** — XGBoost with lag, rolling, and FFT features (24h horizon)
- 🔧 **Predictive Maintenance** — Random Forest 3-class health classifier
- 🎯 **Efficiency Scoring** — K-Means clustering with silhouette analysis
- 🚨 **Smart Alerts** — Rule-based engine with AI recommendations
- 📊 **Classification Metrics** — Confusion matrix, ROC curves, Precision-Recall, Feature Importance
- 🔄 **Live Excel Sync** — Watchdog-based real-time CSV/Excel ingestion
- 🔐 **Auth** — JWT + bcrypt, forgot/reset password with email tokens

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, Uvicorn |
| ML | XGBoost, Scikit-learn, SHAP, Isolation Forest |
| Database | MongoDB |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Charts | Recharts |
| Auth | JWT (HMAC-SHA256), passlib[bcrypt] |
| Deployment | Docker Compose |

## Quick Start

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in your values
uvicorn api:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Docker (full stack)
```bash
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Environment Variables

Copy `backend/.env.example` and fill in:

```env
MONGO_URI=mongodb://localhost:27017
JWT_SECRET=your-strong-secret-here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
WEATHER_API_KEY=           # optional — OpenWeatherMap key
FRONTEND_URL=http://localhost:5173
```

> ⚠️ **Never commit your real `.env` file.** It is excluded via `.gitignore`.

## Project Structure

```
project1/
├── backend/
│   ├── api.py              # FastAPI routes, auth, pipeline, metrics
│   ├── config.py           # Central configuration
│   ├── data/
│   │   ├── pipeline.py     # Ingestion → features → preprocessing
│   │   └── excel_sync.py   # Live file watcher
│   ├── models/
│   │   └── ml_models.py    # Anomaly, Forecast, Maintenance, Efficiency
│   ├── alerts/
│   │   └── alerts_engine.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/          # Login, Register, Reset, Dashboard
│       ├── components/dashboard/
│       ├── hooks/use-ml-data.ts
│       └── lib/api.ts
├── docker-compose.yml
└── README.md
```

## ML Model Accuracy (sample run — 289 rows)

| Model | Metric | Value |
|---|---|---|
| Energy Forecaster | Accuracy (100−MAPE) | 75.5% |
| Maintenance Predictor | Cross-Val Accuracy (5-fold) | 77.4% |
| Anomaly Detector | Normal reading rate | 94.8% |
| Efficiency Clustering | Silhouette Score | 0.28 (Fair) |

> Accuracy improves significantly with larger datasets (5,000+ rows recommended).

## License

MIT

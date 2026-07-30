# alerts/alerts_engine.py — Real-time alerts + AI-generated recommendations

import smtplib
import json
import time
import os
import schedule
import pandas as pd
import numpy as np
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    ALERT_EMAIL_RECIPIENTS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
)

# ── Dynamic threshold loader ───────────────────────────────
_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "data", "settings.json")

_DEFAULT_THRESHOLDS = {
    "alert_consumption_threshold": 500,
    "alert_anomaly_score_threshold": 0.7,
    "alert_voltage_deviation": 10,
    "alert_load_factor_threshold": 0.9,
}

def _get_thresholds() -> dict:
    """Read thresholds from settings.json; fall back to defaults."""
    try:
        if os.path.exists(_SETTINGS_PATH):
            with open(_SETTINGS_PATH) as f:
                s = json.load(f)
            return {**_DEFAULT_THRESHOLDS, **s}
    except Exception:
        pass
    return dict(_DEFAULT_THRESHOLDS)


# ══════════════════════════════════════════════════════════
#  ALERT DEFINITIONS  (thresholds resolved at runtime)
# ══════════════════════════════════════════════════════════

def _build_alert_rules() -> dict:
    """Build alert rules using current threshold settings."""
    th = _get_thresholds()
    return {
        "high_consumption": {
            "condition": lambda row, t=th: row.get("consumption_kwh", 0) > t["alert_consumption_threshold"],
            "severity":  "warning",
            "message":   "High energy consumption detected: {consumption_kwh:.1f} kWh (threshold: {threshold} kWh)",
            "threshold": th["alert_consumption_threshold"],
        },
        "anomaly_detected": {
            "condition": lambda row: row.get("anomaly_flag", 0) == 1,
            "severity":  "critical",
            "message":   "Anomaly detected — severity: {anomaly_severity}, score: {anomaly_score:.3f}",
            "threshold": None,
        },
        "equipment_critical": {
            "condition": lambda row: row.get("health_status", "healthy") == "critical",
            "severity":  "critical",
            "message":   "Equipment in CRITICAL state — maintenance urgency: {maintenance_urgency:.0f}%",
            "threshold": None,
        },
        "equipment_warning": {
            "condition": lambda row: row.get("health_status", "healthy") == "warning",
            "severity":  "warning",
            "message":   "Equipment WARNING — recommend inspection within 48 hours",
            "threshold": None,
        },
        "voltage_deviation": {
            "condition": lambda row, t=th: abs(row.get("voltage", 230) - 230) > t["alert_voltage_deviation"],
            "severity":  "warning",
            "message":   "Voltage deviation detected: {voltage:.1f}V (nominal: 230V)",
            "threshold": th["alert_voltage_deviation"],
        },
        "peak_hour_high_load": {
            "condition": lambda row, t=th: row.get("is_peak_hour", 0) == 1 and row.get("load_factor", 0) > t["alert_load_factor_threshold"],
            "severity":  "info",
            "message":   "High load factor during peak hours: {load_factor:.2f}. Consider load shifting.",
            "threshold": th["alert_load_factor_threshold"],
        },
        "inefficient_consumption": {
            "condition": lambda row: row.get("efficiency_label", "") == "inefficient",
            "severity":  "info",
            "message":   "System operating in inefficient cluster. Efficiency score: {efficiency_score:.1f}/100",
            "threshold": None,
        },
    }



# ══════════════════════════════════════════════════════════
#  ALERT ENGINE
# ══════════════════════════════════════════════════════════

class AlertEngine:
    def __init__(self):
        self.alert_log = []
        self.alert_cooldowns = {}  # Prevent alert spam
        self.cooldown_seconds = 300  # 5 minutes between same alerts

    def check_row(self, row: dict) -> list:
        """Evaluate all rules against a single data row"""
        triggered = []
        now = datetime.now()
        alert_rules = _build_alert_rules()   # re-read thresholds from settings.json

        for rule_name, rule in alert_rules.items():
            try:
                if rule["condition"](row):
                    # Cooldown check
                    last_fired = self.alert_cooldowns.get(rule_name)
                    if last_fired and (now - last_fired).seconds < self.cooldown_seconds:
                        continue

                    msg = rule["message"].format(
                        threshold=rule.get("threshold", ""),
                        **{k: v for k, v in row.items() if isinstance(v, (int, float, str))}
                    )
                    alert = {
                        "timestamp": now.isoformat(),
                        "rule":      rule_name,
                        "severity":  rule["severity"],
                        "message":   msg,
                        "data":      {k: v for k, v in row.items()
                                      if isinstance(v, (int, float, str))},
                    }
                    triggered.append(alert)
                    self.alert_log.append(alert)
                    self.alert_cooldowns[rule_name] = now

            except Exception as e:
                print(f"[Alert] Rule '{rule_name}' error: {e}")

        return triggered

    def check_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Check all rows in a dataframe, return rows with alerts"""
        all_alerts = []
        for _, row in df.iterrows():
            alerts = self.check_row(row.to_dict())
            for alert in alerts:
                all_alerts.append(alert)

        if all_alerts:
            print(f"[AlertEngine] {len(all_alerts)} alerts triggered")
        return pd.DataFrame(all_alerts) if all_alerts else pd.DataFrame()

    def get_alert_summary(self) -> dict:
        """Summarize alerts by severity"""
        if not self.alert_log:
            return {"total": 0, "critical": 0, "warning": 0, "info": 0}
        df = pd.DataFrame(self.alert_log)
        return {
            "total":    len(df),
            "critical": len(df[df["severity"] == "critical"]),
            "warning":  len(df[df["severity"] == "warning"]),
            "info":     len(df[df["severity"] == "info"]),
        }


# ══════════════════════════════════════════════════════════
#  EMAIL NOTIFICATIONS
# ══════════════════════════════════════════════════════════

class EmailNotifier:
    def __init__(self):
        self.host     = SMTP_HOST
        self.port     = SMTP_PORT
        self.user     = SMTP_USER
        self.password = SMTP_PASSWORD
        # Validate SMTP readiness at construction time
        self._ready = bool(
            self.host and self.host.strip()
            and self.user and self.user.strip()
            and self.user not in ("your@gmail.com",)
            and self.password and self.password.strip()
            and self.password not in ("your_password", "your_app_password_here")
        )
        if not self._ready:
            print("[EmailNotifier] ⚠️  SMTP not configured — emails will be skipped")

    def send_alert_email(self, alerts: list, recipients: list = None):
        if not alerts:
            return
        if not self._ready:
            print(f"[EmailNotifier] Skipping email for {len(alerts)} alerts — SMTP not configured")
            return
        recipients = recipients or ALERT_EMAIL_RECIPIENTS

        critical = [a for a in alerts if a["severity"] == "critical"]
        warnings = [a for a in alerts if a["severity"] == "warning"]
        infos    = [a for a in alerts if a["severity"] == "info"]

        subject = f"[Energy Diagnostics] {len(critical)} Critical | {len(warnings)} Warnings"

        body = f"""
        <html><body style="font-family: Arial, sans-serif;">
        <h2>Energy Diagnostics Alert Report</h2>
        <p><b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr/>
        """

        if critical:
            body += "<h3 style='color:red'>🔴 Critical Alerts</h3><ul>"
            for a in critical:
                body += f"<li><b>{a['rule']}</b> — {a['message']}</li>"
            body += "</ul>"

        if warnings:
            body += "<h3 style='color:orange'>🟠 Warnings</h3><ul>"
            for a in warnings:
                body += f"<li><b>{a['rule']}</b> — {a['message']}</li>"
            body += "</ul>"

        if infos:
            body += "<h3 style='color:blue'>🔵 Info</h3><ul>"
            for a in infos:
                body += f"<li>{a['message']}</li>"
            body += "</ul>"

        body += "</body></html>"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = self.user
        msg["To"]      = ", ".join(recipients)
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, recipients, msg.as_string())
            print(f"[Email] ✅ Alert email sent to {recipients}")
        except Exception as e:
            print(f"[Email] ⚠️  Failed to send: {e}")


# ══════════════════════════════════════════════════════════
#  AI-GENERATED RECOMMENDATIONS ENGINE
# ══════════════════════════════════════════════════════════

class RecommendationEngine:
    """Rule-based + pattern-driven energy-saving recommendations"""

    RECOMMENDATION_TEMPLATES = {
        "load_shifting": {
            "condition": lambda s: s.get("peak_hour_ratio", 0) > 0.6,
            "priority":  "high",
            "rec": "Shift {peak_pct:.0f}% of peak-hour load to off-peak hours (10pm–6am) to reduce demand charges by an estimated {savings:.0f} kWh/month.",
            "category":  "Load Management",
        },
        "anomaly_pattern": {
            "condition": lambda s: s.get("anomaly_rate", 0) > 0.05,
            "priority":  "critical",
            "rec": "Anomaly rate is {anomaly_pct:.1f}% — inspect equipment in zones with repeated spikes. Likely causes: motor inefficiency, HVAC fault, or power quality issues.",
            "category":  "Equipment",
        },
        "voltage_optimization": {
            "condition": lambda s: s.get("voltage_std", 0) > 5,
            "priority":  "medium",
            "rec": "Voltage fluctuation (±{voltage_std:.1f}V) detected. Install automatic voltage regulators (AVR) to reduce stress on appliances and improve power factor.",
            "category":  "Power Quality",
        },
        "efficiency_improvement": {
            "condition": lambda s: s.get("avg_efficiency_score", 100) < 65,
            "priority":  "high",
            "rec": "Average efficiency score is {avg_eff:.0f}/100. Consider upgrading motors and compressors to IE3/IE4 class. Estimated energy savings: 15–25%.",
            "category":  "Equipment Upgrade",
        },
        "maintenance_schedule": {
            "condition": lambda s: s.get("critical_pct", 0) > 0.1,
            "priority":  "critical",
            "rec": "{critical_pct:.0f}% of operating hours show critical equipment signals. Schedule preventive maintenance within 72 hours to avoid unplanned downtime.",
            "category":  "Maintenance",
        },
        "consumption_baseline": {
            "condition": lambda s: s.get("consumption_trend", 0) > 0.05,
            "priority":  "medium",
            "rec": "Consumption trend shows +{trend_pct:.1f}% increase over baseline. Review HVAC setpoints and building insulation. Consider ISO 50001 energy audit.",
            "category":  "Energy Management",
        },
        "renewable_potential": {
            "condition": lambda s: s.get("avg_consumption", 0) > 200,
            "priority":  "info",
            "rec": "Average consumption of {avg_kwh:.0f} kWh/day indicates strong ROI for rooftop solar (≈{solar_kw:.0f} kW system). Estimated payback: 4–6 years.",
            "category":  "Renewable Energy",
        },
    }

    def generate(self, df: pd.DataFrame, predictions: pd.DataFrame = None) -> list:
        """Analyze data patterns and generate prioritized recommendations"""

        # Compute summary statistics
        stats = {
            "peak_hour_ratio":      df.get("is_peak_hour", pd.Series([0])).mean() if "is_peak_hour" in df else 0,
            "peak_pct":             df.get("is_peak_hour", pd.Series([0])).mean() * 100 if "is_peak_hour" in df else 0,
            "anomaly_rate":         predictions["anomaly_flag"].mean() if predictions is not None and "anomaly_flag" in predictions else 0,
            "anomaly_pct":          (predictions["anomaly_flag"].mean() * 100) if predictions is not None and "anomaly_flag" in predictions else 0,
            "voltage_std":          df["voltage"].std() if "voltage" in df else 0,
            "avg_efficiency_score": predictions["efficiency_score"].mean() if predictions is not None and "efficiency_score" in predictions else 80,
            "avg_eff":              predictions["efficiency_score"].mean() if predictions is not None and "efficiency_score" in predictions else 80,
            "critical_pct":         (predictions["health_status"] == "critical").mean() if predictions is not None and "health_status" in predictions else 0,
            "consumption_trend":    self._compute_trend(df["consumption_kwh"]) if "consumption_kwh" in df else 0,
            "trend_pct":            self._compute_trend(df["consumption_kwh"]) * 100 if "consumption_kwh" in df else 0,
            "avg_consumption":      df["consumption_kwh"].mean() if "consumption_kwh" in df else 0,
            "avg_kwh":              df["consumption_kwh"].mean() if "consumption_kwh" in df else 0,
            "solar_kw":             (df["consumption_kwh"].mean() / 4) if "consumption_kwh" in df else 0,
            "savings":              df["consumption_kwh"].sum() * 0.15 if "consumption_kwh" in df else 0,
        }

        recommendations = []
        priority_order = {"critical": 0, "high": 1, "medium": 2, "info": 3}

        for key, template in self.RECOMMENDATION_TEMPLATES.items():
            try:
                if template["condition"](stats):
                    rec_text = template["rec"].format(**stats)
                    recommendations.append({
                        "id":       key,
                        "priority": template["priority"],
                        "category": template["category"],
                        "recommendation": rec_text,
                        "generated_at": datetime.now().isoformat(),
                    })
            except Exception as e:
                pass

        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))
        print(f"[Recommendations] Generated {len(recommendations)} recommendations")
        return recommendations

    def _compute_trend(self, series: pd.Series) -> float:
        """Compute linear trend slope normalized by mean"""
        if len(series) < 10:
            return 0
        x = np.arange(len(series))
        slope = np.polyfit(x, series.fillna(series.mean()), 1)[0]
        return slope / (series.mean() + 1e-8)

    def to_dataframe(self, recommendations: list) -> pd.DataFrame:
        return pd.DataFrame(recommendations)


# ══════════════════════════════════════════════════════════
#  REAL-TIME MONITOR (scheduler loop)
# ══════════════════════════════════════════════════════════

class RealTimeMonitor:
    def __init__(self, models: dict, alert_engine: AlertEngine,
                 email_notifier: EmailNotifier, recommendation_engine: RecommendationEngine):
        self.models               = models
        self.alert_engine         = alert_engine
        self.email_notifier       = email_notifier
        self.recommendation_engine = recommendation_engine
        self.latest_alerts        = []
        self.latest_recommendations = []

    def process_new_data(self, new_df: pd.DataFrame):
        """Process new incoming data through all models and alerts"""
        from models.ml_models import run_all_predictions
        predictions, forecast = run_all_predictions(new_df, self.models)

        # Check alerts
        alerts_df = self.alert_engine.check_dataframe(predictions)
        if not alerts_df.empty:
            self.latest_alerts = alerts_df.to_dict("records")
            critical_alerts = [a for a in self.latest_alerts if a["severity"] == "critical"]
            if critical_alerts:
                self.email_notifier.send_alert_email(self.latest_alerts)

        # Generate recommendations
        self.latest_recommendations = self.recommendation_engine.generate(new_df, predictions)

        return predictions, forecast, self.latest_alerts, self.latest_recommendations

    def start_scheduler(self, data_fn, interval_minutes: int = 15):
        """Run monitoring on a schedule"""
        def job():
            print(f"\n[Monitor] Running at {datetime.now().strftime('%H:%M:%S')}")
            new_data = data_fn()
            self.process_new_data(new_data)

        schedule.every(interval_minutes).minutes.do(job)
        print(f"[Monitor] Scheduler started — running every {interval_minutes} minutes")
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")
    from data.pipeline import run_pipeline
    from models.ml_models import train_all_models, run_all_predictions

    df = run_pipeline()
    models = train_all_models(df)
    predictions, forecast = run_all_predictions(df, models)

    engine = AlertEngine()
    alerts_df = engine.check_dataframe(predictions.tail(100))
    print(f"\nAlert summary: {engine.get_alert_summary()}")

    rec_engine = RecommendationEngine()
    recs = rec_engine.generate(df, predictions)
    for r in recs:
        print(f"[{r['priority'].upper()}] {r['category']}: {r['recommendation'][:80]}...")

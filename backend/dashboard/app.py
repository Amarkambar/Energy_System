# dashboard/app.py — Streamlit Live Energy Diagnostics Dashboard

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Energy Diagnostics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid #7c3aed;
        margin-bottom: 8px;
    }
    .alert-critical { border-left-color: #ef4444 !important; }
    .alert-warning  { border-left-color: #f59e0b !important; }
    .alert-info     { border-left-color: #3b82f6 !important; }
    .rec-high       { border-left-color: #ef4444; }
    .rec-medium     { border-left-color: #f59e0b; }
    .rec-info       { border-left-color: #3b82f6; }
    .stMetric label { font-size: 13px !important; color: #94a3b8 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  DATA + MODEL LOADING (cached)
# ══════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def load_data():
    from data.pipeline import run_pipeline
    return run_pipeline()

@st.cache_resource
def load_models(df):
    from models.ml_models import train_all_models
    return train_all_models(df)

@st.cache_data(ttl=300)
def get_predictions(_df, _models):
    from models.ml_models import run_all_predictions
    return run_all_predictions(_df, _models)


# ══════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/lightning-bolt.png", width=60)
    st.title("⚡ Energy Diagnostics")
    st.caption("AI-powered monitoring system")
    st.divider()

    st.subheader("Filters")
    days_back = st.slider("Show last N days", 1, 30, 7)
    show_anomalies_only = st.checkbox("Show anomalies only", False)
    severity_filter = st.multiselect(
        "Alert severities",
        ["critical", "warning", "info"],
        default=["critical", "warning"]
    )

    st.divider()
    st.subheader("Thresholds")
    consumption_thresh = st.number_input("Consumption alert (kWh)", value=500, step=10)
    anomaly_thresh = st.slider("Anomaly score threshold", 0.0, 1.0, 0.5, 0.05)

    st.divider()
    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")


# ══════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════

with st.spinner("Loading data and training models..."):
    df = load_data()
    models = load_models(df)
    predictions, forecast = get_predictions(df, models)

# Filter to selected time window
cutoff = predictions["timestamp"].max() - timedelta(days=days_back)
view   = predictions[predictions["timestamp"] >= cutoff].copy()
if show_anomalies_only:
    view = view[view["anomaly_flag"] == 1]


# ══════════════════════════════════════════════════════════
#  TOP KPI CARDS
# ══════════════════════════════════════════════════════════

st.title("⚡ Energy Diagnostics Dashboard")
st.caption(f"Monitoring period: last {days_back} days  |  {len(view):,} data points")

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    total_kwh = view["consumption_kwh"].sum()
    st.metric("Total Consumption", f"{total_kwh:,.0f} kWh",
              delta=f"{((total_kwh / len(view)) - 200):.1f} vs baseline")
with k2:
    avg_kwh = view["consumption_kwh"].mean()
    st.metric("Avg Hourly Load", f"{avg_kwh:.1f} kWh",
              delta=f"{view['consumption_kwh'].std():.1f} σ")
with k3:
    n_anomalies = view["anomaly_flag"].sum()
    pct = n_anomalies / len(view) * 100
    st.metric("Anomalies Detected", f"{n_anomalies:,}",
              delta=f"{pct:.1f}% of readings", delta_color="inverse")
with k4:
    critical_pct = (view["health_status"] == "critical").mean() * 100
    st.metric("Critical Equipment %", f"{critical_pct:.1f}%",
              delta_color="inverse")
with k5:
    avg_eff = view["efficiency_score"].mean()
    st.metric("Avg Efficiency Score", f"{avg_eff:.1f}/100",
              delta=f"{avg_eff - 75:.1f} vs target")

st.divider()


# ══════════════════════════════════════════════════════════
#  MAIN CHARTS ROW 1
# ══════════════════════════════════════════════════════════

col_left, col_right = st.columns([3, 1])

with col_left:
    st.subheader("Energy consumption over time")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=view["timestamp"], y=view["consumption_kwh"],
        mode="lines", name="Consumption (kWh)",
        line=dict(color="#7c3aed", width=1.5)
    ))
    # Highlight anomalies
    anomalies = view[view["anomaly_flag"] == 1]
    fig.add_trace(go.Scatter(
        x=anomalies["timestamp"], y=anomalies["consumption_kwh"],
        mode="markers", name="Anomaly",
        marker=dict(color="#ef4444", size=6, symbol="x")
    ))
    # Threshold line
    fig.add_hline(y=consumption_thresh, line_dash="dash",
                  line_color="#f59e0b", annotation_text="Alert threshold")
    fig.update_layout(
        height=320, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Equipment health")
    health_counts = view["health_status"].value_counts()
    colors = {"healthy": "#22c55e", "warning": "#f59e0b", "critical": "#ef4444"}
    fig_donut = go.Figure(go.Pie(
        labels=health_counts.index,
        values=health_counts.values,
        hole=0.55,
        marker_colors=[colors.get(k, "#94a3b8") for k in health_counts.index],
    ))
    fig_donut.update_layout(
        height=320, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True, margin=dict(l=0, r=0, t=10, b=0)
    )
    st.plotly_chart(fig_donut, use_container_width=True)


# ══════════════════════════════════════════════════════════
#  MAIN CHARTS ROW 2
# ══════════════════════════════════════════════════════════

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.subheader("24-hour forecast")
    fig_f = go.Figure()
    fig_f.add_trace(go.Scatter(
        x=forecast["timestamp"], y=forecast["forecast_kwh"],
        mode="lines+markers", name="Forecast",
        line=dict(color="#22c55e", width=2)
    ))
    fig_f.add_trace(go.Scatter(
        x=pd.concat([forecast["timestamp"], forecast["timestamp"][::-1]]),
        y=pd.concat([forecast["upper_bound"], forecast["lower_bound"][::-1]]),
        fill="toself", fillcolor="rgba(34,197,94,0.1)",
        line=dict(color="rgba(0,0,0,0)"), name="Confidence band"
    ))
    fig_f.update_layout(
        height=260, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0)
    )
    st.plotly_chart(fig_f, use_container_width=True)

with col_b:
    st.subheader("Anomaly score distribution")
    fig_hist = px.histogram(
        view, x="anomaly_score", nbins=50,
        color_discrete_sequence=["#7c3aed"]
    )
    fig_hist.add_vline(x=anomaly_thresh, line_dash="dash",
                       line_color="#ef4444", annotation_text="Threshold")
    fig_hist.update_layout(
        height=260, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), showlegend=False
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_c:
    st.subheader("Efficiency clusters")
    scatter_sample = view.sample(min(500, len(view)))
    fig_scatter = px.scatter(
        scatter_sample, x="hour", y="consumption_kwh",
        color="efficiency_label",
        color_discrete_map={
            "very efficient": "#22c55e",
            "efficient":      "#84cc16",
            "moderate":       "#f59e0b",
            "inefficient":    "#ef4444",
        },
        size="efficiency_score",
    )
    fig_scatter.update_layout(
        height=260, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0)
    )
    st.plotly_chart(fig_scatter, use_container_width=True)


# ══════════════════════════════════════════════════════════
#  ALERTS + RECOMMENDATIONS
# ══════════════════════════════════════════════════════════

st.divider()
col_alerts, col_recs = st.columns(2)

with col_alerts:
    st.subheader("🚨 Active alerts")
    from alerts.alerts_engine import AlertEngine
    alert_engine = AlertEngine()
    alerts_df = alert_engine.check_dataframe(view.tail(200))

    if not alerts_df.empty:
        filtered = alerts_df[alerts_df["severity"].isin(severity_filter)] if severity_filter else alerts_df
        for _, alert in filtered.head(8).iterrows():
            color = {"critical": "🔴", "warning": "🟠", "info": "🔵"}.get(alert["severity"], "⚪")
            st.markdown(f"""
            <div class="metric-card alert-{alert['severity']}">
                {color} <b>{alert['rule'].replace('_', ' ').title()}</b><br/>
                <small style="color:#94a3b8">{alert['message']}</small><br/>
                <small style="color:#64748b">{alert['timestamp'][:19]}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No active alerts in the selected window")

    summary = alert_engine.get_alert_summary()
    a1, a2, a3 = st.columns(3)
    a1.metric("Critical", summary["critical"])
    a2.metric("Warnings", summary["warning"])
    a3.metric("Info", summary["info"])

with col_recs:
    st.subheader("💡 AI recommendations")
    from alerts.alerts_engine import RecommendationEngine
    rec_engine = RecommendationEngine()
    recs = rec_engine.generate(view, predictions)

    priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "info": "🔵"}
    for rec in recs[:6]:
        icon = priority_icon.get(rec["priority"], "⚪")
        st.markdown(f"""
        <div class="metric-card rec-{rec['priority']}">
            {icon} <b>{rec['category']}</b> <small style="color:#64748b">({rec['priority']} priority)</small><br/>
            <small style="color:#94a3b8">{rec['recommendation']}</small>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  SHAP FEATURE IMPORTANCE
# ══════════════════════════════════════════════════════════

st.divider()
st.subheader("🧠 SHAP — Model explainability (anomaly detection)")

try:
    importance = models["anomaly"].explain(view)
    top15 = importance.head(15)
    fig_shap = px.bar(
        top15, x="shap_mean", y="feature", orientation="h",
        color="shap_mean", color_continuous_scale="Purples",
        labels={"shap_mean": "Mean |SHAP| value", "feature": "Feature"}
    )
    fig_shap.update_layout(
        height=350, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=0, r=0, t=10, b=0), showlegend=False
    )
    st.plotly_chart(fig_shap, use_container_width=True)
except Exception as e:
    st.info(f"SHAP explanation unavailable: {e}")


# ══════════════════════════════════════════════════════════
#  RAW DATA TABLE
# ══════════════════════════════════════════════════════════

with st.expander("📋 View raw prediction data"):
    display_cols = ["timestamp", "consumption_kwh", "voltage", "temperature",
                    "anomaly_flag", "anomaly_severity", "health_status",
                    "efficiency_label", "efficiency_score"]
    display_cols = [c for c in display_cols if c in view.columns]
    st.dataframe(
        view[display_cols].tail(200).sort_values("timestamp", ascending=False),
        use_container_width=True,
        height=300
    )
    st.download_button(
        "⬇ Download CSV",
        view[display_cols].to_csv(index=False),
        file_name=f"energy_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

st.divider()
st.caption("Energy Diagnostics | AI-Powered | Built with Streamlit + Python")

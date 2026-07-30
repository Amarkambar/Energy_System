// ===============================
// TIME GENERATION (unchanged)
// ===============================
export function genHours(n: number, now = new Date()): string[] {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(now.getTime() - (n - i) * 3600000);
    return `${String(d.getHours()).padStart(2, '0')}:00`;
  });
}

// ===============================
// REALISTIC DATA GENERATION (FIXED)
// ===============================
export function genData(n: number, base: number = 100): number[] {
  let value = base;

  return Array.from({ length: n }, (_, i) => {
    // trend (slight increase/decrease)
    const trend = i * 0.1;

    // realistic fluctuation
    const noise = (Math.random() - 0.5) * 8;

    value = value + noise + trend;

    // prevent negative values
    if (value < 0) value = base;

    return Number(value.toFixed(2));
  });
}

// ===============================
// KPI CALCULATIONS (NEW)
// ===============================
export function calculateKpis(data: number[]) {
  const total = data.reduce((a, b) => a + b, 0);
  const avg = total / data.length;
  const min = Math.min(...data);
  const max = Math.max(...data);

  return {
    total: Number(total.toFixed(2)),
    avg: Number(avg.toFixed(2)),
    min,
    max,
  };
}

// ===============================
// ANOMALY DETECTION (Z-SCORE)
// ===============================
export function detectAnomalies(data: number[]) {
  const mean = data.reduce((a, b) => a + b, 0) / data.length;

  const std = Math.sqrt(
    data.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / data.length
  );

  return data.map((value) => {
    const z = (value - mean) / std;

    return {
      value,
      z,
      isAnomaly: Math.abs(z) > 2, // threshold
    };
  });
}

// ===============================
// DYNAMIC ALERTS (FIXED)
// ===============================
export function generateAlerts(data: number[]) {
  return data
    .filter((v) => v > 120)
    .map((v, i) => ({
      sev: v > 140 ? 'critical' : 'warning',
      rule: 'High Consumption',
      msg: `Energy spike detected: ${v} kWh`,
      time: `${i + 1} min ago`,
    }));
}

// ===============================
// RECOMMENDATIONS (IMPROVED)
// ===============================
export function generateRecommendations(avg: number) {
  const recs = [];

  if (avg > 120) {
    recs.push({
      priority: 'high',
      category: 'Energy',
      icon: '⚡',
      text: 'Reduce peak load to improve efficiency.',
    });
  }

  if (avg < 80) {
    recs.push({
      priority: 'info',
      category: 'Optimization',
      icon: '📊',
      text: 'System operating efficiently.',
    });
  }

  return recs;
}

// ===============================
// STATIC (KEEP AS IS)
// ===============================
export const SHAP_FEATURES = [
  { name: 'consumption_kwh_lag_24h', val: 0.82 },
  { name: 'roll_mean_24h', val: 0.71 },
  { name: 'hour_sin', val: 0.64 },
  { name: 'temperature', val: 0.55 },
  { name: 'load_factor', val: 0.47 },
  { name: 'is_peak_hour', val: 0.38 },
  { name: 'fft_component_1', val: 0.31 },
];

export const PIPELINE_STEPS = [
  { num: '01', title: 'Ingestion', desc: 'Smart meters, IoT sensors, Weather API, Historical logs via Kafka / REST' },
  { num: '02', title: 'Preprocessing', desc: 'Clean duplicates, forward-fill, Z-score outlier removal, min-max normalization' },
  { num: '03', title: 'Feature Engineering', desc: 'Lag, rolling stats, FFT, cyclical time encoding, consumption ratios' },
  { num: '04', title: 'Storage', desc: 'TimescaleDB for time-series, Parquet for batch ML, FastAPI endpoints' },
  { num: '05', title: 'Outputs', desc: 'Dashboard, alerts, PDF reports, AI recommendations, email summaries' },
];

export const TECH_STACK = [
  { name: 'Python', sub: 'Pandas · NumPy · SciPy', colorClass: 'text-primary' },
  { name: 'ML Stack', sub: 'Sklearn · XGBoost · SHAP', colorClass: 'text-secondary' },
  { name: 'Streaming', sub: 'Kafka · MQTT · FastAPI', colorClass: 'text-warn' },
  { name: 'Storage', sub: 'TimescaleDB · Parquet', colorClass: 'text-destructive' },
  { name: 'Deploy', sub: 'Docker · Streamlit', colorClass: 'text-primary' },
];
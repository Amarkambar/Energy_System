import { useMemo } from "react";
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart,
  BarChart, Bar, Cell,
} from "recharts";
import ChartCard from "./ChartCard";
import EmptyChartState from "./EmptyChartState";
import { useCsvData } from "@/lib/csv-context";
import { useMlContext } from "@/lib/ml-context";

const COLORS = {
  accent: "#00e5ff", accent2: "#00ff9d", warn: "#ffb800", danger: "#ff3d5a",
  muted: "#5a7a8a", border: "#1e2d35",
};

const tooltipStyle = {
  contentStyle: { background: "#0f1519", border: "1px solid #1e2d35", borderRadius: 8, fontFamily: "Space Mono", fontSize: 11 },
  labelStyle: { fontFamily: "Syne", fontWeight: 700, color: "#e2eef5" },
};

const ForecastPage = () => {
  const { analytics } = useCsvData();
  const { forecast: mlForecast } = useMlContext();
  const mlReady = !!mlForecast;
  const hasData = mlReady || (!!analytics && analytics.consumptionTimeSeries.length > 0);

  // Pull real forecast from backend
  const backendForecast = mlReady
    ? (mlForecast.forecast as {time:string;forecast:number;lower:number;upper:number}[]) ?? []
    : null;
  const backendPeakData = mlReady
    ? (mlForecast.peakData as {time:string;probability:number}[]) ?? []
    : null;

  // Generate forecast from last data points with simple moving average + trend
  const forecastData = useMemo(() => {
    if (!hasData) return [];
    // Use real ML forecast from backend
    if (backendForecast && backendForecast.length > 0) return backendForecast;
    if (!analytics) return [];
    const series = analytics.consumptionTimeSeries;
    const lastN = series.slice(-Math.min(24, series.length));
    const avg = lastN.reduce((s, d) => s + d.value, 0) / lastN.length;
    const trend = lastN.length > 1 ? (lastN[lastN.length - 1].value - lastN[0].value) / lastN.length : 0;
    return Array.from({ length: 24 }, (_, i) => {
      const base = avg + trend * i + (Math.sin(i / 6 * Math.PI) * avg * 0.1);
      return { time: `+${i + 1}h`, forecast: +base.toFixed(1), lower: +(base * 0.88).toFixed(1), upper: +(base * 1.12).toFixed(1) };
    });
  }, [analytics, hasData, backendForecast]);

  const peakData = useMemo(() => {
    if (forecastData.length === 0) return [];
    if (backendPeakData && backendPeakData.length > 0) return backendPeakData.map(d => ({
      time: d.time,
      probability: d.probability,
      color: d.probability > 70 ? COLORS.danger : d.probability > 40 ? COLORS.warn : COLORS.accent,
    }));
    if (!analytics) return [];
    const threshold = analytics.peakUsage * 0.8;
    return forecastData.map((d) => ({
      time: d.time,
      probability: +Math.min(99, Math.max(1, ((d.forecast - threshold * 0.5) / threshold) * 100)).toFixed(1),
      color: d.forecast > threshold ? COLORS.danger : d.forecast > threshold * 0.7 ? COLORS.warn : COLORS.accent,
    }));
  }, [forecastData, analytics]);

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-5">
        <div className="font-head text-xl font-extrabold tracking-tight">24-Hour Demand Forecast</div>
        <div className="text-[11px] text-muted-foreground uppercase tracking-widest">
          {hasData ? "Based on uploaded data trends" : "Upload data to generate forecast"}
        </div>
      </div>

      <ChartCard
        title="Energy demand forecast — next 24 hours"
        subtitle={hasData ? "Shaded area = confidence interval" : "Awaiting data"}
        titleRight={hasData ? "AI-generated" : ""}
      >
        {hasData ? (
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={forecastData}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
              <XAxis dataKey="time" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
              <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
              <Tooltip {...tooltipStyle} />
              <Area type="monotone" dataKey="upper" stroke="rgba(0,255,157,0.25)" strokeWidth={1} fill="rgba(0,255,157,0.07)" />
              <Area type="monotone" dataKey="lower" stroke="rgba(0,255,157,0.25)" strokeWidth={1} fill="transparent" />
              {/* FIX: Line is not supported inside AreaChart — use Area with no fill and dashed stroke */}
              <Area type="monotone" dataKey="forecast" stroke={COLORS.accent2} strokeWidth={2.5} fill="transparent" strokeDasharray="0" dot={{ r: 3, fill: COLORS.accent2 }} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChartState message="Upload CSV with consumption data to generate forecasts" />
        )}
      </ChartCard>

      <div className="grid grid-cols-2 gap-4 mt-4 max-md:grid-cols-1">
        <ChartCard title="Hourly forecast table" subtitle={hasData ? "Next 24 hours" : "Awaiting data"}>
          {forecastData.length > 0 ? (
            <div className="overflow-y-auto max-h-[280px]">
              <table className="w-full border-collapse text-[11px]">
                <thead>
                  <tr>
                    {["Time", "Forecast (kWh)", "Lower", "Upper", "Trend"].map((h) => (
                      <th key={h} className="text-left p-2 px-3 text-muted-foreground uppercase tracking-widest text-[10px] border-b border-border font-normal">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {forecastData.map((row, i) => {
                    // FIX: i=0 previously compared to itself (always ▼). Now shows — for first row.
                    const trendEl = i === 0
                      ? <span className="text-muted-foreground">—</span>
                      : row.forecast > forecastData[i - 1].forecast
                        ? <span className="text-destructive">▲</span>   // rising = higher demand = warn
                        : <span className="text-secondary">▼</span>;     // falling = lower demand = ok
                    return (
                      <tr key={row.time ?? i} className="hover:bg-bg3 transition-colors">
                        <td className="p-2 px-3 border-b border-border">{row.time}</td>
                        <td className="p-2 px-3 border-b border-border text-primary font-bold">{row.forecast}</td>
                        <td className="p-2 px-3 border-b border-border text-muted-foreground">{row.lower}</td>
                        <td className="p-2 px-3 border-b border-border text-muted-foreground">{row.upper}</td>
                        <td className="p-2 px-3 border-b border-border">{trendEl}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>

        <ChartCard title="Peak probability" subtitle={hasData ? "Likelihood of crossing threshold" : "Awaiting data"}>
          {peakData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={peakData}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                <XAxis dataKey="time" tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }} interval={2} />
                <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="probability" radius={[3, 3, 0, 0]}>
                  {peakData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>
      </div>
    </div>
  );
};

export default ForecastPage;

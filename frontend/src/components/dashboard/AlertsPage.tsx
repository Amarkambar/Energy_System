import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import ChartCard from "./ChartCard";
import EmptyChartState from "./EmptyChartState";
import { useCsvData } from "@/lib/csv-context";
import { useMlContext } from "@/lib/ml-context";
import { cn } from "@/lib/utils";

const COLORS = {
  accent: "#00e5ff", accent2: "#00ff9d", warn: "#ffb800", danger: "#ff3d5a",
  muted: "#5a7a8a", border: "#1e2d35",
};

const tooltipStyle = {
  contentStyle: { background: "#0f1519", border: "1px solid #1e2d35", borderRadius: 8, fontFamily: "Space Mono", fontSize: 11 },
  labelStyle: { fontFamily: "Syne", fontWeight: 700, color: "#e2eef5" },
};

const sevBorder = { critical: "border-l-destructive", warning: "border-l-warn", info: "border-l-primary" };
const sevDot = { critical: "bg-destructive shadow-[0_0_6px] shadow-destructive", warning: "bg-warn shadow-[0_0_6px] shadow-warn", info: "bg-primary shadow-[0_0_6px] shadow-primary" };
const sevBadgeBg = { critical: "bg-destructive/15 text-destructive", warning: "bg-warn/15 text-warn", info: "bg-primary/10 text-primary" };
const priIcon = { critical: "bg-destructive/10", high: "bg-warn/10", medium: "bg-primary/10", info: "bg-secondary/10" };
const priBadge = { critical: "bg-destructive/15 text-destructive", high: "bg-warn/15 text-warn", medium: "bg-primary/10 text-primary", info: "bg-secondary/10 text-secondary" };

type SevFilter = "all" | "critical" | "warning" | "info";

const AlertsPage = () => {
  const { analytics } = useCsvData();
  const { alerts: mlAlerts } = useMlContext();
  const mlReady = !!mlAlerts;
  const hasData = mlReady || !!analytics;

  // Pull real alerts from backend when available
  const backendAlerts = mlReady
    ? (mlAlerts.alerts as {sev:string;rule:string;msg:string;time:string}[]) ?? []
    : null;
  const backendRecs = mlReady
    ? (mlAlerts.recommendations as {priority:string;category:string;text:string;icon:string}[]) ?? []
    : null;
  const [sevFilter, setSevFilter] = useState<SevFilter>("all");

  // Generate alerts from analytics
  const alerts = useMemo(() => {
    if (!hasData) return [];
    // Use real backend alerts when available
    if (backendAlerts && backendAlerts.length > 0) {
      return backendAlerts.map(a => ({
        sev: (a.sev === "critical" || a.sev === "warning" || a.sev === "info" ? a.sev : "info") as "critical"|"warning"|"info",
        rule: a.rule, msg: a.msg, time: a.time,
      }));
    }
    if (!analytics) return [];
    const list: { sev: "critical" | "warning" | "info"; rule: string; msg: string; time: string }[] = [];

    if (analytics.peakUsage > analytics.averageUsage * 2) {
      list.push({ sev: "critical", rule: "Peak Spike Detected", msg: `Peak usage ${analytics.peakUsage.toFixed(1)} kWh is ${(analytics.peakUsage / analytics.averageUsage).toFixed(1)}x above average.`, time: "From analysis" });
    }
    if (analytics.invalidRows > 0) {
      list.push({ sev: "warning", rule: "Data Quality Issue", msg: `${analytics.invalidRows} invalid rows found during parsing. Check data integrity.`, time: "From analysis" });
    }
    if (analytics.voltageDeviation > 5) {
      list.push({ sev: "critical", rule: "Voltage Instability", msg: `Voltage deviation of ±${analytics.voltageDeviation}V exceeds safe threshold.`, time: "From analysis" });
    }
    if (analytics.avgVoltage > 0 && Math.abs(analytics.avgVoltage - 230) > 10) {
      list.push({ sev: "warning", rule: "Voltage Deviation", msg: `Average voltage ${analytics.avgVoltage}V deviates ${Math.abs(analytics.avgVoltage - 230).toFixed(1)}V from nominal 230V.`, time: "From analysis" });
    }
    const anomalyHighCount = analytics.anomalyData.slice(7).reduce((s, d) => s + d.count, 0);
    if (anomalyHighCount > analytics.filteredRowCount * 0.05) {
      list.push({ sev: "critical", rule: "High Anomaly Rate", msg: `${anomalyHighCount} readings (${(anomalyHighCount / analytics.filteredRowCount * 100).toFixed(1)}%) flagged as anomalous.`, time: "From analysis" });
    }
    if (analytics.dataAccuracy < 95) {
      list.push({ sev: "warning", rule: "Low Data Accuracy", msg: `Data accuracy at ${analytics.dataAccuracy}%. Consider cleaning the dataset.`, time: "From analysis" });
    }
    if (analytics.peakUsage > analytics.averageUsage * 1.5) {
      list.push({ sev: "info", rule: "Load Optimization", msg: `Peak-to-average ratio is ${(analytics.peakUsage / analytics.averageUsage).toFixed(1)}x. Consider load shifting.`, time: "From analysis" });
    }
    if (analytics.hourlyDistribution[3]?.hours > analytics.filteredRowCount * 0.15) {
      list.push({ sev: "warning", rule: "Inefficiency Detected", msg: `${analytics.hourlyDistribution[3].hours} readings classified as inefficient.`, time: "From analysis" });
    }
    return list;
  // FIX: added mlAlerts to deps — without it, alerts never updated when pipeline completed
  }, [analytics, hasData, mlAlerts]);

  // Generate recommendations from analytics
  const recs = useMemo(() => {
    if (!hasData) return [];
    // Use real backend recommendations when available
    if (backendRecs && backendRecs.length > 0) {
      return backendRecs.map(r => ({
        priority: (["critical","high","medium","info"].includes(r.priority) ? r.priority : "info") as "critical"|"high"|"medium"|"info",
        category: r.category, icon: r.icon, text: r.text,
      }));
    }
    if (!analytics) return [];
    const list: { priority: "critical" | "high" | "medium" | "info"; category: string; icon: string; text: string }[] = [];

    const anomalyRate = (analytics.anomalyData.slice(7).reduce((s, d) => s + d.count, 0) / Math.max(1, analytics.filteredRowCount)) * 100;
    if (anomalyRate > 3) {
      list.push({ priority: "critical", category: "Equipment", icon: "🔧", text: `Anomaly rate is ${anomalyRate.toFixed(1)}% — inspect equipment in zones with repeated spikes.` });
    }
    if (analytics.peakUsage > analytics.averageUsage * 1.8) {
      list.push({ priority: "high", category: "Load Management", icon: "⚡", text: `Shift peak load to off-peak hours. Peak is ${(analytics.peakUsage / analytics.averageUsage).toFixed(1)}x above average.` });
    }
    const effScore = Math.round((analytics.averageUsage / Math.max(1, analytics.peakUsage)) * 100);
    if (effScore < 80) {
      list.push({ priority: "high", category: "Efficiency", icon: "🎯", text: `Efficiency score is ${effScore}/100. Upgrade equipment for 15–25% improvement.` });
    }
    if (analytics.voltageDeviation > 3) {
      list.push({ priority: "medium", category: "Power Quality", icon: "🔌", text: `Voltage fluctuation ±${analytics.voltageDeviation}V. Install automatic voltage regulators.` });
    }
    if (analytics.totalConsumption > 0) {
      list.push({ priority: "info", category: "Renewable Energy", icon: "☀️", text: `Total consumption of ${analytics.totalConsumption.toFixed(0)} kWh suggests strong ROI for solar installation.` });
    }
    return list;
  // FIX: added mlAlerts to deps — without it, recs never updated when pipeline completed
  }, [analytics, hasData, mlAlerts]);

  const filteredAlerts = sevFilter === "all" ? alerts : alerts.filter((a) => a.sev === sevFilter);

  const alertCats = useMemo(() => {
    if (alerts.length === 0) return [];
    const cats: Record<string, number> = {};
    alerts.forEach((a) => { cats[a.rule] = (cats[a.rule] || 0) + 1; });
    const catColors = [COLORS.danger, COLORS.warn, COLORS.accent, COLORS.accent2, "#a855f7", "#fb923c"];
    return Object.entries(cats).map(([name, value], i) => ({
      name, value, color: catColors[i % catColors.length],
    }));
  }, [alerts]);

  const alertTrend = useMemo(() => {
    if (alerts.length === 0) return [];
    return [{ day: "Analysis", Critical: alerts.filter((a) => a.sev === "critical").length, Warning: alerts.filter((a) => a.sev === "warning").length, Info: alerts.filter((a) => a.sev === "info").length }];
  }, [alerts]);

  const sevFilters: { id: SevFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: alerts.length },
    { id: "critical", label: "Critical", count: alerts.filter((a) => a.sev === "critical").length },
    { id: "warning", label: "Warning", count: alerts.filter((a) => a.sev === "warning").length },
    { id: "info", label: "Info", count: alerts.filter((a) => a.sev === "info").length },
  ];

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-5">
        <div className="font-head text-xl font-extrabold tracking-tight">Alerts & Recommendations</div>
        <div className="text-[11px] text-muted-foreground uppercase tracking-widest">
          {hasData ? `${alerts.length} alerts · ML-triggered` : "Upload data to generate alerts"}
        </div>
      </div>

      {/* Severity filter */}
      {hasData && (
        <div className="flex items-center gap-1.5 mb-5">
          {sevFilters.map((f) => (
            <button
              key={f.id}
              onClick={() => setSevFilter(f.id)}
              className={cn(
                "px-3 py-1.5 rounded-md text-[10px] font-head font-semibold transition-all cursor-pointer",
                sevFilter === f.id
                  ? "bg-primary/15 text-primary border border-primary/30"
                  : "bg-bg3 text-muted-foreground border border-transparent hover:border-border"
              )}
            >
              {f.label} ({f.count})
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4 max-md:grid-cols-1">
        {/* Alerts */}
        <div>
          <div className="font-head text-sm font-bold mb-3.5">🚨 Active Alerts</div>
          {filteredAlerts.length > 0 ? (
            <div className="flex flex-col gap-2">
              {filteredAlerts.map((a, i) => (
                <div
                  key={i}
                  className={cn(
                    "bg-bg3 border border-border border-l-[3px] rounded-lg p-3 px-3.5 flex items-start gap-3 cursor-pointer hover:bg-bg2 transition-colors animate-fade-up",
                    sevBorder[a.sev]
                  )}
                  style={{ animationDelay: `${i * 0.07}s` }}
                >
                  <div className={cn("w-2 h-2 rounded-full shrink-0 mt-[5px]", sevDot[a.sev])} />
                  <div className="flex-1">
                    <div className="font-bold text-xs mb-0.5">{a.rule}</div>
                    <div className="text-muted-foreground text-[11px] leading-relaxed">{a.msg}</div>
                    <div className="text-[10px] text-border2 mt-1">{a.time}</div>
                  </div>
                  <div className={cn("text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded font-bold shrink-0 mt-0.5", sevBadgeBg[a.sev])}>
                    {a.sev}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-bg3 border border-border rounded-lg p-8 text-center">
              <p className="text-[11px] text-muted-foreground">{hasData ? "No alerts match this filter" : "Upload CSV and run analytics to generate alerts"}</p>
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div>
          <div className="font-head text-sm font-bold mb-3.5">💡 AI Recommendations</div>
          {recs.length > 0 ? (
            <div className="flex flex-col gap-2">
              {recs.map((r, i) => (
                <div
                  key={i}
                  className="bg-bg3 border border-border rounded-lg p-3.5 px-4 flex gap-3 items-start cursor-pointer hover:border-border2 hover:translate-x-[3px] transition-all animate-fade-up"
                  style={{ animationDelay: `${i * 0.07}s` }}
                >
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-base shrink-0", priIcon[r.priority])}>
                    {r.icon}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="font-head text-[13px] font-bold">{r.category}</div>
                      <div className={cn("text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded font-bold", priBadge[r.priority])}>
                        {r.priority}
                      </div>
                    </div>
                    <div className="text-[11px] text-muted-foreground leading-relaxed">{r.text}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-bg3 border border-border rounded-lg p-8 text-center">
              <p className="text-[11px] text-muted-foreground">Upload CSV and run analytics to get recommendations</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
        <ChartCard title="Alert summary" subtitle={hasData ? "By severity" : "Awaiting data"}>
          {alertTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={alertTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                <XAxis dataKey="day" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="Critical" fill={COLORS.danger} radius={[3, 3, 0, 0]} />
                <Bar dataKey="Warning" fill={COLORS.warn} radius={[3, 3, 0, 0]} />
                <Bar dataKey="Info" fill={COLORS.accent} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>

        <ChartCard title="Alert categories" subtitle={hasData ? "Breakdown by rule type" : "Awaiting data"}>
          {alertCats.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={alertCats} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" stroke="#0f1519" strokeWidth={3}>
                  {alertCats.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip {...tooltipStyle} />
                <Legend layout="vertical" align="right" verticalAlign="middle" iconSize={8} wrapperStyle={{ fontFamily: "Space Mono", fontSize: 9, color: COLORS.muted }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>
      </div>
    </div>
  );
};

export default AlertsPage;

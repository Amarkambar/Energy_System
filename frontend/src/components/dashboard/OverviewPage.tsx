import { useState, useMemo } from "react";
import { format } from "date-fns";
import { CalendarIcon, X, SlidersHorizontal } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell,
} from "recharts";
import KpiCard from "./KpiCard";
import ChartCard from "./ChartCard";
import AnalyticsToolbar from "./AnalyticsToolbar";
import EmptyChartState from "./EmptyChartState";
import DataPreviewTable from "./DataPreviewTable";
import ExportBar from "./ExportBar";
import { useCsvData } from "@/lib/csv-context";
import { cn } from "@/lib/utils";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const COLORS = {
  accent: "#00e5ff",
  accent2: "#00ff9d",
  warn: "#ffb800",
  danger: "#ff3d5a",
  muted: "#5a7a8a",
  bg3: "#141c21",
  border: "#1e2d35",
  blue: "#3399FF",
};

const tooltipStyle = {
  contentStyle: { background: "#0f1519", border: "1px solid #1e2d35", borderRadius: 8, fontFamily: "Space Mono", fontSize: 11 },
  labelStyle: { fontFamily: "Syne", fontWeight: 700, color: "#e2eef5" },
  itemStyle: { color: "#5a7a8a" },
};

type ChartToggle = "consumption" | "voltage" | "efficiency" | "anomaly";

const OverviewPage = () => {
  const { analytics, runAnalytics, rawData } = useCsvData();
  const [dateFrom, setDateFrom] = useState<Date | undefined>();
  const [dateTo, setDateTo] = useState<Date | undefined>();
  const [activeCharts, setActiveCharts] = useState<Set<ChartToggle>>(
    new Set(["consumption", "voltage", "efficiency", "anomaly"])
  );

  const hasData = !!analytics; 
  const activeAnalytics = analytics;

  const toggleChart = (chart: ChartToggle) => {
    setActiveCharts((prev) => {
      const next = new Set(prev);
      if (next.has(chart)) next.delete(chart);
      else next.add(chart);
      return next;
    });
  };

  const handleApplyDateFilter = () => {
    if (rawData.length > 0) runAnalytics(dateFrom || null, dateTo || null);
  };

  const handleClearDates = () => {
    setDateFrom(undefined);
    setDateTo(undefined);
    if (rawData.length > 0) runAnalytics(null, null);
  };

  const healthData = useMemo(() => {
    if (!hasData || !activeAnalytics) return [];
    const total = activeAnalytics.filteredRowCount || 1;
    const anomalyRate = activeAnalytics.anomalyData.slice(7).reduce((s, d) => s + d.count, 0) / total;
    const warnRate = activeAnalytics.anomalyData.slice(5, 7).reduce((s, d) => s + d.count, 0) / total;
    const idleRate = activeAnalytics.anomalyData.slice(0, 2).reduce((s, d) => s + d.count, 0) / total;
    const healthyRate = Math.max(0, 1 - anomalyRate - warnRate - idleRate);
    return [
      { name: "Healthy", value: Math.round(healthyRate * 100), color: COLORS.accent2 },
      { name: "Warning", value: Math.round(warnRate * 100), color: COLORS.warn },
      { name: "Critical", value: Math.round(anomalyRate * 100), color: COLORS.danger },
      { name: "Idle", value: Math.round(idleRate * 100), color: COLORS.blue },
    ];
  }, [activeAnalytics, hasData]);

  const chartToggles: { id: ChartToggle; label: string }[] = [
    { id: "consumption", label: "Consumption" },
    { id: "voltage", label: "Voltage" },
    { id: "efficiency", label: "Efficiency" },
    { id: "anomaly", label: "Anomaly" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        {(() => {
          try {
            const user = JSON.parse(localStorage.getItem("energydiag_user") || '{"name":"User"}');
            return (
              <h1 className="font-head text-2xl font-extrabold tracking-tight mb-1">
                Welcome back, <span className="text-primary">{user.name}</span>
              </h1>
            );
          } catch {
            return <h1 className="font-head text-2xl font-extrabold tracking-tight mb-1">Dashboard</h1>;
          }
        })()}
        <p className="text-muted-foreground text-sm">Industrial energy diagnostics & decision support</p>
      </div>

      <AnalyticsToolbar />

      {hasData && (
        <div className="flex justify-end mb-4 -mt-2">
          <ExportBar />
        </div>
      )}

      {/* ── Modern Filter Bar ─────────────────────────────────── */}
      <div className="bg-card border border-border rounded-xl p-4 mb-6 animate-fade-up">
        <div className="flex items-center justify-between flex-wrap gap-4">

          {/* Left: date pickers */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground uppercase tracking-widest font-head font-semibold">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Filters
            </div>

            {/* Date From */}
            <Popover>
              <PopoverTrigger asChild>
                <button className={cn(
                  "group flex items-center gap-2 px-3 py-2 rounded-lg border text-[12px] font-head font-semibold transition-all cursor-pointer",
                  dateFrom
                    ? "border-primary/50 text-primary bg-primary/8 shadow-[0_0_12px_rgba(0,229,255,0.1)]"
                    : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground hover:bg-primary/5"
                )}>
                  <CalendarIcon className="w-3.5 h-3.5" />
                  {dateFrom ? format(dateFrom, "MMM dd, yyyy") : "From date"}
                  {dateFrom && (
                    <span
                      onClick={(e) => { e.stopPropagation(); setDateFrom(undefined); }}
                      className="ml-1 opacity-60 hover:opacity-100"
                    >
                      <X className="w-3 h-3" />
                    </span>
                  )}
                </button>
              </PopoverTrigger>
              <PopoverContent
                className="w-auto p-0 bg-card border border-border rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden"
                align="start"
                sideOffset={6}
              >
                <div className="px-3 pt-3 pb-1 border-b border-border">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-head">Select start date</p>
                </div>
                <Calendar
                  mode="single"
                  selected={dateFrom}
                  onSelect={setDateFrom}
                  fromYear={2000}
                  toYear={2030}
                  initialFocus
                  className="p-3"
                />
              </PopoverContent>
            </Popover>

            {/* Arrow separator */}
            <span className="text-muted-foreground text-xs">→</span>

            {/* Date To */}
            <Popover>
              <PopoverTrigger asChild>
                <button className={cn(
                  "group flex items-center gap-2 px-3 py-2 rounded-lg border text-[12px] font-head font-semibold transition-all cursor-pointer",
                  dateTo
                    ? "border-primary/50 text-primary bg-primary/8 shadow-[0_0_12px_rgba(0,229,255,0.1)]"
                    : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground hover:bg-primary/5"
                )}>
                  <CalendarIcon className="w-3.5 h-3.5" />
                  {dateTo ? format(dateTo, "MMM dd, yyyy") : "To date"}
                  {dateTo && (
                    <span
                      onClick={(e) => { e.stopPropagation(); setDateTo(undefined); }}
                      className="ml-1 opacity-60 hover:opacity-100"
                    >
                      <X className="w-3 h-3" />
                    </span>
                  )}
                </button>
              </PopoverTrigger>
              <PopoverContent
                className="w-auto p-0 bg-card border border-border rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden"
                align="start"
                sideOffset={6}
              >
                <div className="px-3 pt-3 pb-1 border-b border-border">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-head">Select end date</p>
                </div>
                <Calendar
                  mode="single"
                  selected={dateTo}
                  onSelect={setDateTo}
                  fromYear={2000}
                  toYear={2030}
                  initialFocus
                  className="p-3"
                />
              </PopoverContent>
            </Popover>

            {/* Apply button */}
            <button
              onClick={handleApplyDateFilter}
              disabled={rawData.length === 0}
              className={cn(
                "px-4 py-2 rounded-lg text-[11px] font-head font-bold transition-all",
                rawData.length > 0
                  ? "bg-primary text-background hover:opacity-90 cursor-pointer shadow-[0_0_16px_rgba(0,229,255,0.2)]"
                  : "bg-muted/30 text-muted-foreground cursor-not-allowed border border-border"
              )}
            >
              Apply
            </button>

            {(dateFrom || dateTo) && (
              <button
                onClick={handleClearDates}
                className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-destructive transition-colors cursor-pointer"
              >
                <X className="w-3 h-3" /> Clear
              </button>
            )}
          </div>

          {/* Right: chart toggles */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-muted-foreground uppercase tracking-widest mr-1">Charts:</span>
            {chartToggles.map((t) => (
              <button
                key={t.id}
                onClick={() => toggleChart(t.id)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-[10px] font-head font-semibold transition-all cursor-pointer",
                  activeCharts.has(t.id)
                    ? "bg-primary/15 text-primary border border-primary/40 shadow-[0_0_8px_rgba(0,229,255,0.1)]"
                    : "bg-bg3 text-muted-foreground border border-transparent hover:border-border hover:text-foreground"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Active date range indicator */}
        {(dateFrom || dateTo) && (
          <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-dot" />
            <span className="text-muted-foreground">Active filter:</span>
            {dateFrom && <span className="text-primary font-head font-bold">{format(dateFrom, "MMM dd, yyyy")}</span>}
            {dateFrom && dateTo && <span className="text-muted-foreground">→</span>}
            {dateTo && <span className="text-primary font-head font-bold">{format(dateTo, "MMM dd, yyyy")}</span>}
          </div>
        )}
      </div>

      {/* Data range info */}
      {hasData && activeAnalytics?.dateRange?.min && (
        <div className="text-[10px] text-muted-foreground mb-4 flex items-center gap-2">
          <span className="uppercase tracking-widest">Data range:</span>
          <span className="text-foreground">{activeAnalytics.dateRange.min?.toLocaleDateString()}</span>
          <span>→</span>
          <span className="text-foreground">{activeAnalytics.dateRange.max ? activeAnalytics.dateRange.max.toLocaleDateString() : "—"}</span>
          <span className="text-border">·</span>
          <span>{activeAnalytics.filteredRowCount} of {activeAnalytics.rowCount} rows</span>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-5 gap-3 mb-6 max-lg:grid-cols-3 max-md:grid-cols-2">
        <KpiCard label="Total Consumption" value={hasData && activeAnalytics ? activeAnalytics.totalConsumption.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0.00"} unit="kWh" delta={hasData && activeAnalytics ? `${activeAnalytics.filteredRowCount} data points` : "No data uploaded"} deltaType="neutral" icon="⚡" delay={0.05} />
        <KpiCard label="Average Usage" value={hasData && activeAnalytics ? activeAnalytics.averageUsage.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0.00"} unit="kWh" delta={hasData ? "per reading" : "—"} deltaType="neutral" icon="📊" delay={0.1} />
        <KpiCard label="Peak Usage" value={hasData && activeAnalytics ? activeAnalytics.peakUsage.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0.00"} unit="kWh" delta={hasData && activeAnalytics ? `min: ${activeAnalytics.minUsage}` : "—"} deltaType={hasData ? "up" : "neutral"} icon="📈" variant="warn" delay={0.15} />
        <KpiCard label="Data Accuracy" value={hasData && activeAnalytics ? activeAnalytics.dataAccuracy.toFixed(0) : "0"} unit="%" delta={hasData && activeAnalytics ? `${activeAnalytics.filteredRowCount - activeAnalytics.invalidRows} valid rows` : "—"} deltaType={hasData && activeAnalytics && activeAnalytics.dataAccuracy > 95 ? "down" : "neutral"} icon="✅" variant="green" delay={0.2} />
        <KpiCard label="Invalid Rows" value={hasData && activeAnalytics ? activeAnalytics.invalidRows.toString() : "0"} unit="" delta={hasData ? "parsing errors" : "—"} deltaType={hasData && activeAnalytics && activeAnalytics.invalidRows > 0 ? "up" : "neutral"} icon="⚠️" variant={hasData && activeAnalytics && activeAnalytics.invalidRows > 0 ? "danger" : "default"} delay={0.25} />
      </div>

      {/* Voltage KPIs */}
      {hasData && activeAnalytics && activeAnalytics.voltageTimeSeries.length > 0 && (
        <div className="grid grid-cols-5 gap-3 mb-6 max-lg:grid-cols-3 max-md:grid-cols-2">
          <KpiCard label="Avg Voltage" value={activeAnalytics.avgVoltage.toString()} unit="V" delta={`±${activeAnalytics.voltageDeviation}V deviation`} deltaType="neutral" icon="🔌" delay={0.05} />
          <KpiCard label="Voltage Readings" value={activeAnalytics.voltageTimeSeries.length.toString()} unit="pts" delta="total measurements" deltaType="neutral" icon="📐" delay={0.1} />
        </div>
      )}

      {/* Main charts */}
      <div className="grid grid-cols-[2fr_1fr] gap-4 mb-4 max-md:grid-cols-1">
        {activeCharts.has("consumption") && (
          <ChartCard
            title="Energy Consumption"
            subtitle={hasData && activeAnalytics ? `${activeAnalytics.consumptionTimeSeries.length} readings · ${activeAnalytics.consumptionColumn || "auto-detected"}` : "Upload CSV to populate"}
            titleRight={hasData && activeAnalytics?.dateRange?.min && activeAnalytics?.dateRange?.max ? format(activeAnalytics.dateRange.min, "MMM dd") + " – " + format(activeAnalytics.dateRange.max, "MMM dd") : ""}
            delay={0.3}
          >
            {hasData && activeAnalytics && activeAnalytics.consumptionTimeSeries.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={activeAnalytics.consumptionTimeSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="time" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} interval={Math.max(1, Math.floor(activeAnalytics.consumptionTimeSeries.length / 8))} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <Tooltip {...tooltipStyle} />
                  <Line type="monotone" dataKey="value" stroke={COLORS.accent} strokeWidth={1.5} dot={activeAnalytics.consumptionTimeSeries.length < 50} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChartState message="Upload CSV with a consumption/energy column" />
            )}
          </ChartCard>
        )}

        {/* Equipment Health Donut */}
        <ChartCard title="Equipment Health" subtitle={hasData ? "Derived from anomaly analysis" : "Awaiting data"} delay={0.35}>
          {hasData && healthData.length > 0 ? (
            <div>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={healthData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} dataKey="value" stroke={COLORS.bg3} strokeWidth={3}>
                    {healthData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-1.5 mt-2">
                {healthData.map((item) => (
                  <div key={item.name} className="flex items-center gap-1.5 text-[10px]">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: item.color }} />
                    <span className="text-muted-foreground">{item.name}</span>
                    <span className="ml-auto font-mono font-bold" style={{ color: item.color }}>{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>
      </div>

      {/* Bottom charts */}
      <div className="grid grid-cols-3 gap-4 max-md:grid-cols-1">
        {activeCharts.has("anomaly") && (
          <ChartCard title="Anomaly Scores" subtitle={hasData ? "Distribution by score range" : "Awaiting data"} delay={0.4}>
            {hasData && activeAnalytics && activeAnalytics.anomalyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={activeAnalytics.anomalyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="range" tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {activeAnalytics.anomalyData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyChartState />}
          </ChartCard>
        )}

        {activeCharts.has("efficiency") && (
          <ChartCard title="Efficiency Clusters" subtitle={hasData ? "From ML clustering" : "Awaiting data"} delay={0.45}>
            {hasData && activeAnalytics ? (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={activeAnalytics.hourlyDistribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="name" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="hours" radius={[4, 4, 0, 0]}>
                    {activeAnalytics.hourlyDistribution.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyChartState />}
          </ChartCard>
        )}

        {activeCharts.has("voltage") && (
          <ChartCard title="Voltage Pattern" subtitle={hasData && activeAnalytics && activeAnalytics.voltageTimeSeries.length > 0 ? `${activeAnalytics.voltageTimeSeries.length} readings` : "Awaiting data"} delay={0.5}>
            {hasData && activeAnalytics && activeAnalytics.voltageTimeSeries.length > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={activeAnalytics.voltageTimeSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="time" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} interval={Math.max(1, Math.floor(activeAnalytics.voltageTimeSeries.length / 8))} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} domain={["auto", "auto"]} />
                  <Tooltip {...tooltipStyle} />
                  <Line type="monotone" dataKey="voltage" stroke={COLORS.warn} strokeWidth={1.5} dot={activeAnalytics.voltageTimeSeries.length < 50 ? { r: 2, fill: COLORS.warn } : false} />
                  <Line type="monotone" dataKey="nominal" stroke={COLORS.muted} strokeWidth={1} strokeDasharray="4 3" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <EmptyChartState message="Upload CSV with a voltage column" />}
          </ChartCard>
        )}
      </div>

      {/* Data Preview */}
      <div className="mt-6">
        <DataPreviewTable />
      </div>
    </div>
  );
};

export default OverviewPage;
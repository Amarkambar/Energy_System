import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area,
} from "recharts";
import ChartCard from "./ChartCard";
import EmptyChartState from "./EmptyChartState";
import { PIPELINE_STEPS, TECH_STACK } from "@/lib/dashboard-data";
import { useCsvData } from "@/lib/csv-context";
import { useMlContext } from "@/lib/ml-context";

const COLORS = {
  accent: "#00e5ff", accent2: "#00ff9d", muted: "#5a7a8a", border: "#1e2d35",
};

const tooltipStyle = {
  contentStyle: { background: "#0f1519", border: "1px solid #1e2d35", borderRadius: 8, fontFamily: "Space Mono", fontSize: 11 },
  labelStyle: { fontFamily: "Syne", fontWeight: 700, color: "#e2eef5" },
};

const PipelinePage = () => {
  const { analytics, rawData } = useCsvData();
  const { pipelineStats, pipelineReady, loadState, runPipeline } = useMlContext();
  const mlReady = !!pipelineStats;
  const hasData = mlReady || rawData.length > 0;

  const backendRows = mlReady ? (pipelineStats.rows as number) : rawData.length;
  const backendVolume = mlReady ? (pipelineStats.volumeSeries as {time:string;value:number}[]) ?? [] : [];
  const backendFeatureDist = mlReady ? (pipelineStats.featureDist as {feature:string;std:number}[]) ?? [] : [];
  const backendSteps = mlReady ? (pipelineStats.steps as {num:string;title:string;desc:string;status:string}[]) : null;

  // Pipeline steps status
  const stepStatus = hasData
    ? ["✓ Active", "✓ Active", "✓ Active", "✓ Active", "✓ Active"]
    : ["Waiting", "Waiting", "Waiting", "Waiting", "Waiting"];

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-5">
        <div className="font-head text-xl font-extrabold tracking-tight">Data Pipeline</div>
        <div className="text-[11px] text-muted-foreground uppercase tracking-widest">
          {hasData ? `Processing ${backendRows.toLocaleString()} rows` : "Ingestion → Features → Models → Outputs"}
        </div>
      </div>

      {/* Pipeline steps */}
      <div className="flex bg-card border border-border rounded-lg overflow-hidden mb-7 max-md:flex-col">
        {(backendSteps || PIPELINE_STEPS).map((step, i) => (
          <div
            key={i}
            className="flex-1 p-5 px-[18px] border-r border-border last:border-r-0 relative cursor-pointer hover:bg-bg3 transition-colors max-md:border-r-0 max-md:border-b max-md:last:border-b-0"
          >
            {hasData && <div className="absolute top-0 left-0 right-0 h-[3px] bg-secondary" />}
            <div className="font-head text-[28px] font-extrabold text-border2 mb-2">{step.num}</div>
            <div className="font-head text-[13px] font-bold mb-1">{step.title}</div>
            <div className="text-[10px] text-muted-foreground leading-relaxed">{step.desc}</div>
            <div className={`inline-block mt-2.5 text-[9px] uppercase tracking-widest px-2 py-0.5 rounded ${
              hasData ? "bg-secondary/10 text-secondary" : "bg-muted text-muted-foreground"
            }`}>
              {stepStatus[i]}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4 max-md:grid-cols-1">
        <ChartCard title="Data volume" subtitle={hasData ? `${backendRows.toLocaleString()} records loaded` : "Awaiting data"}>
          {hasData ? (
            <ResponsiveContainer width="100%" height={200}>
              {mlReady && backendVolume.length > 0 ? (
                <AreaChart data={backendVolume}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="time" tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }} interval={Math.floor(backendVolume.length / 6)} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <Tooltip {...tooltipStyle} />
                  <Area type="monotone" dataKey="value" stroke={COLORS.accent} fill={COLORS.accent + "22"} strokeWidth={2} dot={false} />
                </AreaChart>
              ) : analytics ? (
                <BarChart data={[
                  { label: "Total Rows", value: analytics.rowCount },
                  { label: "Valid", value: analytics.rowCount - analytics.invalidRows },
                  { label: "Invalid", value: analytics.invalidRows },
                  { label: "Filtered", value: analytics.filteredRowCount },
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="label" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="value" fill={COLORS.accent} radius={[4, 4, 0, 0]} />
                </BarChart>
              ) : <EmptyChartState />}
            </ResponsiveContainer>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>

        <ChartCard title="Processing summary" subtitle={hasData ? (mlReady ? "ML pipeline results" : "Column detection results") : "Awaiting data"}>
          {hasData ? (
            <div className="space-y-3 py-2">
              {mlReady ? (
                <>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Total rows processed</span>
                    <span className="text-foreground font-bold">{(pipelineStats!.rows as number).toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Feature columns</span>
                    <span className="text-secondary font-bold">{(pipelineStats!.columns as number)}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Predictions generated</span>
                    <span className="text-primary font-bold">{(pipelineStats!.predictions as number).toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Pipeline status</span>
                    <span className="text-secondary font-bold">✓ Complete</span>
                  </div>
                  {backendFeatureDist.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">Top features by variance</div>
                      <div className="space-y-1.5">
                        {backendFeatureDist.slice(0, 5).map(f => (
                          <div key={f.feature} className="flex items-center justify-between text-[10px]">
                            <span className="text-muted-foreground font-mono">{f.feature}</span>
                            <span className="text-primary font-bold">{f.std.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : analytics ? (
                <>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Columns detected</span>
                <span className="text-foreground font-bold">{analytics.columnNames.length}</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Consumption column</span>
                <span className={analytics.consumptionColumn ? "text-secondary font-bold" : "text-muted-foreground"}>
                  {analytics.consumptionColumn || "Not found"}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Voltage column</span>
                <span className={analytics.voltageColumn ? "text-secondary font-bold" : "text-muted-foreground"}>
                  {analytics.voltageColumn || "Not found"}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Time column</span>
                <span className={analytics.timeColumn ? "text-secondary font-bold" : "text-muted-foreground"}>
                  {analytics.timeColumn || "Not found"}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Data accuracy</span>
                <span className="text-primary font-bold">{analytics.dataAccuracy}%</span>
              </div>
              <div className="mt-3 pt-3 border-t border-border">
                <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">All columns</div>
                <div className="flex flex-wrap gap-1.5">
                  {analytics.columnNames.map((col) => (
                    <span key={col} className={`text-[9px] px-2 py-0.5 rounded-full border ${
                      col === analytics.consumptionColumn ? "border-primary/40 text-primary bg-primary/5" :
                      col === analytics.voltageColumn ? "border-warn/40 text-warn bg-warn/5" :
                      col === analytics.timeColumn ? "border-secondary/40 text-secondary bg-secondary/5" :
                      "border-border text-muted-foreground"
                    }`}>
                      {col}
                    </span>
                  ))}
                </div>
              </div>
                </>
              ) : null}
            </div>
          ) : (
            <EmptyChartState />
          )}
        </ChartCard>
      </div>

      {/* Tech stack */}
      <ChartCard title="Tech stack" subtitle="Components and versions">
        <div className="grid grid-cols-5 gap-2.5 max-md:grid-cols-2">
          {TECH_STACK.map((t, i) => (
            <div key={i} className="bg-bg3 border border-border rounded-lg p-3 text-center">
              <div className={`font-head text-[13px] font-bold ${t.colorClass}`}>{t.name}</div>
              <div className="text-[10px] text-muted-foreground mt-1">{t.sub}</div>
            </div>
          ))}
        </div>
      </ChartCard>
    </div>
  );
};

export default PipelinePage;

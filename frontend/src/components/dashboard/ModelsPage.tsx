import { useState, useEffect } from "react";
import {
  LineChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from "recharts";
import { useCsvData } from "@/lib/csv-context";
import { useMlContext } from "@/lib/ml-context";
import EmptyChartState from "./EmptyChartState";
import ConfusionMatrix from "./ConfusionMatrix";
import RocCurveChart from "./RocCurveChart";
import PrecisionRecallChart from "./PrecisionRecallChart";
import ModelComparisonChart from "./ModelComparisonChart";
import MetricsTable from "./MetricsTable";
import FeatureImportanceChart from "./FeatureImportanceChart";

const COLORS = {
  accent: "#00e5ff", accent2: "#00ff9d", warn: "#ffb800", danger: "#ff3d5a",
  muted: "#5a7a8a", bg3: "#141c21", border: "#1e2d35",
};

const tooltipStyle = {
  contentStyle: { background: "#0f1519", border: "1px solid #1e2d35", borderRadius: 8, fontFamily: "Space Mono", fontSize: 11 },
  labelStyle: { fontFamily: "Syne", fontWeight: 700, color: "#e2eef5" },
};

const ModelMetric = ({ val, label, color }: { val: string; label: string; color: string }) => (
  <div className="bg-bg3 rounded-md p-2.5 text-center">
    <div className="font-head text-lg font-extrabold" style={{ color }}>{val}</div>
    <div className="text-[9px] text-muted-foreground uppercase tracking-widest mt-0.5">{label}</div>
  </div>
);

const ModelCard = ({ icon, iconBg, name, algo, metrics, children, statusText }: {
  icon: string; iconBg: string; name: string; algo: string;
  metrics: { val: string; label: string; color: string }[];
  children?: React.ReactNode;
  statusText?: string;
}) => (
  <div className="bg-card border border-border rounded-lg p-[22px] animate-fade-up">
    <div className="flex items-center gap-3 mb-4">
      <div className={`w-[42px] h-[42px] rounded-lg flex items-center justify-center text-xl ${iconBg}`}>{icon}</div>
      <div>
        <div className="font-head text-[15px] font-extrabold">{name}</div>
        <div className="text-[11px] text-muted-foreground mt-0.5">{algo}</div>
      </div>
    </div>
    <div className="grid grid-cols-3 gap-2.5 mb-3.5">
      {metrics.map((m, i) => <ModelMetric key={i} {...m} />)}
    </div>
    {children}
    <div className="flex items-center gap-1.5 text-[11px] text-secondary mt-3.5">
      <div className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse-dot" />
      {statusText || "Awaiting data"}
    </div>
  </div>
);

type ViewTab = "models" | "metrics" | "comparison";

const ModelsPage = () => {
  const { analytics } = useCsvData();
  const { 
    models: mlModels, 
    pipelineReady,
    confusionMatrix,
    rocCurves,
    precisionRecall,
    modelComparison,
    featureImportance,
    refreshMetrics,
  } = useMlContext();
  const mlReady = !!mlModels;
  const hasData = mlReady || !!analytics;

  const [activeTab, setActiveTab] = useState<ViewTab>("models");
  const [metricsLoading, setMetricsLoading] = useState(false);

  // Backend metrics are only available after ML training has completed. Local
  // CSV analytics alone must not trigger requests that return 503 while training.
  useEffect(() => {
    if (pipelineReady && hasData && (activeTab === "metrics" || activeTab === "comparison")) {
      setMetricsLoading(true);
      refreshMetrics().finally(() => setMetricsLoading(false));
    }
  }, [hasData, activeTab, pipelineReady, refreshMetrics]);

  // Real model metrics from backend
  const anomalyRate = mlReady && typeof mlModels.anomalyRate === "number"
    ? mlModels.anomalyRate.toFixed(1)
    : "—";

  const forecastData = mlReady
    ? ((mlModels.forecastSeries as {time:string;value:number;lower?:number;upper?:number}[]) ?? []).map(point => ({
        ...point,
        residualRange: typeof point.lower === "number" && typeof point.upper === "number"
          ? [point.lower, point.upper]
          : undefined,
      }))
    : [];

  const maintData = mlReady
    ? (mlModels.healthDist as {name:string;value:number;color:string}[]) ?? []
    : [];

  const clusterData = mlReady
    ? ((mlModels.clusterDist as {name:string;value:number;color:string}[]) ?? []).map(d => ({ name: d.name, value: d.value, color: d.color }))
    : [];

  const shapFeatures = mlReady
    ? (mlModels.shapFeatures as {feature:string;importance:number}[]) ?? []
    : [];

  // Prepare comparison data for new charts
  const comparisonBarData = modelComparison?.bar_chart_data?.map(item => ({
    model: String(item.model || ""),
    mae: Number(item.mae) || undefined,
    rmse: Number(item.rmse) || undefined,
    r2: Number(item.r2) || undefined,
    mape: Number(item.mape) || undefined,
  })) || null;

  const metricsTableData = modelComparison?.comparison_table?.map(item => ({
    model: String(item.Model || item.model || ""),
    mae: Number(item.mae) || undefined,
    rmse: Number(item.rmse) || undefined,
    r2: Number(item.r2) || undefined,
    mape: Number(item.mape) || undefined,
  })) || null;

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-5">
        <div className="font-head text-xl font-extrabold tracking-tight">AI / ML Models</div>
        <div className="text-[11px] text-muted-foreground uppercase tracking-widest">
          {hasData ? `Analyzing ${analytics?.filteredRowCount || 0} data points` : "Upload data to activate models"}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-5">
        <button
          onClick={() => setActiveTab("models")}
          className={`px-4 py-2 text-[11px] font-medium rounded-md transition-all ${
            activeTab === "models"
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          🤖 Models Overview
        </button>
        <button
          onClick={() => setActiveTab("metrics")}
          className={`px-4 py-2 text-[11px] font-medium rounded-md transition-all ${
            activeTab === "metrics"
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          📊 Classification Metrics
        </button>
        <button
          onClick={() => setActiveTab("comparison")}
          className={`px-4 py-2 text-[11px] font-medium rounded-md transition-all ${
            activeTab === "comparison"
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          📈 Model Comparison
        </button>
      </div>

      {/* Loading indicator for metrics */}
      {metricsLoading && (
        <div className="text-center py-4 text-[11px] text-muted-foreground">
          Loading metrics...
        </div>
      )}

      {/* Models Tab */}
      {activeTab === "models" && (
        <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
          {/* Anomaly Detection */}
          <ModelCard icon="🔍" iconBg="bg-primary/10" name="Anomaly Detection" algo="Isolation Forest · SHAP importance when available"
            statusText={mlReady ? `Trained · ${anomalyRate}% flagged` : hasData ? "Waiting for ML pipeline" : undefined}
            metrics={[
              { val: mlReady ? `${anomalyRate}%` : "—", label: "Flagged Rate", color: COLORS.accent },
              { val: mlReady ? "5%" : "—", label: "Configured contamination", color: COLORS.accent },
              { val: "—", label: "Precision (needs labels)", color: COLORS.accent },
            ]}>
            <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2.5">SHAP feature importance</div>
          {shapFeatures.length > 0 ? (
              <div className="flex flex-col gap-2">
                {shapFeatures.map(f => ({ name: f.feature, val: f.importance })).map((f) => (
                  <div key={f.name} className="flex items-center gap-2.5">
                    <div className="w-[180px] text-[11px] text-muted-foreground text-right shrink-0">{f.name}</div>
                    <div className="flex-1 h-2 bg-bg3 rounded overflow-hidden">
                      <div className="h-full rounded bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
                        style={{ width: `${Math.min(100, (f.val / (shapFeatures.length > 0 ? Math.max(...shapFeatures.map(x => x.importance)) + 0.001 : 1)) * 100)}%` }} />
                    </div>
                    <div className="w-10 text-[11px] text-primary text-right shrink-0">{f.val.toFixed(3)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyChartState message="Run the ML pipeline to calculate feature importance" />
            )}
          </ModelCard>

          {/* Demand Forecasting */}
          <ModelCard icon="📈" iconBg="bg-secondary/10" name="Demand Forecasting" algo="Tree-based regression · recursive lag/rolling features"
            statusText={mlReady ? "Forecast model trained" : hasData ? "Waiting for ML pipeline" : undefined}
            metrics={[
              {
                // FIX: was `(peakUsage || 0 - averageUsage)` — operator precedence bug. Now correctly: (peak - avg) * 0.08
                val: mlReady && typeof mlModels.mae === "number"
                  ? mlModels.mae.toFixed(1)
                  : "—",
                label: "Rolling Holdout MAE (kWh)", color: COLORS.accent2,
              },
              {
                val: mlReady && typeof mlModels.mape === "number"
                  ? `${mlModels.mape.toFixed(1)}%`
                  : "—",
                label: "Rolling Holdout MAPE", color: COLORS.accent2,
              },
              { val: mlReady ? "24h" : "—", label: "Horizon", color: COLORS.accent2 },
            ]}>
            <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">24-hour forecast · approximate validation-residual range</div>
            {forecastData.length > 0 ? (
              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={forecastData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="time" tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }} interval={Math.max(1, Math.floor(forecastData.length / 6))} />
                  <YAxis tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }} />
                  <Tooltip {...tooltipStyle} />
                  <Area type="monotone" dataKey="residualRange" stroke="none" fill={COLORS.accent2} fillOpacity={0.14} isAnimationActive={false} />
                  <Line type="monotone" dataKey="value" stroke={COLORS.accent2} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChartState message="Run the ML pipeline to generate a forecast" />
            )}
          </ModelCard>

          {/* Predictive Maintenance */}
          <ModelCard icon="🔧" iconBg="bg-warn/10" name="Predictive Maintenance" algo="Gradient Boosting · 3-class classifier"
            statusText={mlReady ? `Predictions for ${maintData.reduce((sum, item) => sum + item.value, 0).toLocaleString()} readings` : hasData ? "Waiting for ML pipeline" : undefined}
            metrics={[
              { val: mlReady && typeof mlModels.maintenanceAccuracy === "number" ? `${mlModels.maintenanceAccuracy.toFixed(1)}%` : "—", label: "Holdout Accuracy", color: COLORS.warn },
              { val: mlReady && typeof mlModels.maintenanceF1 === "number" ? `${mlModels.maintenanceF1.toFixed(1)}%` : "—", label: "Holdout Weighted F1", color: COLORS.warn },
              { val: mlReady ? (String(mlModels.maintenanceLabelSource || "").startsWith("uploaded:") ? "Uploaded" : "Generated") : "—", label: "Label Source", color: COLORS.warn },
            ]}>
            {mlReady && (
              <p className="mb-3 text-[10px] leading-relaxed text-warn">
                {mlModels.maintenanceLabelSource === "rule_generated"
                  ? "Evaluation labels were generated from signal rules; these scores do not verify real equipment outcomes."
                  : "Holdout scores compare predictions with uploaded labels; their validity depends on label quality."}
              </p>
            )}
            <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">Predicted health class distribution</div>
            {maintData.length > 0 ? (
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={maintData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis type="number" tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }} width={60} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {maintData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChartState message="Run the ML pipeline for maintenance predictions" />
            )}
          </ModelCard>

          {/* Efficiency Scoring */}
          <ModelCard icon="🎯" iconBg="bg-destructive/10" name="Efficiency Scoring" algo="K-Means Clustering · Percentile ranking"
            statusText={mlReady ? "Clusters fitted to uploaded readings" : hasData ? "Waiting for ML pipeline" : undefined}
            metrics={[
              {
                // FIX: was hardcoded "0.62" — now reads real silhouette from backend
                val: mlReady && typeof mlModels.silhouetteScore === "number"
                  ? mlModels.silhouetteScore.toFixed(3)
                  : "—",
                label: "Training silhouette", color: COLORS.danger,
              },
              {
                // FIX: was hardcoded "4" — now reads real cluster count from backend
                val: mlReady && typeof mlModels.nClusters === "number"
                  ? String(mlModels.nClusters)
                  : "—",
                label: "Clusters", color: COLORS.danger,
              },
              { val: mlReady && typeof mlModels.avgEfficiencyScore === "number" ? `${mlModels.avgEfficiencyScore.toFixed(1)}` : "—", label: "Avg Score", color: COLORS.danger },
            ]}>
            <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">Cluster size breakdown</div>
            {clusterData.length > 0 && clusterData.some((d) => d.value > 0) ? (
              <ResponsiveContainer width="100%" height={120}>
                <PieChart>
                  <Pie data={clusterData} cx="50%" cy="50%" outerRadius={45} dataKey="value" stroke="#0f1519" strokeWidth={3}>
                    {clusterData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                  <Legend iconSize={8} wrapperStyle={{ fontFamily: "Space Mono", fontSize: 9, color: COLORS.muted }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChartState message="Run the ML pipeline for cluster analysis" />
            )}
          </ModelCard>
        </div>
      )}

      {/* Classification Metrics Tab */}
      {activeTab === "metrics" && (
        <div className="space-y-4">
          {mlReady && (
            <p className="rounded-md border border-border bg-card px-3 py-2 text-[11px] text-muted-foreground">
              Classification charts use held-out rows. {mlModels.maintenanceLabelSource === "rule_generated"
                ? "Labels were generated from signal rules, so these charts measure agreement with those rules rather than verified equipment outcomes."
                : "Scores compare predictions with the uploaded labels and depend on their quality."}
            </p>
          )}
          <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
            {/* Confusion Matrix */}
            <ConfusionMatrix
              matrix={confusionMatrix?.confusion_matrix || null}
              matrixNormalized={confusionMatrix?.confusion_matrix_normalized || null}
              classes={confusionMatrix?.classes || ["healthy", "warning", "critical"]}
              showNormalized={false}
              title="Confusion Matrix"
              subtitle="Maintenance classification results"
            />

            {/* Feature Importance */}
            <FeatureImportanceChart
              shapImportance={featureImportance?.shap_importance || null}
              modelImportance={featureImportance?.model_importance || null}
              pcaVariance={featureImportance?.pca_analysis?.scree_plot || null}
              title="Feature Analysis"
              subtitle="SHAP when available · model importance · PCA"
            />
          </div>

          <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
            {/* ROC Curves */}
            <RocCurveChart
              curves={rocCurves?.curves || null}
              aucScores={rocCurves?.auc_scores}
              macroAuc={rocCurves?.macro_auc}
              title="ROC Curves"
              subtitle="Receiver Operating Characteristic"
            />

            {/* Precision-Recall Curves */}
            <PrecisionRecallChart
              curves={precisionRecall?.curves || null}
              apScores={precisionRecall?.ap_scores}
              macroAp={precisionRecall?.macro_ap}
              title="Precision-Recall"
              subtitle="Classification trade-off analysis"
            />
          </div>

          {/* Per-class metrics */}
          {confusionMatrix?.per_class_metrics && (
            <div className="bg-card border border-border rounded-lg p-5">
              <div className="font-head text-sm font-bold mb-1">Per-Class Metrics</div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-4">
                Detailed metrics for each classification class
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-3 text-muted-foreground">Class</th>
                      <th className="text-right py-2 px-3 text-muted-foreground">Precision</th>
                      <th className="text-right py-2 px-3 text-muted-foreground">Recall</th>
                      <th className="text-right py-2 px-3 text-muted-foreground">F1-Score</th>
                      <th className="text-right py-2 px-3 text-muted-foreground">Support</th>
                    </tr>
                  </thead>
                  <tbody>
                    {confusionMatrix.classes.map((cls, idx) => (
                      <tr key={cls} className="border-b border-border/30">
                        <td className="py-2 px-3 font-medium capitalize">{cls}</td>
                        <td className="py-2 px-3 text-right font-mono">
                          {confusionMatrix.per_class_metrics.precision[idx]?.toFixed(4) || "—"}
                        </td>
                        <td className="py-2 px-3 text-right font-mono">
                          {confusionMatrix.per_class_metrics.recall[idx]?.toFixed(4) || "—"}
                        </td>
                        <td className="py-2 px-3 text-right font-mono">
                          {confusionMatrix.per_class_metrics.f1_score[idx]?.toFixed(4) || "—"}
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-muted-foreground">
                          {confusionMatrix.per_class_metrics.support[idx] || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Model Comparison Tab */}
      {activeTab === "comparison" && (
        <div className="space-y-4">
          {/* Model Comparison Chart */}
          <ModelComparisonChart
            barData={comparisonBarData}
            radarData={modelComparison?.radar_chart_data || null}
            taskType="regression"
            title="Forecasting Model Comparison"
            subtitle="Compare performance across different models"
          />

          {/* Metrics Table */}
          <MetricsTable
            data={metricsTableData}
            title="Detailed Metrics Table"
            subtitle="Sortable comparison with best value highlighting"
          />

          {/* Model Rankings */}
          {modelComparison?.rankings && Object.keys(modelComparison.rankings).length > 0 && (
            <div className="bg-card border border-border rounded-lg p-5">
              <div className="font-head text-sm font-bold mb-1">Model Rankings</div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-4">
                Best model for each metric
              </div>
              <div className="grid grid-cols-4 gap-4 max-md:grid-cols-2">
                {Object.entries(modelComparison.rankings).map(([metric, rankings]) => (
                  <div key={metric} className="bg-bg3 rounded-lg p-3">
                    <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">
                      {metric.toUpperCase()}
                    </div>
                    {rankings.slice(0, 3).map((item, idx) => (
                      <div
                        key={item.model}
                        className={`flex items-center justify-between text-[11px] py-1 ${
                          idx === 0 ? "text-accent2 font-bold" : "text-muted-foreground"
                        }`}
                      >
                        <span>#{item.rank} {item.model}</span>
                        <span className="font-mono">{item.value.toFixed(4)}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Best Model Summary */}
          {modelComparison?.best_model && (
            <div className="bg-card border border-accent2/30 rounded-lg p-5 text-center">
              <div className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">
                Best Overall Model
              </div>
              <div className="font-head text-xl font-extrabold text-accent2">
                {modelComparison.best_model}
              </div>
              <div className="text-[11px] text-muted-foreground mt-1">
                Based on primary metric comparison
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelsPage;

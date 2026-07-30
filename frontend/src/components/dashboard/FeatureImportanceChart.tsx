// src/components/dashboard/FeatureImportanceChart.tsx
// Horizontal bar chart for feature importances and PCA variance

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
} from "recharts";
import ChartCard from "./ChartCard";
import EmptyChartState from "./EmptyChartState";

const COLORS = {
  accent: "#00e5ff",
  accent2: "#00ff9d",
  warn: "#ffb800",
  danger: "#ff3d5a",
  muted: "#5a7a8a",
  bg3: "#141c21",
  border: "#1e2d35",
};

interface FeatureImportance {
  feature: string;
  importance: number;
}

interface PcaVariance {
  component: string;
  individual: number;
  cumulative: number;
}

interface FeatureImportanceChartProps {
  shapImportance?: FeatureImportance[] | null;
  modelImportance?: FeatureImportance[] | null;
  pcaVariance?: PcaVariance[] | null;
  title?: string;
  subtitle?: string;
}

const tooltipStyle = {
  contentStyle: {
    background: "#0f1519",
    border: "1px solid #1e2d35",
    borderRadius: 8,
    fontFamily: "Space Mono",
    fontSize: 11,
  },
  labelStyle: { fontFamily: "Syne", fontWeight: 700, color: "#e2eef5" },
};

const FeatureImportanceChart = ({
  shapImportance,
  modelImportance,
  pcaVariance,
  title = "Feature Importance",
  subtitle = "Model interpretability analysis",
}: FeatureImportanceChartProps) => {
  const [viewMode, setViewMode] = useState<"shap" | "model" | "pca">("shap");

  const hasShap = shapImportance && shapImportance.length > 0;
  const hasModel = modelImportance && modelImportance.length > 0;
  const hasPca = pcaVariance && pcaVariance.length > 0;

  const hasAnyData = hasShap || hasModel || hasPca;

  if (!hasAnyData) {
    return (
      <ChartCard title={title} subtitle={subtitle}>
        <EmptyChartState message="Run Analytics to see feature importance" />
      </ChartCard>
    );
  }

  // Normalize importance values for display
  const normalizeImportance = (data: FeatureImportance[]) => {
    const maxVal = Math.max(...data.map((d) => d.importance));
    return data.map((d) => ({
      ...d,
      normalized: maxVal > 0 ? (d.importance / maxVal) * 100 : 0,
    }));
  };

  const currentData =
    viewMode === "shap" && hasShap
      ? normalizeImportance(shapImportance!)
      : viewMode === "model" && hasModel
      ? normalizeImportance(modelImportance!)
      : null;

  return (
    <ChartCard title={title} subtitle={subtitle}>
      <div className="flex flex-col">
        {/* View mode toggle */}
        <div className="flex justify-center gap-2 mb-4">
          {hasShap && (
            <button
              onClick={() => setViewMode("shap")}
              className={`px-3 py-1 text-[10px] rounded-md transition-all ${
                viewMode === "shap"
                  ? "bg-primary text-primary-foreground"
                  : "bg-bg3 text-muted-foreground hover:text-foreground"
              }`}
            >
              SHAP
            </button>
          )}
          {hasModel && (
            <button
              onClick={() => setViewMode("model")}
              className={`px-3 py-1 text-[10px] rounded-md transition-all ${
                viewMode === "model"
                  ? "bg-primary text-primary-foreground"
                  : "bg-bg3 text-muted-foreground hover:text-foreground"
              }`}
            >
              Model Importance
            </button>
          )}
          {hasPca && (
            <button
              onClick={() => setViewMode("pca")}
              className={`px-3 py-1 text-[10px] rounded-md transition-all ${
                viewMode === "pca"
                  ? "bg-primary text-primary-foreground"
                  : "bg-bg3 text-muted-foreground hover:text-foreground"
              }`}
            >
              PCA Variance
            </button>
          )}
        </div>

        {viewMode !== "pca" && currentData ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={currentData.slice(0, 12)}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="feature"
                tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }}
                width={95}
              />
              <Tooltip
                {...tooltipStyle}
                formatter={(value: number, name: string, props: unknown) => {
                  const payload = (props as { payload?: { importance: number } }).payload;
                  return [
                    `${payload?.importance.toFixed(4)} (${value.toFixed(1)}%)`,
                    viewMode === "shap" ? "SHAP Value" : "Importance",
                  ];
                }}
              />
              <Bar
                dataKey="normalized"
                fill={viewMode === "shap" ? COLORS.accent : COLORS.accent2}
                radius={[0, 4, 4, 0]}
                name="Importance"
              />
            </BarChart>
          </ResponsiveContainer>
        ) : hasPca ? (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart
              data={pcaVariance}
              margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
              <XAxis
                dataKey="component"
                tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }}
                tickFormatter={(v) => `${v}%`}
                label={{
                  value: "Variance Explained (%)",
                  angle: -90,
                  position: "insideLeft",
                  fill: COLORS.muted,
                  fontSize: 10,
                }}
              />
              <Tooltip
                {...tooltipStyle}
                formatter={(value: number, name: string) => [
                  `${value.toFixed(2)}%`,
                  name === "individual" ? "Individual" : "Cumulative",
                ]}
              />
              <Area
                type="monotone"
                dataKey="cumulative"
                fill={COLORS.accent}
                fillOpacity={0.2}
                stroke={COLORS.accent}
                strokeWidth={2}
                name="Cumulative"
              />
              <Bar
                dataKey="individual"
                fill={COLORS.accent2}
                radius={[4, 4, 0, 0]}
                name="Individual"
              />
              <Line
                type="monotone"
                dataKey="cumulative"
                stroke={COLORS.accent}
                strokeWidth={2}
                dot={{ fill: COLORS.accent, r: 4 }}
                name="Cumulative"
              />
            </ComposedChart>
          </ResponsiveContainer>
        ) : null}

        {/* Info text */}
        <div className="text-[9px] text-muted-foreground text-center mt-3">
          {viewMode === "shap"
            ? "SHAP values measure the impact of each feature on model predictions"
            : viewMode === "model"
            ? "Feature importance from tree-based model splits"
            : "Principal components sorted by explained variance ratio"}
        </div>

        {/* Top features summary */}
        {currentData && viewMode !== "pca" && (
          <div className="flex flex-wrap gap-2 mt-3 justify-center">
            {currentData.slice(0, 5).map((item, idx) => (
              <div
                key={item.feature}
                className="flex items-center gap-1.5 bg-bg3 rounded-md px-2 py-1"
              >
                <span className="text-[9px] font-mono text-muted-foreground">#{idx + 1}</span>
                <span className="text-[10px] text-foreground">{item.feature}</span>
              </div>
            ))}
          </div>
        )}

        {hasPca && viewMode === "pca" && pcaVariance && (
          <div className="flex items-center gap-4 mt-3 justify-center text-[10px]">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS.accent2 }} />
              <span className="text-muted-foreground">Individual variance</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS.accent }} />
              <span className="text-muted-foreground">Cumulative variance</span>
            </div>
          </div>
        )}
      </div>
    </ChartCard>
  );
};

export default FeatureImportanceChart;

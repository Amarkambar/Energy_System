// src/components/dashboard/ModelComparisonChart.tsx
// Bar chart and radar chart for model comparison

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
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

const MODEL_COLORS = [COLORS.accent, COLORS.accent2, COLORS.warn, COLORS.danger];

interface ModelMetrics {
  model: string;
  mae?: number;
  rmse?: number;
  r2?: number;
  mape?: number;
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1_score?: number;
}

interface RadarDataset {
  model: string;
  values: number[];
}

interface RadarChartData {
  labels: string[];
  datasets: RadarDataset[];
}

interface ModelComparisonChartProps {
  barData: ModelMetrics[] | null;
  radarData?: RadarChartData | null;
  taskType?: "regression" | "classification";
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

const ModelComparisonChart = ({
  barData,
  radarData,
  taskType = "regression",
  title = "Model Comparison",
  subtitle = "Performance metrics across models",
}: ModelComparisonChartProps) => {
  const [viewMode, setViewMode] = useState<"bar" | "radar">("bar");

  if (!barData || barData.length === 0) {
    return (
      <ChartCard title={title} subtitle={subtitle}>
        <EmptyChartState message="Run Analytics to see model comparison" />
      </ChartCard>
    );
  }

  // Determine which metrics to show based on task type
  const regressionMetrics = ["mae", "rmse", "mape", "r2"];
  const classificationMetrics = ["accuracy", "precision", "recall", "f1_score"];
  const metricsToShow = taskType === "regression" ? regressionMetrics : classificationMetrics;

  // Filter metrics that exist in the data
  const availableMetrics = metricsToShow.filter((metric) =>
    barData.some((d) => d[metric as keyof ModelMetrics] !== undefined)
  );

  // Prepare radar chart data
  const radarChartData = availableMetrics.map((metric) => {
    const point: Record<string, unknown> = { metric: metric.toUpperCase() };
    barData.forEach((model, idx) => {
      let value = model[metric as keyof ModelMetrics] as number;
      // Normalize for radar chart (0-1 scale)
      if (metric === "mape") {
        value = Math.max(0, 1 - value / 100); // Lower is better
      } else if (metric === "mae" || metric === "rmse") {
        // Normalize based on max value
        const maxVal = Math.max(...barData.map((d) => (d[metric as keyof ModelMetrics] as number) || 0));
        value = maxVal > 0 ? 1 - value / maxVal : 0;
      }
      point[model.model] = value || 0;
    });
    return point;
  });

  return (
    <ChartCard title={title} subtitle={subtitle}>
      <div className="flex flex-col">
        {/* View mode toggle */}
        <div className="flex justify-center gap-2 mb-4">
          <button
            onClick={() => setViewMode("bar")}
            className={`px-3 py-1 text-[10px] rounded-md transition-all ${
              viewMode === "bar"
                ? "bg-primary text-primary-foreground"
                : "bg-bg3 text-muted-foreground hover:text-foreground"
            }`}
          >
            Bar Chart
          </button>
          <button
            onClick={() => setViewMode("radar")}
            className={`px-3 py-1 text-[10px] rounded-md transition-all ${
              viewMode === "radar"
                ? "bg-primary text-primary-foreground"
                : "bg-bg3 text-muted-foreground hover:text-foreground"
            }`}
          >
            Radar Chart
          </button>
        </div>

        {viewMode === "bar" ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={barData}
              margin={{ top: 10, right: 30, left: 10, bottom: 50 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
              <XAxis
                dataKey="model"
                tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }}
                angle={0}
                textAnchor="middle"
                interval={0}
              />
              <YAxis
                tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }}
              />
              <Tooltip {...tooltipStyle} />
              <Legend
                wrapperStyle={{
                  fontFamily: "Space Mono",
                  fontSize: 9,
                  color: COLORS.muted,
                }}
              />
              {availableMetrics.map((metric, idx) => (
                <Bar
                  key={metric}
                  dataKey={metric}
                  name={metric.toUpperCase()}
                  fill={MODEL_COLORS[idx % MODEL_COLORS.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarChartData} cx="50%" cy="50%" outerRadius="70%">
              <PolarGrid stroke={COLORS.border} />
              <PolarAngleAxis
                dataKey="metric"
                tick={{ fill: COLORS.muted, fontSize: 9, fontFamily: "Space Mono" }}
              />
              <PolarRadiusAxis
                tick={{ fill: COLORS.muted, fontSize: 8 }}
                domain={[0, 1]}
              />
              {barData.map((model, idx) => (
                <Radar
                  key={model.model}
                  name={model.model}
                  dataKey={model.model}
                  stroke={MODEL_COLORS[idx % MODEL_COLORS.length]}
                  fill={MODEL_COLORS[idx % MODEL_COLORS.length]}
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              ))}
              <Legend
                wrapperStyle={{
                  fontFamily: "Space Mono",
                  fontSize: 9,
                  color: COLORS.muted,
                }}
              />
              <Tooltip {...tooltipStyle} />
            </RadarChart>
          </ResponsiveContainer>
        )}

        {/* Metrics summary table */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2 text-muted-foreground font-medium">Model</th>
                {availableMetrics.map((metric) => (
                  <th key={metric} className="text-right py-2 px-2 text-muted-foreground font-medium">
                    {metric.toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {barData.map((model, idx) => (
                <tr key={model.model} className="border-b border-border/50">
                  <td className="py-2 px-2 font-mono" style={{ color: MODEL_COLORS[idx % MODEL_COLORS.length] }}>
                    {model.model}
                  </td>
                  {availableMetrics.map((metric) => {
                    const value = model[metric as keyof ModelMetrics];
                    const isR2OrAccuracy = metric === "r2" || metric === "accuracy";
                    return (
                      <td key={metric} className="text-right py-2 px-2 font-mono">
                        {value !== undefined ? (
                          <span className={isR2OrAccuracy && (value as number) > 0.9 ? "text-accent2" : ""}>
                            {typeof value === "number" ? value.toFixed(4) : value}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </ChartCard>
  );
};

export default ModelComparisonChart;

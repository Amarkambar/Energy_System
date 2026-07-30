// src/components/dashboard/RocCurveChart.tsx
// ROC curve visualization with AUC values

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
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

const CLASS_COLORS = [COLORS.accent, COLORS.accent2, COLORS.warn, COLORS.danger, "#9c27b0"];

interface RocCurve {
  class: string;
  fpr: number[];
  tpr: number[];
  auc: number;
}

interface RocCurveChartProps {
  curves: RocCurve[] | null;
  aucScores?: Record<string, number>;
  macroAuc?: number;
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

const RocCurveChart = ({
  curves,
  aucScores,
  macroAuc,
  title = "ROC Curves",
  subtitle = "Receiver Operating Characteristic",
}: RocCurveChartProps) => {
  if (!curves || curves.length === 0) {
    return (
      <ChartCard title={title} subtitle={subtitle}>
        <EmptyChartState message="Run classification model to see ROC curves" />
      </ChartCard>
    );
  }

  // Transform curve data for Recharts
  // Combine all curves into one dataset with proper sampling
  const chartData: Record<string, unknown>[] = [];
  
  // Create unified x-axis points
  const fprPoints = new Set<number>();
  curves.forEach((curve) => {
    curve.fpr.forEach((f) => fprPoints.add(f));
  });
  
  const sortedFpr = Array.from(fprPoints).sort((a, b) => a - b);
  
  // Sample points for smoother chart
  const sampleStep = Math.max(1, Math.floor(sortedFpr.length / 50));
  const sampledFpr = sortedFpr.filter((_, i) => i % sampleStep === 0 || i === sortedFpr.length - 1);
  
  sampledFpr.forEach((fpr) => {
    const point: Record<string, unknown> = { fpr: fpr };
    
    curves.forEach((curve, idx) => {
      // Interpolate TPR for this FPR value
      const fprIdx = curve.fpr.findIndex((f) => f >= fpr);
      if (fprIdx >= 0) {
        point[`tpr_${curve.class}`] = curve.tpr[fprIdx];
      }
    });
    
    chartData.push(point);
  });

  // Ensure diagonal line data
  const diagonalData = [
    { fpr: 0, diagonal: 0 },
    { fpr: 1, diagonal: 1 },
  ];

  return (
    <ChartCard
      title={title}
      subtitle={subtitle}
      titleRight={macroAuc ? `Macro AUC: ${macroAuc.toFixed(3)}` : undefined}
    >
      <div className="flex flex-col">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
            <XAxis
              dataKey="fpr"
              type="number"
              domain={[0, 1]}
              tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }}
              label={{
                value: "False Positive Rate",
                position: "bottom",
                fill: COLORS.muted,
                fontSize: 10,
              }}
            />
            <YAxis
              type="number"
              domain={[0, 1]}
              tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }}
              label={{
                value: "True Positive Rate",
                angle: -90,
                position: "insideLeft",
                fill: COLORS.muted,
                fontSize: 10,
              }}
            />
            <Tooltip
              {...tooltipStyle}
              formatter={(value: number, name: string) => [
                value.toFixed(3),
                name.replace("tpr_", ""),
              ]}
            />
            <Legend
              wrapperStyle={{
                fontFamily: "Space Mono",
                fontSize: 10,
                color: COLORS.muted,
              }}
              formatter={(value) => value.replace("tpr_", "")}
            />
            
            {/* Diagonal reference line (random classifier) */}
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
              stroke={COLORS.muted}
              strokeDasharray="5 5"
              strokeWidth={1}
            />
            
            {/* ROC curves for each class */}
            {curves.map((curve, idx) => (
              <Line
                key={curve.class}
                type="monotone"
                dataKey={`tpr_${curve.class}`}
                stroke={CLASS_COLORS[idx % CLASS_COLORS.length]}
                strokeWidth={2}
                dot={false}
                name={`${curve.class} (AUC: ${curve.auc.toFixed(3)})`}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>

        {/* AUC Summary */}
        <div className="flex flex-wrap gap-3 mt-3 justify-center">
          {curves.map((curve, idx) => (
            <div
              key={curve.class}
              className="flex items-center gap-2 bg-bg3 rounded-md px-3 py-1.5"
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: CLASS_COLORS[idx % CLASS_COLORS.length] }}
              />
              <span className="text-[10px] text-muted-foreground">{curve.class}</span>
              <span
                className="text-[11px] font-bold font-mono"
                style={{ color: CLASS_COLORS[idx % CLASS_COLORS.length] }}
              >
                {curve.auc.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </ChartCard>
  );
};

export default RocCurveChart;

// src/components/dashboard/PrecisionRecallChart.tsx
// Precision-Recall curve visualization with Average Precision values

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
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

interface PrCurve {
  class: string;
  precision: number[];
  recall: number[];
  ap: number;
}

interface PrecisionRecallChartProps {
  curves: PrCurve[] | null;
  apScores?: Record<string, number>;
  macroAp?: number;
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

const PrecisionRecallChart = ({
  curves,
  apScores,
  macroAp,
  title = "Precision-Recall Curves",
  subtitle = "Precision vs Recall Trade-off",
}: PrecisionRecallChartProps) => {
  if (!curves || curves.length === 0) {
    return (
      <ChartCard title={title} subtitle={subtitle}>
        <EmptyChartState message="Run classification model to see PR curves" />
      </ChartCard>
    );
  }

  // Transform curve data for Recharts
  const chartData: Record<string, unknown>[] = [];
  
  // Create unified x-axis points (recall)
  const recallPoints = new Set<number>();
  curves.forEach((curve) => {
    curve.recall.forEach((r) => recallPoints.add(r));
  });
  
  const sortedRecall = Array.from(recallPoints).sort((a, b) => a - b);
  
  // Sample points for smoother chart
  const sampleStep = Math.max(1, Math.floor(sortedRecall.length / 50));
  const sampledRecall = sortedRecall.filter(
    (_, i) => i % sampleStep === 0 || i === sortedRecall.length - 1
  );
  
  sampledRecall.forEach((recall) => {
    const point: Record<string, unknown> = { recall };
    
    curves.forEach((curve) => {
      // Find closest recall value and get corresponding precision
      const recallIdx = curve.recall.findIndex((r) => r >= recall);
      if (recallIdx >= 0 && recallIdx < curve.precision.length) {
        point[`precision_${curve.class}`] = curve.precision[recallIdx];
      }
    });
    
    chartData.push(point);
  });

  return (
    <ChartCard
      title={title}
      subtitle={subtitle}
      titleRight={macroAp ? `Macro AP: ${macroAp.toFixed(3)}` : undefined}
    >
      <div className="flex flex-col">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
            <XAxis
              dataKey="recall"
              type="number"
              domain={[0, 1]}
              tick={{ fill: COLORS.muted, fontSize: 10, fontFamily: "Space Mono" }}
              label={{
                value: "Recall",
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
                value: "Precision",
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
                name.replace("precision_", ""),
              ]}
            />
            <Legend
              wrapperStyle={{
                fontFamily: "Space Mono",
                fontSize: 10,
                color: COLORS.muted,
              }}
              formatter={(value) => value.replace("precision_", "")}
            />
            
            {/* PR curves for each class */}
            {curves.map((curve, idx) => (
              <Line
                key={curve.class}
                type="stepAfter"
                dataKey={`precision_${curve.class}`}
                stroke={CLASS_COLORS[idx % CLASS_COLORS.length]}
                strokeWidth={2}
                dot={false}
                name={`${curve.class} (AP: ${curve.ap.toFixed(3)})`}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>

        {/* Average Precision Summary */}
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
                AP: {curve.ap.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
        
        {/* Info text */}
        <div className="text-[9px] text-muted-foreground text-center mt-2">
          Higher area under curve indicates better precision-recall trade-off
        </div>
      </div>
    </ChartCard>
  );
};

export default PrecisionRecallChart;

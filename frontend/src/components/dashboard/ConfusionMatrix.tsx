// src/components/dashboard/ConfusionMatrix.tsx
// Heatmap-style confusion matrix visualization

import { useMemo } from "react";
import ChartCard from "./ChartCard";
import EmptyChartState from "./EmptyChartState";

const COLORS = {
  accent: "#00e5ff",
  accent2: "#00ff9d",
  warn: "#ffb800",
  danger: "#ff3d5a",
  bg3: "#141c21",
  border: "#1e2d35",
  muted: "#5a7a8a",
};

interface ConfusionMatrixProps {
  matrix: number[][] | null;
  matrixNormalized?: number[][] | null;
  classes: string[];
  showNormalized?: boolean;
  title?: string;
  subtitle?: string;
}

const ConfusionMatrix = ({
  matrix,
  matrixNormalized,
  classes,
  showNormalized = false,
  title = "Confusion Matrix",
  subtitle = "Actual vs Predicted Classification",
}: ConfusionMatrixProps) => {
  const displayMatrix = showNormalized && matrixNormalized ? matrixNormalized : matrix;

  const { maxVal, colorScale } = useMemo(() => {
    if (!displayMatrix) return { maxVal: 1, colorScale: () => COLORS.bg3 };

    const flatValues = displayMatrix.flat();
    const max = Math.max(...flatValues);

    const colorScale = (value: number) => {
      const intensity = max > 0 ? value / max : 0;
      
      // Color gradient from bg3 (low) -> accent2 (diagonal/correct) -> danger (off-diagonal/errors)
      if (intensity < 0.3) {
        return COLORS.bg3;
      } else if (intensity < 0.6) {
        return `rgba(0, 229, 255, ${intensity})`;  // accent
      } else {
        return `rgba(0, 255, 157, ${intensity})`;  // accent2
      }
    };

    return { maxVal: max, colorScale };
  }, [displayMatrix]);

  if (!matrix || matrix.length === 0) {
    return (
      <ChartCard title={title} subtitle={subtitle}>
        <EmptyChartState message="Run classification model to see confusion matrix" />
      </ChartCard>
    );
  }

  const getCellColor = (rowIdx: number, colIdx: number, value: number) => {
    const intensity = maxVal > 0 ? value / maxVal : 0;
    
    // Diagonal cells (correct predictions) - green tones
    if (rowIdx === colIdx) {
      return `rgba(0, 255, 157, ${Math.max(0.2, intensity)})`;
    }
    // Off-diagonal cells (errors) - red tones for high values
    if (intensity > 0.3) {
      return `rgba(255, 61, 90, ${intensity * 0.8})`;
    }
    return `rgba(26, 45, 53, ${Math.max(0.3, intensity)})`;
  };

  return (
    <ChartCard title={title} subtitle={subtitle}>
      <div className="flex flex-col items-center">
        {/* Y-axis label */}
        <div className="flex items-center gap-4 w-full">
          <div className="text-[9px] text-muted-foreground uppercase tracking-widest -rotate-90 w-6">
            Actual
          </div>
          
          <div className="flex-1">
            {/* X-axis labels */}
            <div className="flex mb-2">
              <div className="w-16" /> {/* Spacer for row labels */}
              {classes.map((cls, idx) => (
                <div
                  key={`col-${idx}`}
                  className="flex-1 text-center text-[10px] text-muted-foreground font-mono truncate px-1"
                  title={cls}
                >
                  {cls.length > 8 ? cls.slice(0, 8) + "…" : cls}
                </div>
              ))}
            </div>

            {/* Matrix grid */}
            <div className="space-y-1">
              {displayMatrix.map((row, rowIdx) => (
                <div key={`row-${rowIdx}`} className="flex items-center gap-1">
                  {/* Row label */}
                  <div className="w-16 text-right text-[10px] text-muted-foreground font-mono truncate pr-2">
                    {classes[rowIdx]?.length > 8 
                      ? classes[rowIdx].slice(0, 8) + "…" 
                      : classes[rowIdx]}
                  </div>
                  
                  {/* Row cells */}
                  {row.map((value, colIdx) => (
                    <div
                      key={`cell-${rowIdx}-${colIdx}`}
                      className="flex-1 aspect-square flex items-center justify-center rounded-md transition-all duration-300 hover:scale-105 cursor-default"
                      style={{
                        backgroundColor: getCellColor(rowIdx, colIdx, value),
                        minHeight: "40px",
                        border: rowIdx === colIdx ? `1px solid ${COLORS.accent2}` : "1px solid transparent",
                      }}
                      title={`Actual: ${classes[rowIdx]}, Predicted: ${classes[colIdx]}, Count: ${
                        showNormalized ? `${(value * 100).toFixed(1)}%` : value
                      }`}
                    >
                      <span
                        className="font-mono text-xs font-bold"
                        style={{
                          color: value / maxVal > 0.5 ? "#fff" : COLORS.muted,
                        }}
                      >
                        {showNormalized ? `${(value * 100).toFixed(0)}%` : value}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            {/* X-axis label */}
            <div className="text-center text-[9px] text-muted-foreground uppercase tracking-widest mt-3">
              Predicted
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 text-[9px] text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: "rgba(0, 255, 157, 0.7)" }} />
            <span>Correct</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: "rgba(255, 61, 90, 0.5)" }} />
            <span>Error</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS.bg3 }} />
            <span>Low/None</span>
          </div>
        </div>
      </div>
    </ChartCard>
  );
};

export default ConfusionMatrix;

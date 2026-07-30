// src/components/dashboard/MetricsTable.tsx
// Sortable metrics table with best value highlighting

import { useState, useMemo } from "react";
import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
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

interface ModelMetric {
  model: string;
  mae?: number;
  rmse?: number;
  r2?: number;
  mape?: number;
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1_score?: number;
  training_time?: number;
  [key: string]: string | number | undefined;
}

interface MetricsTableProps {
  data: ModelMetric[] | null;
  title?: string;
  subtitle?: string;
}

type SortDirection = "asc" | "desc" | null;

interface ColumnConfig {
  key: string;
  label: string;
  lowerIsBetter: boolean;
  format: (val: number) => string;
}

const COLUMNS: ColumnConfig[] = [
  { key: "model", label: "Model", lowerIsBetter: false, format: (v) => String(v) },
  { key: "mae", label: "MAE", lowerIsBetter: true, format: (v) => v?.toFixed(4) || "—" },
  { key: "rmse", label: "RMSE", lowerIsBetter: true, format: (v) => v?.toFixed(4) || "—" },
  { key: "r2", label: "R²", lowerIsBetter: false, format: (v) => v?.toFixed(4) || "—" },
  { key: "mape", label: "MAPE (%)", lowerIsBetter: true, format: (v) => v?.toFixed(2) || "—" },
  { key: "accuracy", label: "Accuracy", lowerIsBetter: false, format: (v) => v?.toFixed(4) || "—" },
  { key: "f1_score", label: "F1-Score", lowerIsBetter: false, format: (v) => v?.toFixed(4) || "—" },
  { key: "training_time", label: "Time (s)", lowerIsBetter: true, format: (v) => v?.toFixed(2) || "—" },
];

const MetricsTable = ({
  data,
  title = "Model Metrics",
  subtitle = "Detailed performance comparison",
}: MetricsTableProps) => {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Filter columns that have data
  const visibleColumns = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    return COLUMNS.filter((col) => {
      if (col.key === "model") return true;
      return data.some((row) => row[col.key] !== undefined && row[col.key] !== null);
    });
  }, [data]);

  // Find best values for each column
  const bestValues = useMemo(() => {
    if (!data || data.length === 0) return {};
    
    const best: Record<string, number> = {};
    
    visibleColumns.forEach((col) => {
      if (col.key === "model") return;
      
      const values = data
        .map((row) => row[col.key])
        .filter((v): v is number => typeof v === "number" && !isNaN(v));
      
      if (values.length > 0) {
        best[col.key] = col.lowerIsBetter 
          ? Math.min(...values)
          : Math.max(...values);
      }
    });
    
    return best;
  }, [data, visibleColumns]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!data) return [];
    if (!sortKey || !sortDirection) return data;
    
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      
      if (aVal === undefined || aVal === null) return 1;
      if (bVal === undefined || bVal === null) return -1;
      
      const comparison = typeof aVal === "string" 
        ? aVal.localeCompare(bVal as string)
        : (aVal as number) - (bVal as number);
      
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [data, sortKey, sortDirection]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortKey(null);
        setSortDirection(null);
      }
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const getSortIcon = (key: string) => {
    if (sortKey !== key) {
      return <ArrowUpDown className="w-3 h-3 text-muted-foreground/50" />;
    }
    return sortDirection === "asc" 
      ? <ArrowUp className="w-3 h-3 text-primary" />
      : <ArrowDown className="w-3 h-3 text-primary" />;
  };

  if (!data || data.length === 0) {
    return (
      <ChartCard title={title} subtitle={subtitle}>
        <EmptyChartState message="Run Analytics to see model metrics" />
      </ChartCard>
    );
  }

  return (
    <ChartCard title={title} subtitle={subtitle}>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-border">
              {visibleColumns.map((col) => (
                <th
                  key={col.key}
                  className={`py-2.5 px-3 font-medium cursor-pointer hover:bg-bg3/50 transition-colors ${
                    col.key === "model" ? "text-left" : "text-right"
                  }`}
                  onClick={() => handleSort(col.key)}
                >
                  <div className={`flex items-center gap-1.5 ${col.key === "model" ? "" : "justify-end"}`}>
                    <span className="text-muted-foreground">{col.label}</span>
                    {getSortIcon(col.key)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row, rowIdx) => (
              <tr
                key={row.model}
                className="border-b border-border/30 hover:bg-bg3/30 transition-colors"
              >
                {visibleColumns.map((col) => {
                  const value = row[col.key];
                  const isBest = col.key !== "model" && 
                    typeof value === "number" && 
                    value === bestValues[col.key];
                  
                  return (
                    <td
                      key={col.key}
                      className={`py-2.5 px-3 font-mono ${
                        col.key === "model" ? "text-left font-sans font-medium" : "text-right"
                      }`}
                    >
                      {col.key === "model" ? (
                        <span className="text-foreground">{value}</span>
                      ) : (
                        <span
                          className={`${
                            isBest
                              ? "text-accent2 font-bold"
                              : "text-muted-foreground"
                          }`}
                        >
                          {value !== undefined && value !== null
                            ? col.format(value as number)
                            : "—"}
                          {isBest && (
                            <span className="ml-1 text-[8px] text-accent2 uppercase">★</span>
                          )}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 text-[9px] text-muted-foreground justify-center">
        <div className="flex items-center gap-1.5">
          <span className="text-accent2 font-bold">★</span>
          <span>Best value</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>Click column header to sort</span>
        </div>
      </div>
    </ChartCard>
  );
};

export default MetricsTable;

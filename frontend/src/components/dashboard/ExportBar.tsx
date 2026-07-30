import { Download, FileText, FileSpreadsheet } from "lucide-react";
import { useCsvData } from "@/lib/csv-context";

const ExportBar = () => {
  const { analytics, rawData, columns, fileName } = useCsvData();

  if (!analytics) return null;

  const exportCsv = () => {
    const header = columns.join(",");
    const rows = rawData.map((row) =>
      columns.map((col) => {
        const val = String(row[col] ?? "");
        return val.includes(",") || val.includes('"') ? `"${val.replace(/"/g, '""')}"` : val;
      }).join(",")
    );
    const csv = [header, ...rows].join("\n");
    downloadBlob(csv, "text/csv", `${(fileName || "export").replace(".csv", "")}_filtered.csv`);
  };

  const exportReport = () => {
    const a = analytics;
    const lines = [
      "═══════════════════════════════════════════",
      "  ENERGY DIAGNOSTICS REPORT",
      "═══════════════════════════════════════════",
      "",
      `Generated: ${new Date().toLocaleString()}`,
      `Source: ${fileName || "Unknown"}`,
      `Total Rows: ${a.rowCount}  |  Filtered: ${a.filteredRowCount}`,
      "",
      "── KEY METRICS ─────────────────────────────",
      `  Total Consumption:  ${a.totalConsumption.toLocaleString()} kWh`,
      `  Average Usage:      ${a.averageUsage.toLocaleString()} kWh`,
      `  Peak Usage:         ${a.peakUsage.toLocaleString()} kWh`,
      `  Minimum Usage:      ${a.minUsage.toLocaleString()} kWh`,
      `  Data Accuracy:      ${a.dataAccuracy}%`,
      `  Invalid Rows:       ${a.invalidRows}`,
      "",
    ];

    if (a.voltageTimeSeries.length > 0) {
      lines.push(
        "── VOLTAGE ─────────────────────────────────",
        `  Average Voltage:              ${a.avgVoltage} V`,
        `  Voltage Standard Deviation:   ${a.voltageDeviation} V`,
        `  Readings:                     ${a.voltageTimeSeries.length}`,
        ""
      );
    }

    lines.push(
      "── EFFICIENCY DISTRIBUTION ─────────────────",
      ...a.hourlyDistribution.map((d) => `  ${d.name.padEnd(14)} ${d.hours} readings`),
      "",
      "── DETECTED COLUMNS ───────────────────────",
      `  Time:        ${a.timeColumn || "Not detected"}`,
      `  Consumption: ${a.consumptionColumn || "Not detected"}`,
      `  Voltage:     ${a.voltageColumn || "Not detected"}`,
      "",
      "── DATE RANGE ─────────────────────────────",
      `  From: ${a.dateRange.min?.toLocaleString() || "N/A"}`,
      `  To:   ${a.dateRange.max?.toLocaleString() || "N/A"}`,
      "",
      "═══════════════════════════════════════════",
    );

    downloadBlob(lines.join("\n"), "text/plain", `${(fileName || "report").replace(".csv", "")}_report.txt`);
  };

  const downloadBlob = (content: string, type: string, name: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={exportCsv}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border text-[11px] font-head font-semibold text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
      >
        <FileSpreadsheet className="w-3.5 h-3.5 text-secondary" />
        Export CSV
      </button>
      <button
        onClick={exportReport}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border text-[11px] font-head font-semibold text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
      >
        <FileText className="w-3.5 h-3.5 text-primary" />
        Export Report
      </button>
    </div>
  );
};

export default ExportBar;

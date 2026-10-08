import { FileText, FileSpreadsheet } from "lucide-react";
import { useCsvData } from "@/lib/csv-context";

type ExportBarProps = {
  dateFrom?: Date;
  dateTo?: Date;
};

const escapeCsvField = (value: unknown) => {
  const text = String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
};

const ExportBar = ({ dateFrom, dateTo }: ExportBarProps) => {
  const { analytics, parsedRows, columns, fileName } = useCsvData();

  if (!analytics) return null;

  const exportCsv = () => {
    const endOfDay = dateTo ? new Date(dateTo) : null;
    endOfDay?.setHours(23, 59, 59, 999);
    const exportedRows = parsedRows.filter(({ date }) => {
      if (!date) return true;
      if (dateFrom && date < dateFrom) return false;
      if (endOfDay && date > endOfDay) return false;
      return true;
    });
    const records = exportedRows.map(({ raw }) => columns.map((column) => escapeCsvField(raw[column])));
    const csv = `\uFEFF${[columns.map(escapeCsvField).join(","), ...records.map((row) => row.join(","))].join("\r\n")}`;
    downloadBlob(csv, "text/csv;charset=utf-8", `${baseName(fileName, "export")}_filtered.csv`);
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

    downloadBlob(lines.join("\n"), "text/plain;charset=utf-8", `${baseName(fileName, "report")}_report.txt`);
  };

  const baseName = (name: string | null, fallback: string) =>
    (name || fallback).replace(/\.csv$/i, "").replace(/[\\/:*?"<>|]/g, "_");

  const downloadBlob = (content: string, type: string, name: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
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

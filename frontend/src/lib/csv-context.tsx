import { createContext, useContext, useState, useCallback, useMemo, ReactNode, useRef } from "react";
import Papa from "papaparse";

export interface CsvRow {
  [key: string]: string | number | null;
}

export interface ParsedRow {
  raw: CsvRow;
  date: Date | null;
  consumption: number | null;
  voltage: number | null;
  timeLabel: string;
}

export interface AnalyticsResult {
  totalConsumption: number;
  averageUsage: number;
  peakUsage: number;
  minUsage: number;
  dataAccuracy: number;
  invalidRows: number;
  rowCount: number;
  filteredRowCount: number;
  columnNames: string[];
  consumptionColumn: string | null;
  voltageColumn: string | null;
  timeColumn: string | null;
  consumptionTimeSeries: { time: string; value: number }[];
  voltageTimeSeries: { time: string; voltage: number; nominal: number }[];
  hourlyDistribution: { name: string; hours: number; color: string }[];
  anomalyData: { range: string; count: number; color: string }[];
  dateRange: { min: Date | null; max: Date | null };
  avgVoltage: number;
  voltageDeviation: number;
}

interface CsvContextType {
  rawData: CsvRow[];
  parsedRows: ParsedRow[];
  fileName: string | null;
  analytics: AnalyticsResult | null;
  status: "idle" | "uploading" | "analyzing" | "ready" | "error";
  error: string | null;
  uploadCsv: (file: File) => void;
  runAnalytics: (dateFrom?: Date | null, dateTo?: Date | null) => void;
  clearData: () => void;
  autoRefresh: boolean;
  setAutoRefresh: (v: boolean) => void;
  columns: string[];
}

const CsvContext = createContext<CsvContextType | null>(null);

export const useCsvData = () => {
  const ctx = useContext(CsvContext);
  if (!ctx) throw new Error("useCsvData must be used within CsvProvider");
  return ctx;
};

const COLORS = {
  accent: "#00e5ff",
  accent2: "#00ff9d",
  warn: "#ffb800",
  danger: "#ff3d5a",
};

function guessColumn(columns: string[], hints: string[]): string | null {
  const lower = columns.map((c) => c.toLowerCase().replace(/[^a-z0-9]/g, ""));
  for (const hint of hints) {
    const idx = lower.findIndex((c) => c.includes(hint));
    if (idx >= 0) return columns[idx];
  }
  return null;
}

function normalizeNumber(val: string | number | null): number | null {
  if (val == null) return null;
  if (typeof val === "number") return Number.isFinite(val) ? val : null;

  const raw = String(val).trim();
  if (!raw) return null;

  const cleaned = raw.replace(/[^0-9,.-]/g, "");
  if (!cleaned) return null;

  const hasComma = cleaned.includes(",");
  const hasDot = cleaned.includes(".");

  let normalized = cleaned;

  if (hasComma && hasDot) {
    normalized = cleaned.lastIndexOf(",") > cleaned.lastIndexOf(".")
      ? cleaned.replace(/\./g, "").replace(",", ".")
      : cleaned.replace(/,/g, "");
  } else if (hasComma && !hasDot) {
    const commaCount = (cleaned.match(/,/g) || []).length;
    normalized = commaCount === 1 ? cleaned.replace(",", ".") : cleaned.replace(/,/g, "");
  }

  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function tryParseDate(val: string | number | null): Date | null {
  if (val == null) return null;
  const s = String(val).trim();
  if (!s) return null;
  const d = new Date(s);
  if (!isNaN(d.getTime())) return d;
  const parts = s.match(/(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})/);
  if (parts) {
    const a = parseInt(parts[1]), b = parseInt(parts[2]), c = parseInt(parts[3]);
    if (a > 31) return new Date(a, b - 1, c);
    if (c > 31) return new Date(c, b - 1, a);
    return new Date(c, a - 1, b);
  }
  return null;
}

function scoreNumericColumn(data: CsvRow[], column: string): number {
  const sample = data.slice(0, 50);
  let valid = 0;
  let positive = 0;

  for (const row of sample) {
    const n = normalizeNumber(row[column]);
    if (n !== null) {
      valid += 1;
      if (n >= 0) positive += 1;
    }
  }

  return sample.length === 0 ? 0 : valid / sample.length + positive / Math.max(1, valid) * 0.1;
}

function inferColumns(data: CsvRow[], columns: string[]) {
  const timeCol = guessColumn(columns, ["time", "timestamp", "date", "datetime", "hour", "period"]);
  let consumptionCol = guessColumn(columns, ["consumption", "kwh", "energy", "usage", "power", "load", "demand", "reading", "value"]);
  let voltageCol = guessColumn(columns, ["voltage", "volt", "v_rms", "vrms"]);

  const numericCandidates = columns
    .filter((col) => col !== timeCol)
    .map((col) => ({ col, score: scoreNumericColumn(data, col) }))
    .filter((item) => item.score >= 0.5)
    .sort((a, b) => b.score - a.score);

  if (!consumptionCol && numericCandidates.length > 0) {
    consumptionCol = numericCandidates[0].col;
  }

  if (!voltageCol) {
    const voltageCandidate = numericCandidates.find((item) => item.col !== consumptionCol && item.col.toLowerCase().includes("volt"));
    voltageCol = voltageCandidate?.col || null;
  }

  return { consumptionCol, voltageCol, timeCol };
}

function computeAnalytics(
  rows: ParsedRow[],
  columns: string[],
  dateFrom?: Date | null,
  dateTo?: Date | null
): AnalyticsResult {
  const consumptionCol = rows.some((r) => r.consumption !== null) ? rows.find((r) => r.raw)?.raw ? guessColumn(columns, ["consumption", "kwh", "energy", "usage", "power", "load", "demand", "reading", "value"]) : null : null;
  const voltageCol = rows.some((r) => r.voltage !== null) ? guessColumn(columns, ["voltage", "volt", "v_rms", "vrms"]) : null;
  const timeCol = guessColumn(columns, ["time", "timestamp", "date", "datetime", "hour", "period"]);

  let filtered = rows;
  if (dateFrom || dateTo) {
    filtered = rows.filter((r) => {
      if (!r.date) return true;
      if (dateFrom && r.date < dateFrom) return false;
      if (dateTo) {
        const endOfDay = new Date(dateTo);
        endOfDay.setHours(23, 59, 59, 999);
        if (r.date > endOfDay) return false;
      }
      return true;
    });
  }

  let totalConsumption = 0;
  let peakUsage = 0;
  let minUsage = Infinity;
  let invalidRows = 0;
  const consumptionValues: number[] = [];
  const consumptionTimeSeries: { time: string; value: number }[] = [];
  const voltageTimeSeries: { time: string; voltage: number; nominal: number }[] = [];
  const voltageValues: number[] = [];
  let minDate: Date | null = null;
  let maxDate: Date | null = null;

  filtered.forEach((row) => {
    if (row.date) {
      if (!minDate || row.date < minDate) minDate = row.date;
      if (!maxDate || row.date > maxDate) maxDate = row.date;
    }

    if (row.consumption !== null) {
      totalConsumption += row.consumption;
      consumptionValues.push(row.consumption);
      if (row.consumption > peakUsage) peakUsage = row.consumption;
      if (row.consumption < minUsage) minUsage = row.consumption;
      consumptionTimeSeries.push({ time: row.timeLabel, value: row.consumption });
    } else {
      invalidRows++;
    }

    if (row.voltage !== null) {
      voltageValues.push(row.voltage);
      voltageTimeSeries.push({ time: row.timeLabel, voltage: row.voltage, nominal: 230 });
    }
  });

  if (minUsage === Infinity) minUsage = 0;

  const averageUsage = consumptionValues.length > 0 ? totalConsumption / consumptionValues.length : 0;
  const validConsumptionRows = consumptionValues.length;
  const dataAccuracy = filtered.length > 0 ? (validConsumptionRows / filtered.length) * 100 : 0;

  const avgVoltage = voltageValues.length > 0 ? voltageValues.reduce((a, b) => a + b, 0) / voltageValues.length : 0;
  const voltageDeviation = voltageValues.length > 0
    ? Math.sqrt(voltageValues.reduce((sum, v) => sum + Math.pow(v - avgVoltage, 2), 0) / voltageValues.length)
    : 0;

  let veryEff = 0, efficient = 0, moderate = 0, inefficient = 0;
  const sortedC = [...consumptionValues].sort((a, b) => a - b);
  const median = sortedC.length > 0 ? sortedC[Math.floor(sortedC.length / 2)] : 0;
  consumptionValues.forEach((v) => {
    const ratio = median > 0 ? v / median : 1;
    if (ratio < 0.6) veryEff++;
    else if (ratio < 1.0) efficient++;
    else if (ratio < 1.4) moderate++;
    else inefficient++;
  });

  const mean = averageUsage;
  const stdDev = consumptionValues.length > 1
    ? Math.sqrt(consumptionValues.reduce((s, v) => s + Math.pow(v - mean, 2), 0) / consumptionValues.length)
    : 1;
  const anomalyScores = consumptionValues.map((v) => Math.min(1, Math.abs(v - mean) / Math.max(stdDev * 3, 1)));
  const buckets = Array.from({ length: 10 }, () => 0);
  anomalyScores.forEach((s) => {
    const b = Math.min(9, Math.floor(s * 10));
    buckets[b]++;
  });
  const anomalyData = buckets.map((count, i) => ({
    range: (i * 0.1).toFixed(1),
    count,
    color: i > 6 ? COLORS.danger : i > 4 ? COLORS.warn : COLORS.accent,
  }));

  return {
    totalConsumption: +totalConsumption.toFixed(2),
    averageUsage: +averageUsage.toFixed(2),
    peakUsage: +peakUsage.toFixed(2),
    minUsage: +minUsage.toFixed(2),
    dataAccuracy: +dataAccuracy.toFixed(1),
    invalidRows,
    rowCount: rows.length,
    filteredRowCount: filtered.length,
    columnNames: columns,
    consumptionColumn: consumptionCol,
    voltageColumn: voltageCol,
    timeColumn: timeCol,
    consumptionTimeSeries: consumptionTimeSeries.slice(0, 500),
    voltageTimeSeries: voltageTimeSeries.slice(0, 500),
    hourlyDistribution: [
      { name: "Very Eff.", hours: veryEff, color: COLORS.accent2 },
      { name: "Efficient", hours: efficient, color: "#7ee8a2" },
      { name: "Moderate", hours: moderate, color: COLORS.warn },
      { name: "Inefficient", hours: inefficient, color: COLORS.danger },
    ],
    anomalyData,
    dateRange: { min: minDate, max: maxDate },
    avgVoltage: +avgVoltage.toFixed(1),
    voltageDeviation: +voltageDeviation.toFixed(1),
  };
}

export const CsvProvider = ({ children }: { children: ReactNode }) => {
  const [rawData, setRawData] = useState<CsvRow[]>([]);
  const [parsedRows, setParsedRows] = useState<ParsedRow[]>([]);
  const [fileName, setFileName] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsResult | null>(null);
  const [status, setStatus] = useState<CsvContextType["status"]>("idle");
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const columnsRef = useRef<string[]>([]);

  const uploadCsv = useCallback((file: File) => {
    if (!file.name.endsWith(".csv")) {
      setError("Please upload a .csv file");
      setStatus("error");
      return;
    }
    setStatus("uploading");
    setError(null);
    setFileName(file.name);
    setAnalytics(null);

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: false,
      complete: async (results) => {
        if (results.errors.length > 0 && results.data.length === 0) {
          setError(`Parse error: ${results.errors[0].message}`);
          setStatus("error");
          return;
        }

        const cols = (results.meta.fields || []).filter(Boolean);
        columnsRef.current = cols;
        const data = results.data as CsvRow[];
        setRawData(data);

        const { consumptionCol, voltageCol, timeCol } = inferColumns(data, cols);

        const parsed: ParsedRow[] = data.map((row, i) => ({
          raw: row,
          date: timeCol ? tryParseDate(row[timeCol]) : null,
          consumption: consumptionCol ? normalizeNumber(row[consumptionCol]) : null,
          voltage: voltageCol ? normalizeNumber(row[voltageCol]) : null,
          timeLabel: timeCol ? String(row[timeCol]) : `Row ${i + 1}`,
        }));

        setParsedRows(parsed);
        setAnalytics(computeAnalytics(parsed, cols));
        
        // Upload to backend
        try {
          const { apiUploadCsv } = await import("./api");
          await apiUploadCsv(file);
          console.log("✓ CSV uploaded to backend");
        } catch (err) {
          console.warn("Backend upload failed:", err);
          // Continue with local analysis even if backend upload fails
        }
        
        setStatus("ready");
      },
      error: (err) => {
        setError(err.message);
        setStatus("error");
      },
    });
  }, []);

  const runAnalytics = useCallback(async (dateFrom?: Date | null, dateTo?: Date | null) => {
    if (parsedRows.length === 0) return;
    setStatus("analyzing");
    // Fix #5: only run local CSV analytics here.
    // Backend ML pipeline is triggered explicitly via useMlContext().runPipeline()
    // to avoid two concurrent pipeline runs racing each other.
    const result = computeAnalytics(parsedRows, columnsRef.current, dateFrom, dateTo);
    setAnalytics(result);
    setStatus("ready");
  }, [parsedRows]);

  const clearData = useCallback(() => {
    setRawData([]);
    setParsedRows([]);
    setFileName(null);
    setAnalytics(null);
    setStatus("idle");
    setError(null);
  }, []);

  return (
    <CsvContext.Provider value={{
      rawData, parsedRows, fileName, analytics, status, error,
      uploadCsv, runAnalytics, clearData, autoRefresh, setAutoRefresh,
      columns: columnsRef.current,
    }}>
      {children}
    </CsvContext.Provider>
  );
};

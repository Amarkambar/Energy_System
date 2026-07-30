import { useRef } from "react";
import { Upload, Play, X, RefreshCw } from "lucide-react";
import { useCsvData } from "@/lib/csv-context";
import { useMlContext } from "@/lib/ml-context";
import { cn } from "@/lib/utils";

const AnalyticsToolbar = () => {
  const { fileName, status, error, uploadCsv, runAnalytics, clearData, autoRefresh, setAutoRefresh, rawData } = useCsvData();
  const { runPipeline, pipelineReady, loadState } = useMlContext();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadCsv(file);
    e.target.value = "";
  };

  const statusConfig = {
    idle:      { label: "Idle",           color: "text-muted-foreground", dotColor: "bg-muted-foreground/30", pulse: false },
    uploading: { label: "Uploading…",     color: "text-warn",             dotColor: "bg-warn",               pulse: true  },
    analyzing: { label: "Training ML…",   color: "text-primary",          dotColor: "bg-primary",            pulse: true  },
    ready:     { label: "Ready",          color: "text-secondary",        dotColor: "bg-secondary",          pulse: false },
    error:     { label: "Error",          color: "text-destructive",      dotColor: "bg-destructive",        pulse: false },
  }[status] ?? { label: status, color: "text-muted-foreground", dotColor: "bg-muted-foreground/30", pulse: false };

  const mlStatus = loadState === "loading"
    ? { label: "Pipeline Training", color: "text-warn", dotColor: "bg-warn", pulse: true }
    : pipelineReady
    ? { label: "ML Ready", color: "text-secondary", dotColor: "bg-secondary", pulse: false }
    : null;

  return (
    <div className="bg-card border border-border rounded-xl p-4 px-5 mb-6 animate-fade-up">
      <div className="flex items-center justify-between flex-wrap gap-3">

        {/* Left: actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Run Analytics */}
          <button
            onClick={() => runAnalytics()}
            disabled={rawData.length === 0 || status === "analyzing"}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-xl font-head text-[12px] font-bold tracking-wide transition-all",
              rawData.length > 0 && status !== "analyzing"
                ? "bg-primary text-primary-foreground hover:opacity-90 cursor-pointer shadow-[0_4px_16px_rgba(0,229,255,0.2)] hover:shadow-[0_4px_24px_rgba(0,229,255,0.3)]"
                : "bg-muted/40 text-muted-foreground cursor-not-allowed border border-border"
            )}
          >
            <Play className="w-3.5 h-3.5" />
            Run Analytics
          </button>

          {/* Run ML Pipeline */}
          <button
            onClick={() => runPipeline?.()}
            disabled={loadState === "loading"}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-xl font-head text-[12px] font-bold tracking-wide transition-all border",
              loadState !== "loading"
                ? "border-secondary/30 text-secondary bg-secondary/8 hover:bg-secondary/15 hover:border-secondary/50 cursor-pointer"
                : "border-border text-muted-foreground cursor-not-allowed bg-muted/20"
            )}
          >
            {loadState === "loading" ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <span className="text-[11px]">◎</span>
            )}
            ML Pipeline
          </button>

          {/* Status indicators */}
          <div className="flex items-center gap-4 px-3 py-1.5 bg-bg3 rounded-lg border border-border">
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="text-muted-foreground font-inter">CSV:</span>
              <span className={cn("font-head font-semibold flex items-center gap-1.5", statusConfig.color)}>
                {statusConfig.pulse && (
                  <span className={cn("w-1.5 h-1.5 rounded-full inline-block animate-pulse-dot", statusConfig.dotColor)} />
                )}
                {!statusConfig.pulse && (
                  <span className={cn("w-1.5 h-1.5 rounded-full inline-block", statusConfig.dotColor)} />
                )}
                {statusConfig.label}
              </span>
            </div>

            {mlStatus && (
              <>
                <div className="w-px h-3 bg-border" />
                <div className="flex items-center gap-1.5 text-[11px]">
                  <span className="text-muted-foreground font-inter">ML:</span>
                  <span className={cn("font-head font-semibold flex items-center gap-1.5", mlStatus.color)}>
                    {mlStatus.pulse ? (
                      <span className={cn("w-1.5 h-1.5 rounded-full inline-block animate-pulse-dot", mlStatus.dotColor)} />
                    ) : (
                      <span className={cn("w-1.5 h-1.5 rounded-full inline-block", mlStatus.dotColor)} />
                    )}
                    {mlStatus.label}
                  </span>
                </div>
              </>
            )}
          </div>

          {/* File name tag */}
          {fileName && (
            <div className="flex items-center gap-1.5 text-[11px] bg-primary/8 border border-primary/20 rounded-lg px-3 py-1.5">
              <span>📄</span>
              <span className="text-foreground font-inter">{fileName}</span>
              <span className="text-muted-foreground">({rawData.length.toLocaleString()} rows)</span>
              <button
                onClick={clearData}
                className="text-muted-foreground hover:text-destructive ml-1 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-destructive/10 border border-destructive/30 rounded-lg text-[11px] text-destructive font-inter">
              ⚠ {error}
            </div>
          )}
        </div>

        {/* Right: Upload + Auto Refresh */}
        <div className="flex items-center gap-4">
          <input ref={inputRef} type="file" accept=".csv" onChange={handleFile} className="hidden" />
          <button
            onClick={() => inputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-border text-[12px] font-head font-semibold text-foreground hover:bg-card hover:border-border2 transition-all cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload CSV
          </button>

          <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-inter">
            <span>Auto Refresh</span>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(
                "w-9 h-5 rounded-full relative transition-colors cursor-pointer",
                autoRefresh ? "bg-primary shadow-[0_0_8px_rgba(0,229,255,0.3)]" : "bg-border2"
              )}
            >
              <div
                className={cn(
                  "absolute top-0.5 w-4 h-4 rounded-full bg-foreground transition-transform shadow-sm",
                  autoRefresh ? "translate-x-[18px]" : "translate-x-0.5"
                )}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsToolbar;

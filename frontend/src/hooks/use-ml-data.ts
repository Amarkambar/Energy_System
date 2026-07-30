// src/hooks/use-ml-data.ts
// Central hook — fetches live ML data from FastAPI backend.
// All dashboard pages use this instead of useCsvData() for backend data.

import { useState, useEffect, useCallback, useRef } from "react";
import {
  apiGetPipelineStatus,
  apiRunPipeline,
  apiOverview,
  apiForecast,
  apiAlerts,
  apiModels,
  apiPipelineStats,
  apiConfusionMatrix,
  apiRocCurves,
  apiPrecisionRecall,
  apiModelComparison,
  apiFeatureImportance,
  type ConfusionMatrixData,
  type RocCurvesData,
  type PrecisionRecallData,
  type ModelComparisonData,
  type FeatureImportanceData,
} from "@/lib/api";

export type LoadState = "idle" | "loading" | "ready" | "error";

export interface MLDataState {
  pipelineReady: boolean;
  loadState: LoadState;
  error: string | null;

  // Per-page data (null until fetched)
  overview: Record<string, unknown> | null;
  forecast: Record<string, unknown> | null;
  alerts: Record<string, unknown> | null;
  models: Record<string, unknown> | null;
  pipelineStats: Record<string, unknown> | null;
  
  // New metrics data
  confusionMatrix: ConfusionMatrixData | null;
  rocCurves: RocCurvesData | null;
  precisionRecall: PrecisionRecallData | null;
  modelComparison: ModelComparisonData | null;
  featureImportance: FeatureImportanceData | null;

  // Actions
  runPipeline: () => Promise<void>;
  refreshOverview: () => Promise<void>;
  refreshForecast: () => Promise<void>;
  refreshAlerts: () => Promise<void>;
  refreshModels: () => Promise<void>;
  refreshPipelineStats: () => Promise<void>;
  refreshMetrics: () => Promise<void>;
}

export function useMLData(): MLDataState {
  const [pipelineReady, setPipelineReady] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [forecast, setForecast] = useState<Record<string, unknown> | null>(null);
  const [alerts, setAlerts] = useState<Record<string, unknown> | null>(null);
  const [models, setModels] = useState<Record<string, unknown> | null>(null);
  const [pipelineStats, setPipelineStats] = useState<Record<string, unknown> | null>(null);

  // New metrics state
  const [confusionMatrix, setConfusionMatrix] = useState<ConfusionMatrixData | null>(null);
  const [rocCurves, setRocCurves] = useState<RocCurvesData | null>(null);
  const [precisionRecall, setPrecisionRecall] = useState<PrecisionRecallData | null>(null);
  const [modelComparison, setModelComparison] = useState<ModelComparisonData | null>(null);
  const [featureImportance, setFeatureImportance] = useState<FeatureImportanceData | null>(null);

  // ── Fix #1: use a ref for the interval so only ONE ever exists ──
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const clearMLData = useCallback(() => {
    setOverview(null);
    setForecast(null);
    setAlerts(null);
    setModels(null);
    setPipelineStats(null);
    setConfusionMatrix(null);
    setRocCurves(null);
    setPrecisionRecall(null);
    setModelComparison(null);
    setFeatureImportance(null);
  }, []);

  const fetchAll = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    try {
      const [ov, fc, al, md, ps] = await Promise.all([
        apiOverview(),
        apiForecast(),
        apiAlerts(),
        apiModels(),
        apiPipelineStats(),
      ]);
      setOverview(ov);
      setForecast(fc);
      setAlerts(al);
      setModels(md);
      setPipelineStats(ps);
      setLoadState("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load ML data");
      setLoadState("error");
    }
  }, []);

  const refreshMetrics = useCallback(async () => {
    try {
      const [cm, roc, pr, comp, fi] = await Promise.all([
        apiConfusionMatrix().catch(() => null),
        apiRocCurves().catch(() => null),
        apiPrecisionRecall().catch(() => null),
        apiModelComparison().catch(() => null),
        apiFeatureImportance().catch(() => null),
      ]);
      if (cm) setConfusionMatrix(cm);
      if (roc) setRocCurves(roc);
      if (pr) setPrecisionRecall(pr);
      if (comp) setModelComparison(comp);
      if (fi) setFeatureImportance(fi);
    } catch {
      /* silent - metrics are optional */
    }
  }, []);

  // ── FIX: stopPolling MUST be declared before startPolling/restartPolling ──
  // `const` is NOT hoisted — accessing stopPolling before its declaration
  // causes a TDZ ReferenceError in the dependency arrays below.
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Poll fast (5s) while training for quick feedback; slow (30s) when idle/ready.
  const startPolling = useCallback((isTraining = false) => {
    if (intervalRef.current) return; // already running — don't stack a second interval
    const intervalMs = isTraining ? 5000 : 30000;
    intervalRef.current = setInterval(() => {
      fetchAll();
      refreshMetrics();
    }, intervalMs);
  }, [fetchAll, refreshMetrics]);

  // ── On mount: check if backend already has cached data (survives Ctrl+R) ──
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await apiGetPipelineStatus();

        if (status.is_training) {
          setLoadState("loading");
          setPipelineReady(false);
          stopPolling();
          clearMLData();
        } else if (status.has_cache || status.ready) {
          // Backend already has results — restore them immediately
          setPipelineReady(true);
          await fetchAll();
          await refreshMetrics();
          startPolling(false); // pipeline is ready — use slow 30s polling
        } else {
          setPipelineReady(false);
          setLoadState("idle");
          stopPolling();
          clearMLData();
        }
      } catch {
        setPipelineReady(false);
        setLoadState("idle");
      }
    };

    checkStatus();

    // ── Cleanup: always clear the interval when the component unmounts ──
    return () => stopPolling();
  }, [fetchAll, refreshMetrics, clearMLData, startPolling, stopPolling]);

  const runPipeline = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    stopPolling();
    clearMLData();
    try {
      // Kick off the background pipeline run (returns immediately)
      await apiRunPipeline();

      // Poll /api/pipeline/status every 2s until training finishes
      await new Promise<void>((resolve, reject) => {
        const poll = setInterval(async () => {
          try {
            const status = await apiGetPipelineStatus();
            if (!status.is_training && (status.has_cache || status.ready)) {
              clearInterval(poll);
              resolve();
            } else if (!status.is_training && !status.has_cache) {
              // Training stopped but no cache — something failed server-side
              clearInterval(poll);
              reject(new Error("Pipeline completed but no data was cached. Check backend logs."));
            }
            // else: still training — keep polling
          } catch (e) {
            clearInterval(poll);
            reject(e);
          }
        }, 2000);
      });

      setPipelineReady(true);
      await fetchAll();
      await refreshMetrics();
      startPolling(false); // pipeline just finished — use slow 30s polling
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pipeline run failed");
      setLoadState("error");
    }
  }, [fetchAll, refreshMetrics, startPolling, stopPolling, clearMLData]);

  const refreshOverview = useCallback(async () => {
    try { setOverview(await apiOverview()); } catch { /* silent */ }
  }, []);

  const refreshForecast = useCallback(async () => {
    try { setForecast(await apiForecast()); } catch { /* silent */ }
  }, []);

  const refreshAlerts = useCallback(async () => {
    try { setAlerts(await apiAlerts()); } catch { /* silent */ }
  }, []);

  const refreshModels = useCallback(async () => {
    try { setModels(await apiModels()); } catch { /* silent */ }
  }, []);

  const refreshPipelineStats = useCallback(async () => {
    try { setPipelineStats(await apiPipelineStats()); } catch { /* silent */ }
  }, []);

  return {
    pipelineReady,
    loadState,
    error,
    overview,
    forecast,
    alerts,
    models,
    pipelineStats,
    confusionMatrix,
    rocCurves,
    precisionRecall,
    modelComparison,
    featureImportance,
    runPipeline,
    refreshOverview,
    refreshForecast,
    refreshAlerts,
    refreshModels,
    refreshPipelineStats,
    refreshMetrics,
  };
}

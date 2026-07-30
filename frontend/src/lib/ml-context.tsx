// src/lib/ml-context.tsx
// Wraps dashboard pages with live ML data from FastAPI backend.
// Pages access via useMlContext() instead of fetching independently.

import { createContext, useContext, ReactNode } from "react";
import { useMLData, MLDataState } from "@/hooks/use-ml-data";

const MLContext = createContext<MLDataState | null>(null);

export function MLDataProvider({ children }: { children: ReactNode }) {
  const mlData = useMLData();
  return <MLContext.Provider value={mlData}>{children}</MLContext.Provider>;
}

export function useMlContext(): MLDataState {
  const ctx = useContext(MLContext);
  if (!ctx) throw new Error("useMlContext must be inside MLDataProvider");
  return ctx;
}

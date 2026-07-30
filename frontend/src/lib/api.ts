// src/lib/api.ts — All backend API calls go through here

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("energydiag_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  // Add _ts cache-buster to GET requests so proxies/CDNs never serve stale data.
  // The backend Cache-Control headers handle the browser cache layer;
  // this handles any intermediate caching layer that ignores those headers.
  const isWrite = options.method && ["POST", "PUT", "PATCH", "DELETE"].includes(options.method.toUpperCase());
  const url = isWrite
    ? `${API_BASE}${path}`
    : `${API_BASE}${path}${path.includes("?") ? "&" : "?"}_ts=${Date.now()}`;

  const res = await fetch(url, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── Auth ────────────────────────────────────────────────
export interface AuthUser {
  email: string;
  name: string;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

export async function apiRegister(
  name: string,
  email: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function apiLogin(
  email: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiForgotPassword(email: string): Promise<{ message: string }> {
  return request("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function apiResetPassword(
  email: string,
  new_password: string,
  token: string,  // FIX: backend now requires token to prevent unauthenticated resets
): Promise<{ message: string }> {
  return request("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ email, new_password, token }),
  });
}

export async function apiMe(): Promise<{ user: AuthUser }> {
  return request("/api/auth/me");
}

// ── Session helpers ─────────────────────────────────────
export function saveSession(token: string, user: AuthUser) {
  localStorage.setItem("energydiag_token", token);
  localStorage.setItem("energydiag_user", JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem("energydiag_token");
  localStorage.removeItem("energydiag_user");
}

export function getSession(): AuthUser | null {
  const raw = localStorage.getItem("energydiag_user");
  return raw ? JSON.parse(raw) : null;
}

// ── ML / Pipeline endpoints ─────────────────────────────

export async function apiUploadCsv(file: File): Promise<{ status: string; message: string; filename: string }> {
  const token = getToken();
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/data/upload-csv`, {
    method: 'POST',
    cache: "no-store",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function apiRunPipeline(): Promise<{ status: string; rows: number; message: string }> {
  return request("/api/pipeline/run", { method: "POST" });
}

export async function apiClearPipeline(): Promise<{ status: string; message: string }> {
  return request("/api/pipeline/clear", { method: "POST" });
}

export async function apiGetPipelineStatus(): Promise<{
  is_training: boolean;
  has_cache: boolean;
  has_uploaded_csv: boolean;
  ready?: boolean;
  status?: string;
  rows?: number;
  columns?: number;
  message?: string;
}> {
  return request("/api/pipeline/status");
}

// NOTE: apiPipelineStatus removed — was a duplicate of apiGetPipelineStatus.
// Use apiGetPipelineStatus() for all status checks.

export async function apiOverview(): Promise<Record<string, unknown>> {
  return request("/api/data/overview");
}

export async function apiForecast(): Promise<Record<string, unknown>> {
  return request("/api/data/forecast");
}

export async function apiAlerts(): Promise<Record<string, unknown>> {
  return request("/api/data/alerts");
}

export async function apiModels(): Promise<Record<string, unknown>> {
  return request("/api/data/models");
}

export async function apiPipelineStats(): Promise<Record<string, unknown>> {
  return request("/api/data/pipeline-stats");
}

// ── New Metrics endpoints ─────────────────────────────────

export interface ConfusionMatrixData {
  confusion_matrix: number[][];
  confusion_matrix_normalized: number[][];
  classes: string[];
  per_class_metrics: {
    precision: number[];
    recall: number[];
    f1_score: number[];
    specificity: number[];
    support: number[];
  };
  accuracy: number;
  f1_score: number;
  precision: number;
  recall: number;
}

export interface RocCurve {
  class: string;
  fpr: number[];
  tpr: number[];
  auc: number;
}

export interface RocCurvesData {
  curves: RocCurve[];
  auc_scores: Record<string, number>;
  macro_auc: number;
  classes: string[];
}

export interface PrCurve {
  class: string;
  precision: number[];
  recall: number[];
  ap: number;
}

export interface PrecisionRecallData {
  curves: PrCurve[];
  ap_scores: Record<string, number>;
  macro_ap: number;
  classes: string[];
}

export interface ModelComparisonData {
  models: Array<{
    name: string;
    task_type: string;
    metrics: Record<string, number>;
    training_time?: number;
    params?: Record<string, unknown>;
  }>;
  comparison_table: Array<Record<string, unknown>>;
  bar_chart_data: Array<Record<string, unknown>>;
  radar_chart_data: {
    labels: string[];
    datasets: Array<{ model: string; values: number[] }>;
  };
  rankings: Record<string, Array<{ model: string; value: number; rank: number }>>;
  best_model: string | null;
  summary: {
    n_models: number;
    task_type: string | null;
  };
}

export interface FeatureImportanceData {
  shap_importance: Array<{ feature: string; importance: number }>;
  model_importance: Array<{ feature: string; importance: number }>;
  pca_analysis: {
    n_components: number;
    total_variance_explained: number;
    scree_plot: Array<{ component: string; individual: number; cumulative: number }>;
    component_loadings: Array<{
      component: string;
      variance_explained: number;
      top_features: Array<{ feature: string; loading: number; abs_loading: number }>;
    }>;
  };
  feature_selection: {
    method: string;
    selected_features: string[];
    feature_scores: Array<{ feature: string; score: number }>;
  };
}

export async function apiConfusionMatrix(): Promise<ConfusionMatrixData> {
  return request("/api/metrics/confusion-matrix");
}

export async function apiRocCurves(): Promise<RocCurvesData> {
  return request("/api/metrics/roc-curves");
}

export async function apiPrecisionRecall(): Promise<PrecisionRecallData> {
  return request("/api/metrics/precision-recall");
}

export async function apiModelComparison(): Promise<ModelComparisonData> {
  return request("/api/metrics/comparison");
}

export async function apiFeatureImportance(): Promise<FeatureImportanceData> {
  return request("/api/metrics/feature-importance");
}

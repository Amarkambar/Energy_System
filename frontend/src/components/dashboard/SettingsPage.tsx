// components/dashboard/SettingsPage.tsx — Configurable alert thresholds + system info

import { useId, useState, useEffect } from "react";
import { toast } from "sonner";
import {
  AlertTriangle,
  BellRing,
  Check,
  ChevronDown,
  Download,
  Gauge,
  HardDrive,
  KeyRound,
  Mail,
  MonitorCog,
  RotateCcw,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function getToken() {
  // FIX: JWT is stored under 'energydiag_token', NOT nested inside 'energydiag_user'
  return localStorage.getItem("energydiag_token") ?? "";
}

interface Settings {
  alert_consumption_threshold: number;
  alert_anomaly_score_threshold: number;
  alert_voltage_deviation: number;
  alert_load_factor_threshold: number;
  alert_email_recipients: string[];
  smtp_enabled: boolean;
}

const DEFAULTS: Settings = {
  alert_consumption_threshold: 500,
  alert_anomaly_score_threshold: 0.7,
  alert_voltage_deviation: 10,
  alert_load_factor_threshold: 0.9,
  alert_email_recipients: [],
  smtp_enabled: false,
};

// Industry-specific preset configurations
const PRESETS: Record<string, { name: string; description: string; settings: Settings }> = {
  manufacturing: {
    name: "Manufacturing Facility",
    description: "High consumption, moderate voltage tolerance",
    settings: {
      alert_consumption_threshold: 800,
      alert_anomaly_score_threshold: 0.75,
      alert_voltage_deviation: 12,
      alert_load_factor_threshold: 0.92,
      alert_email_recipients: [],
      smtp_enabled: false,
    },
  },
  datacenter: {
    name: "Data Center",
    description: "Critical voltage stability, high baseline consumption",
    settings: {
      alert_consumption_threshold: 1200,
      alert_anomaly_score_threshold: 0.65,
      alert_voltage_deviation: 5,
      alert_load_factor_threshold: 0.95,
      alert_email_recipients: [],
      smtp_enabled: false,
    },
  },
  hospital: {
    name: "Hospital / Healthcare",
    description: "Very strict voltage tolerance, 24/7 monitoring",
    settings: {
      alert_consumption_threshold: 600,
      alert_anomaly_score_threshold: 0.6,
      alert_voltage_deviation: 6,
      alert_load_factor_threshold: 0.88,
      alert_email_recipients: [],
      smtp_enabled: false,
    },
  },
  retail: {
    name: "Retail / Office",
    description: "Lower consumption, business hours focus",
    settings: {
      alert_consumption_threshold: 350,
      alert_anomaly_score_threshold: 0.7,
      alert_voltage_deviation: 15,
      alert_load_factor_threshold: 0.85,
      alert_email_recipients: [],
      smtp_enabled: false,
    },
  },
  default: {
    name: "Default / General",
    description: "Balanced thresholds for general use",
    settings: DEFAULTS,
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [recipientInput, setRecipientInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showPresets, setShowPresets] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/settings/thresholds`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Settings request failed (${r.status})`);
        return r.json();
      })
      .then((d) => {
        setSettings({ ...DEFAULTS, ...d });
        setRecipientInput((d.alert_email_recipients ?? []).join(", "));
      })
      .catch(() => {
        setLoadError(true);
        toast.error("Failed to load settings. Changes cannot be confirmed until the API reconnects.");
      })
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    setSaving(true);
    const payload: Settings = {
      ...settings,
      alert_email_recipients: recipientInput
        .split(",")
        .map((e) => e.trim())
        .filter(Boolean),
    };
    try {
      const r = await fetch(`${API}/api/settings/thresholds`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(await r.text());
      toast.success("Settings saved successfully");
      const d = await r.json();
      setSettings({ ...DEFAULTS, ...d.settings });
      setLoadError(false);
      setHasUnsavedChanges(false);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      toast.error(`Save failed: ${message}`);
    } finally {
      setSaving(false);
    }
  }

  function reset() {
    setSettings(DEFAULTS);
    setRecipientInput("");
    setHasUnsavedChanges(true);
    toast.info("Settings reset to defaults (not yet saved)");
  }

  function applyPreset(presetKey: string) {
    const preset = PRESETS[presetKey];
    if (preset) {
      setSettings({ ...preset.settings, alert_email_recipients: settings.alert_email_recipients, smtp_enabled: settings.smtp_enabled });
      setHasUnsavedChanges(true);
      setShowPresets(false);
      toast.success(`Applied "${preset.name}" preset`);
    }
  }

  function exportSettings() {
    const json = JSON.stringify(settings, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `energy-diagnostics-settings-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Settings exported");
  }

  function importSettings(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string);
        setSettings({ ...DEFAULTS, ...imported });
        setRecipientInput((imported.alert_email_recipients ?? []).join(", "));
        setHasUnsavedChanges(true);
        toast.success("Settings imported successfully");
      } catch (err) {
        toast.error("Invalid settings file");
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  }

  function calculateAlertSensitivity() {
    // Calculate a simple sensitivity score (0-100)
    const consumptionScore = Math.max(0, 100 - (settings.alert_consumption_threshold / 10));
    const anomalyScore = (1 - settings.alert_anomaly_score_threshold) * 100;
    const voltageScore = Math.max(0, 100 - (settings.alert_voltage_deviation * 5));
    const loadScore = settings.alert_load_factor_threshold * 100;
    
    return Math.round((consumptionScore + anomalyScore + voltageScore + loadScore) / 4);
  }

  if (loading) {
    return (
      <div className="mx-auto w-full min-w-0 max-w-5xl space-y-6 p-2" aria-label="Loading settings">
        <div className="h-24 animate-pulse rounded-2xl border border-border bg-card/60" />
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="h-64 animate-pulse rounded-2xl border border-border bg-card/60" />
          <div className="h-64 animate-pulse rounded-2xl border border-border bg-card/60" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-5xl space-y-6 p-2 pb-8 sm:space-y-8">
      <header className="flex min-w-0 flex-col gap-5 rounded-2xl border border-border bg-card/70 p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Settings2 className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">Workspace</p>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Tune energy alerts, notification delivery, and system preferences.
            </p>
          </div>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-3 sm:justify-end">
          <div className={`inline-flex max-w-full items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${loadError ? "border-destructive/30 bg-destructive/10 text-destructive" : hasUnsavedChanges ? "border-amber-500/30 bg-amber-500/10 text-amber-500" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"}`} role="status" aria-live="polite">
            {loadError ? <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> : hasUnsavedChanges ? <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> : <Check className="h-3.5 w-3.5 shrink-0" />}
            <span>{loadError ? "Could not verify saved settings" : hasUnsavedChanges ? "Unsaved changes" : "All changes saved"}</span>
          </div>
        </div>
      </header>

      {/* Industry Presets */}
      <section className="space-y-4 rounded-2xl border border-border bg-card/70 p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><SlidersHorizontal className="h-5 w-5" /></div>
            <div>
              <h2 className="text-base font-semibold text-foreground">Industry presets</h2>
              <p className="text-xs text-muted-foreground">Start with thresholds tailored to your facility.</p>
            </div>
          </div>
          <button
            onClick={() => setShowPresets(!showPresets)}
            aria-expanded={showPresets}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            {showPresets ? "Hide presets" : "Browse presets"}
            <ChevronDown className={`h-4 w-4 transition-transform ${showPresets ? "rotate-180" : ""}`} />
          </button>
        </div>
        
        {showPresets && (
          <div className="grid grid-cols-1 gap-3 border-t border-border pt-4 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                className="group rounded-xl border border-border bg-background/60 p-4 text-left transition-all hover:border-primary/50 hover:bg-primary/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <h3 className="text-sm font-semibold text-foreground transition-colors group-hover:text-primary">
                  {preset.name}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">{preset.description}</p>
                <div className="mt-4 space-y-2 border-t border-border pt-3 text-xs text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Consumption:</span>
                    <span className="font-medium text-foreground">{preset.settings.alert_consumption_threshold} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Anomaly:</span>
                    <span className="font-medium text-foreground">{preset.settings.alert_anomaly_score_threshold}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Voltage:</span>
                    <span className="font-medium text-foreground">±{preset.settings.alert_voltage_deviation} V</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Alert Sensitivity Indicator */}
      <section className="rounded-2xl border border-border bg-gradient-to-br from-primary/[0.08] via-card/70 to-card/40 p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-foreground">
              <Gauge className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">Alert sensitivity</h3>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Estimated responsiveness of the current threshold configuration.
            </p>
          </div>
          <div className="flex items-center gap-3 sm:min-w-40 sm:justify-end">
            <div className="text-3xl font-bold tabular-nums text-primary">{calculateAlertSensitivity()}%</div>
            <div className="text-xs text-muted-foreground">
              <div className="font-medium text-foreground">{calculateAlertSensitivity() > 70 ? "High" : calculateAlertSensitivity() > 40 ? "Medium" : "Low"}</div>
              Overall rating
            </div>
          </div>
        </div>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-background/70" role="progressbar" aria-label="Alert sensitivity" aria-valuenow={calculateAlertSensitivity()} aria-valuemin={0} aria-valuemax={100}>
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500 transition-all duration-500"
            style={{ width: `${calculateAlertSensitivity()}%` }}
          />
        </div>
      </section>

      {/* Alert Thresholds */}
      <section className="min-w-0 space-y-6 rounded-2xl border border-border bg-card/70 p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><BellRing className="h-5 w-5" /></div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Alert thresholds</h2>
            <p className="text-xs text-muted-foreground">Set when the monitoring system should flag a reading.</p>
          </div>
        </div>

        <div className="grid min-w-0 grid-cols-1 gap-x-8 gap-y-6 border-t border-border pt-5 md:grid-cols-2">
          <NumberField
            label="Consumption Threshold (kWh)"
            description="Trigger a warning when hourly consumption exceeds this value."
            value={settings.alert_consumption_threshold}
            min={50}
            max={5000}
            step={50}
            onChange={(v) => {
              setSettings((s) => ({ ...s, alert_consumption_threshold: v }));
              setHasUnsavedChanges(true);
            }}
          />

          <NumberField
            label="Anomaly Score Threshold (0–1)"
            description="Flag readings with an anomaly confidence score above this value."
            value={settings.alert_anomaly_score_threshold}
            min={0.1}
            max={1}
            step={0.05}
            onChange={(v) => {
              setSettings((s) => ({ ...s, alert_anomaly_score_threshold: v }));
              setHasUnsavedChanges(true);
            }}
          />

          <NumberField
            label="Voltage Deviation (V)"
            description="Alert when voltage deviates from 230 V nominal by more than this."
            value={settings.alert_voltage_deviation}
            min={1}
            max={50}
            step={1}
            onChange={(v) => {
              setSettings((s) => ({ ...s, alert_voltage_deviation: v }));
              setHasUnsavedChanges(true);
            }}
          />

          <NumberField
            label="Peak Load Factor Threshold (0–1)"
            description="High-load-factor alert fires when load_factor exceeds this during peak hours."
            value={settings.alert_load_factor_threshold}
            min={0.5}
            max={1}
            step={0.05}
            onChange={(v) => {
              setSettings((s) => ({ ...s, alert_load_factor_threshold: v }));
              setHasUnsavedChanges(true);
            }}
          />
        </div>
      </section>

      {/* Email / SMTP */}
      <section className="min-w-0 space-y-5 rounded-2xl border border-border bg-card/70 p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><Mail className="h-5 w-5" /></div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Email notifications</h2>
            <p className="text-xs text-muted-foreground">Choose whether alert messages should be sent by email.</p>
          </div>
        </div>

        <div className="flex flex-col gap-4 rounded-xl border border-border bg-background/50 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">Email alerts</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{settings.smtp_enabled ? "Delivery is enabled for the configured recipients." : "Delivery is currently turned off."}</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={settings.smtp_enabled}
            aria-label="Enable email alerts"
            className={`relative h-7 w-12 shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${settings.smtp_enabled ? "bg-primary" : "bg-muted"}`}
            onClick={() => {
              setSettings((s) => ({ ...s, smtp_enabled: !s.smtp_enabled }));
              setHasUnsavedChanges(true);
            }}
          >
            <div
              className={`absolute top-1 h-5 w-5 rounded-full bg-background shadow transition-transform ${
                settings.smtp_enabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        <div className="min-w-0">
          <label htmlFor="alert-email-recipients" className="mb-2 block text-sm font-medium text-foreground">
            Alert recipients
          </label>
          <p className="mb-2 text-xs text-muted-foreground">Separate multiple email addresses with commas.</p>
          <input
            id="alert-email-recipients"
            name="alert-email-recipients"
            type="text"
            className="block w-full min-w-0 rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="admin@company.com, ops@company.com"
            value={recipientInput}
            onChange={(e) => {
              setRecipientInput(e.target.value);
              setHasUnsavedChanges(true);
            }}
          />
        </div>

        <details className="group rounded-xl border border-border bg-background/50">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-medium text-foreground [&::-webkit-details-marker]:hidden">
            <span>SMTP delivery configuration</span>
            <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
          </summary>
          <div className="space-y-2 border-t border-border px-4 pb-4 pt-3 text-xs text-muted-foreground">
          <p>
            Configure these environment variables in <code className="rounded bg-muted px-1.5 py-0.5 text-primary">backend/.env</code> to enable email delivery:
          </p>
          <pre className="overflow-x-auto rounded-lg border border-border bg-muted/50 p-3 text-xs text-foreground">
{`SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password`}
          </pre>
          <p className="text-amber-500">
            Use an app password for Gmail. Never use or share your regular account password.
          </p>
          </div>
        </details>
      </section>

      {/* System Info */}
      <section className="space-y-4 rounded-2xl border border-border bg-card/70 p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><MonitorCog className="h-5 w-5" /></div>
          <div>
            <h2 className="text-base font-semibold text-foreground">System information</h2>
            <p className="text-xs text-muted-foreground">Security and storage details for this workspace.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 border-t border-border pt-4 sm:grid-cols-3">
          {[
            { label: "Cache", value: "Disk-persistent (restart-proof)", icon: HardDrive },
            { label: "Authentication", value: "HMAC token (7-day expiry)", icon: ShieldCheck },
            { label: "Reset tokens", value: "15-minute one-time tokens", icon: KeyRound },
          ].map((item) => (
            <div
              key={item.label}
              className="flex items-start gap-3 rounded-xl border border-border bg-background/50 p-4"
            >
              <item.icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{item.label}</p>
                <p className="mt-1 break-words text-sm text-foreground">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Actions */}
      <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card/70 p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={exportSettings}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            <Download className="h-4 w-4" /> Export
          </button>
          <label className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent">
            <input
              id="settings-import-file"
              name="settings-file"
              type="file"
              accept=".json"
              onChange={importSettings}
              className="hidden"
            />
            <Upload className="h-4 w-4" /> Import
          </label>
        </div>
        
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:gap-3">
          <button
            onClick={reset}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            <RotateCcw className="h-4 w-4" /> Reset defaults
          </button>
          <button
            onClick={save}
            disabled={saving || !hasUnsavedChanges}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Saving…
              </>
            ) : (
              "Save Settings"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Reusable number slider field ─────────────────────────
function NumberField({
  label,
  description,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  const fieldId = useId();
  const updateValue = (rawValue: string) => {
    const parsed = Number(rawValue);
    if (rawValue.trim() !== "" && Number.isFinite(parsed)) {
      onChange(Math.min(max, Math.max(min, parsed)));
    }
  };

  return (
    <div className="min-w-0 space-y-2">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <label htmlFor={`${fieldId}-number`} className="min-w-0 flex-1 break-words pt-1 text-sm font-medium text-foreground">{label}</label>
        <input
          id={`${fieldId}-number`}
          name={`${fieldId}-number`}
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => updateValue(e.target.value)}
          className="w-24 shrink-0 rounded-lg border border-border bg-background px-2 py-1.5 text-right text-sm font-semibold tabular-nums text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <input
        id={`${fieldId}-range`}
        name={`${fieldId}-range`}
        aria-label={`${label} slider`}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => updateValue(e.target.value)}
        className="w-full cursor-pointer accent-primary"
      />
      <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}

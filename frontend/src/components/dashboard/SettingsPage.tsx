// components/dashboard/SettingsPage.tsx — Configurable alert thresholds + system info

import { useState, useEffect } from "react";
import { toast } from "sonner";

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
  const [saving, setSaving] = useState(false);
  const [showPresets, setShowPresets] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/settings/thresholds`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        setSettings({ ...DEFAULTS, ...d });
        setRecipientInput((d.alert_email_recipients ?? []).join(", "));
      })
      .catch(() => toast.error("Failed to load settings"))
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
      setHasUnsavedChanges(false);
    } catch (e: any) {
      toast.error(`Save failed: ${e.message}`);
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
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-2">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-slate-400 text-sm mt-1">
            Configure alert thresholds and system preferences. Changes take effect
            immediately without restarting the server.
          </p>
        </div>
        {hasUnsavedChanges && (
          <div className="flex items-center gap-2 bg-yellow-500/20 border border-yellow-500/30 rounded-lg px-3 py-2">
            <span className="text-yellow-400 text-xs font-medium">⚠️ Unsaved changes</span>
          </div>
        )}
      </div>

      {/* Industry Presets */}
      <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
            <span>🏭</span> Industry Presets
          </h2>
          <button
            onClick={() => setShowPresets(!showPresets)}
            className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            {showPresets ? "Hide" : "Show"} Presets
          </button>
        </div>
        
        {showPresets && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                className="bg-slate-900/60 border border-slate-700 hover:border-cyan-500/50 rounded-lg p-4 text-left transition-all group"
              >
                <h3 className="text-sm font-semibold text-white group-hover:text-cyan-400 transition-colors">
                  {preset.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1">{preset.description}</p>
                <div className="mt-3 space-y-1 text-xs text-slate-500">
                  <div className="flex justify-between">
                    <span>Consumption:</span>
                    <span className="text-slate-400">{preset.settings.alert_consumption_threshold} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Anomaly:</span>
                    <span className="text-slate-400">{preset.settings.alert_anomaly_score_threshold}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Voltage:</span>
                    <span className="text-slate-400">±{preset.settings.alert_voltage_deviation}V</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
        
        <p className="text-xs text-slate-500">
          Select a preset to quickly configure thresholds for your industry. You can customize values after applying.
        </p>
      </section>

      {/* Alert Sensitivity Indicator */}
      <section className="bg-gradient-to-r from-slate-800/60 to-slate-800/40 border border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Alert Sensitivity</h3>
            <p className="text-xs text-slate-400 mt-1">
              Overall sensitivity of your alert configuration
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-cyan-400">{calculateAlertSensitivity()}%</div>
            <div className="text-xs text-slate-500 mt-1">
              {calculateAlertSensitivity() > 70 ? "High" : calculateAlertSensitivity() > 40 ? "Medium" : "Low"}
            </div>
          </div>
        </div>
        <div className="mt-4 bg-slate-900/60 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 transition-all duration-500"
            style={{ width: `${calculateAlertSensitivity()}%` }}
          />
        </div>
      </section>

      {/* Alert Thresholds */}
      <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-6">
        <h2 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
          <span>⚡</span> Alert Thresholds
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
      <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-5">
        <h2 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
          <span>📧</span> Email Notifications
        </h2>

        <div className="flex items-center gap-3">
          <div
            className={`w-11 h-6 rounded-full relative cursor-pointer transition-colors ${
              settings.smtp_enabled ? "bg-cyan-500" : "bg-slate-600"
            }`}
            onClick={() => {
              setSettings((s) => ({ ...s, smtp_enabled: !s.smtp_enabled }));
              setHasUnsavedChanges(true);
            }}
          >
            <div
              className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                settings.smtp_enabled ? "translate-x-5" : "translate-x-0.5"
              }`}
            />
          </div>
          <span className="text-slate-300 text-sm">
            Email alerts {settings.smtp_enabled ? "enabled" : "disabled"}
          </span>
        </div>

        <div>
          <label className="block text-sm text-slate-400 mb-1">
            Alert Recipients (comma-separated emails)
          </label>
          <input
            type="text"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 transition-colors"
            placeholder="admin@company.com, ops@company.com"
            value={recipientInput}
            onChange={(e) => {
              setRecipientInput(e.target.value);
              setHasUnsavedChanges(true);
            }}
          />
        </div>

        <div className="bg-slate-900/60 rounded-lg p-4 text-xs text-slate-400 space-y-1">
          <p className="font-semibold text-slate-300">SMTP Configuration</p>
          <p>
            To enable real email sending, set these environment variables in{" "}
            <code className="text-cyan-400 bg-slate-800 px-1 rounded">backend/.env</code>:
          </p>
          <pre className="bg-slate-800 rounded p-2 text-xs mt-2 overflow-x-auto">
{`SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password`}
          </pre>
          <p className="text-yellow-400">
            ⚠️ Use an App Password (not your real password) for Gmail accounts.
          </p>
        </div>
      </section>

      {/* System Info */}
      <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-cyan-400 flex items-center gap-2">
          <span>🖥️</span> System Info
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: "Cache", value: "Disk-persistent (restart-proof)", icon: "💾" },
            { label: "Auth", value: "HMAC token (7-day expiry)", icon: "🔐" },
            { label: "Reset tokens", value: "15-minute one-time tokens", icon: "🔑" },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-slate-900/60 rounded-lg p-4 flex items-start gap-3"
            >
              <span className="text-2xl">{item.icon}</span>
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider">{item.label}</p>
                <p className="text-sm text-slate-300 mt-0.5">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">
        <div className="flex gap-2">
          <button
            onClick={exportSettings}
            className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 text-sm hover:bg-slate-700 transition-colors flex items-center gap-2"
          >
            <span>💾</span> Export
          </button>
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".json"
              onChange={importSettings}
              className="hidden"
            />
            <div className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 text-sm hover:bg-slate-700 transition-colors flex items-center gap-2">
              <span>📂</span> Import
            </div>
          </label>
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={reset}
            className="px-5 py-2.5 rounded-lg border border-slate-600 text-slate-300 text-sm hover:bg-slate-700 transition-colors"
          >
            Reset to Defaults
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-6 py-2.5 rounded-lg bg-cyan-500 text-slate-900 font-semibold text-sm hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
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
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-300">{label}</label>
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-cyan-400 text-right focus:outline-none focus:border-cyan-500"
        />
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-cyan-500 cursor-pointer"
      />
      <p className="text-xs text-slate-500">{description}</p>
    </div>
  );
}

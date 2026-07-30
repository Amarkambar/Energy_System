import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiLogin, saveSession } from "@/lib/api";

const FEATURES = [
  { icon: "⚡", label: "Real-time monitoring" },
  { icon: "🤖", label: "AI anomaly detection" },
  { icon: "📈", label: "24-hour forecasting" },
  { icon: "🔔", label: "Smart alert engine" },
];

const LoginPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password.trim()) { setError("Please fill in all fields"); return; }
    setLoading(true);
    try {
      const { token, user } = await apiLogin(email.trim(), password);
      saveSession(token, user);
      navigate("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow orbs */}
      <div className="fixed w-[600px] h-[600px] rounded-full bg-primary/[0.06] -top-[200px] -left-[200px] blur-[140px] pointer-events-none z-0 animate-float" />
      <div className="fixed w-[500px] h-[500px] rounded-full bg-secondary/[0.05] bottom-[-100px] -right-[150px] blur-[140px] pointer-events-none z-0" style={{ animationDelay: "2s" }} />
      <div className="fixed w-[300px] h-[300px] rounded-full bg-primary/[0.04] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 blur-[100px] pointer-events-none z-0" />

      <div className="relative z-10 w-full max-w-4xl flex gap-0 rounded-2xl overflow-hidden border border-border shadow-[0_24px_80px_rgba(0,0,0,0.6)]">
        {/* Left panel — branding */}
        <div className="hidden md:flex flex-col justify-between w-[45%] bg-gradient-to-br from-card via-bg2 to-background p-10 border-r border-border relative overflow-hidden">
          {/* Decorative grid in left panel */}
          <div className="absolute inset-0 opacity-20 pointer-events-none" style={{
            backgroundImage: "linear-gradient(hsl(196 30% 14%) 1px, transparent 1px), linear-gradient(90deg, hsl(196 30% 14%) 1px, transparent 1px)",
            backgroundSize: "30px 30px"
          }} />
          {/* Glow accent */}
          <div className="absolute top-0 right-0 w-48 h-48 bg-primary/10 rounded-full blur-[80px] pointer-events-none" />

          <div className="relative z-10">
            {/* Logo */}
            <div className="flex items-center gap-3 mb-12">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-2xl shadow-[0_0_24px_rgba(0,229,255,0.25)]">
                ⚡
              </div>
              <div>
                <div className="font-head text-2xl font-extrabold tracking-tight">
                  Energy<span className="text-primary">Diag</span>
                </div>
                <div className="text-[9px] text-muted-foreground uppercase tracking-widest">AI Diagnostics</div>
              </div>
            </div>

            {/* Tagline */}
            <h2 className="font-head text-2xl font-extrabold leading-tight mb-3 text-foreground">
              Industrial energy<br />
              <span className="text-gradient-primary">intelligence</span>
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-10 font-inter">
              Monitor, predict, and optimize your energy systems with real-time AI analytics.
            </p>

            {/* Feature list */}
            <div className="space-y-3">
              {FEATURES.map((f) => (
                <div key={f.label} className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-xs">
                    {f.icon}
                  </div>
                  <span className="text-[12px] text-muted-foreground font-inter">{f.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom version tag */}
          <div className="relative z-10 flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse-dot" />
            <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest">v2.0 · Pipeline Ready</span>
          </div>
        </div>

        {/* Right panel — form */}
        <div className="flex-1 bg-card p-8 sm:p-10 flex flex-col justify-center">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 md:hidden">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-lg">⚡</div>
            <div className="font-head text-xl font-extrabold">Energy<span className="text-primary">Diag</span></div>
          </div>

          <div className="mb-8">
            <h1 className="font-head text-2xl font-extrabold tracking-tight mb-1.5">Welcome back</h1>
            <p className="text-[12px] text-muted-foreground font-inter">Sign in to your diagnostics dashboard</p>
          </div>

          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-[1.8px] font-head font-semibold mb-2 block">
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 rounded-xl border border-border bg-background text-[13px] text-foreground placeholder:text-muted-foreground/50 transition-all"
              />
            </div>

            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-[1.8px] font-head font-semibold mb-2 block">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-3 pr-12 rounded-xl border border-border bg-background text-[13px] text-foreground placeholder:text-muted-foreground/50 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors text-[11px] font-mono"
                >
                  {showPass ? "HIDE" : "SHOW"}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 px-3.5 py-2.5 bg-destructive/10 border border-destructive/30 rounded-lg">
                <span className="text-[10px] text-destructive">⚠</span>
                <p className="text-[11px] text-destructive font-inter">{error}</p>
              </div>
            )}

            <div className="flex items-center justify-between -mt-1">
              <div className="flex items-center gap-2">
                <input type="checkbox" id="remember" className="w-3.5 h-3.5 accent-primary" />
                <label htmlFor="remember" className="text-[11px] text-muted-foreground cursor-pointer font-inter">Remember me</label>
              </div>
              <Link to="/forgot-password" className="text-[11px] text-primary hover:text-primary/80 transition-colors font-inter">
                Forgot password?
              </Link>
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-head font-bold text-sm tracking-wide hover:opacity-90 transition-all cursor-pointer disabled:opacity-50 shadow-[0_4px_20px_rgba(0,229,255,0.2)] hover:shadow-[0_4px_28px_rgba(0,229,255,0.35)]"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  Signing in…
                </span>
              ) : "Sign In"}
            </button>
          </form>

          <p className="text-[11px] text-muted-foreground text-center mt-6 font-inter">
            Don't have an account?{" "}
            <Link to="/register" className="text-primary hover:text-primary/80 transition-colors font-semibold">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;

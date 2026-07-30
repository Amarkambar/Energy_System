import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiRegister, saveSession } from "@/lib/api";

const PasswordStrength = ({ password }: { password: string }) => {
  const checks = [
    password.length >= 6,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];
  const score = checks.filter(Boolean).length;
  const label = ["", "Weak", "Fair", "Good", "Strong"][score];
  const colors = ["", "#ff3d5a", "#ffb800", "#00e5ff", "#00ff9d"][score];

  if (!password) return null;
  return (
    <div className="mt-2">
      <div className="flex gap-1 mb-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-all duration-300"
            style={{ background: i < score ? colors : "hsl(196 30% 14%)" }}
          />
        ))}
      </div>
      <span className="text-[10px] font-inter" style={{ color: colors }}>{label}</span>
    </div>
  );
};

const RegisterPage = () => {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!name.trim() || !email.trim() || !password.trim()) { setError("Please fill in all fields"); return; }
    if (password.length < 6) { setError("Password must be at least 6 characters"); return; }
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setLoading(true);
    try {
      const { token, user } = await apiRegister(name.trim(), email.trim(), password);
      saveSession(token, user);
      navigate("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally { setLoading(false); }
  };

  const inputClass = "w-full px-4 py-3 rounded-xl border border-border bg-background text-[13px] text-foreground placeholder:text-muted-foreground/50 transition-all";
  const labelClass = "text-[10px] text-muted-foreground uppercase tracking-[1.8px] font-head font-semibold mb-2 block";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Glow orbs */}
      <div className="fixed w-[500px] h-[500px] rounded-full bg-secondary/[0.06] -top-[150px] -right-[150px] blur-[130px] pointer-events-none z-0 animate-float" />
      <div className="fixed w-[400px] h-[400px] rounded-full bg-primary/[0.05] bottom-[-100px] -left-[100px] blur-[120px] pointer-events-none z-0" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8 animate-fade-up">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-2xl shadow-[0_0_24px_rgba(0,229,255,0.25)]">
            ⚡
          </div>
          <div>
            <div className="font-head text-2xl font-extrabold tracking-tight">
              Energy<span className="text-primary">Diag</span>
            </div>
            <div className="text-[9px] text-muted-foreground uppercase tracking-widest">AI Diagnostics Platform</div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-8 shadow-[0_24px_80px_rgba(0,0,0,0.5)] animate-fade-up" style={{ animationDelay: "0.1s" }}>
          <div className="mb-7">
            <h1 className="font-head text-2xl font-extrabold tracking-tight mb-1.5">Create account</h1>
            <p className="text-[12px] text-muted-foreground font-inter">
              Start monitoring your energy systems with AI
            </p>
          </div>

          <form onSubmit={handleRegister} className="flex flex-col gap-5">
            <div>
              <label className={labelClass}>Full Name</label>
              <input
                id="register-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Amar Kambar"
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>Email Address</label>
              <input
                id="register-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>Password</label>
              <div className="relative">
                <input
                  id="register-password"
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className={`${inputClass} pr-12`}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors text-[11px] font-mono"
                >
                  {showPass ? "HIDE" : "SHOW"}
                </button>
              </div>
              <PasswordStrength password={password} />
            </div>

            <div>
              <label className={labelClass}>Confirm Password</label>
              <input
                id="register-confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                className={`${inputClass} ${confirm && confirm !== password ? "border-destructive/50" : ""}`}
              />
              {confirm && confirm !== password && (
                <p className="text-[10px] text-destructive mt-1 font-inter">Passwords don't match</p>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 px-3.5 py-2.5 bg-destructive/10 border border-destructive/30 rounded-lg">
                <span className="text-[10px] text-destructive">⚠</span>
                <p className="text-[11px] text-destructive font-inter">{error}</p>
              </div>
            )}

            <button
              id="register-submit"
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-head font-bold text-sm tracking-wide hover:opacity-90 transition-all cursor-pointer disabled:opacity-50 shadow-[0_4px_20px_rgba(0,229,255,0.2)] hover:shadow-[0_4px_28px_rgba(0,229,255,0.35)] mt-1"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  Creating account…
                </span>
              ) : "Create Account"}
            </button>
          </form>

          <p className="text-[11px] text-muted-foreground text-center mt-6 font-inter">
            Already have an account?{" "}
            <Link to="/login" className="text-primary hover:text-primary/80 transition-colors font-semibold">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;

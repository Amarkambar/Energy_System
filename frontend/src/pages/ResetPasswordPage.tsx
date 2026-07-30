import { useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { apiResetPassword } from "@/lib/api";

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const email = searchParams.get("email") || "";
  const token = searchParams.get("token") || "";  // FIX: read one-time token from URL
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  // Guard: if token or email is missing the link is invalid/expired
  if (!token || !email) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="bg-card border border-border rounded-xl p-8 max-w-md w-full text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="font-head text-xl font-bold mb-2">Invalid Reset Link</h1>
          <p className="text-muted-foreground text-sm mb-4">This password reset link is missing required information. Please request a new one.</p>
          <a href="/forgot-password" className="text-primary hover:underline text-sm">← Request new reset link</a>
        </div>
      </div>
    );
  }

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!password.trim()) { setError("Please enter a new password"); return; }
    if (password.length < 6) { setError("Password must be at least 6 characters"); return; }
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setLoading(true);
    try {
      await apiResetPassword(email, password, token);  // FIX: pass token
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative">
      <div className="fixed inset-0 z-0 pointer-events-none opacity-30" style={{ backgroundImage: "linear-gradient(hsl(196 30% 16%) 1px, transparent 1px), linear-gradient(90deg, hsl(196 30% 16%) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
      <div className="fixed w-[500px] h-[500px] rounded-full bg-primary/[0.08] top-1/4 -left-[100px] blur-[120px] pointer-events-none z-0" />
      <div className="fixed w-[400px] h-[400px] rounded-full bg-secondary/[0.06] bottom-[100px] -right-[100px] blur-[120px] pointer-events-none z-0" />
      <div className="relative z-10 w-full max-w-md">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xl">⚡</div>
          <div className="font-head text-2xl font-extrabold tracking-tight">Energy<span className="text-primary">Diag</span></div>
        </div>
        <div className="bg-card border border-border rounded-xl p-8">
          {!success ? (
            <>
              <h1 className="font-head text-xl font-bold text-center mb-1">Reset password</h1>
              <p className="text-[12px] text-muted-foreground text-center mb-6">Set a new password for <span className="text-foreground font-semibold">{email}</span></p>
              <form onSubmit={handleReset} className="flex flex-col gap-4">
                <div>
                  <label className="text-[11px] text-muted-foreground uppercase tracking-widest font-head font-semibold mb-1.5 block">New Password</label>
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 transition-colors" />
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground uppercase tracking-widest font-head font-semibold mb-1.5 block">Confirm Password</label>
                  <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 transition-colors" />
                </div>
                {error && <p className="text-[11px] text-destructive">{error}</p>}
                <button type="submit" disabled={loading} className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-head font-bold text-sm tracking-wide hover:opacity-90 transition-all cursor-pointer disabled:opacity-50">
                  {loading ? "Updating…" : "Update Password"}
                </button>
              </form>
            </>
          ) : (
            <div className="text-center py-4">
              <div className="w-14 h-14 rounded-full bg-secondary/10 flex items-center justify-center mx-auto mb-4 text-2xl">✅</div>
              <h2 className="font-head text-lg font-bold mb-2">Password updated!</h2>
              <p className="text-[12px] text-muted-foreground">Redirecting to sign in…</p>
            </div>
          )}
          <p className="text-[11px] text-muted-foreground text-center mt-5">
            <Link to="/login" className="text-primary hover:underline">← Back to sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
};
export default ResetPasswordPage;

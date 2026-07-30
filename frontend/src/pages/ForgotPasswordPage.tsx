import { useState } from "react";
import { Link } from "react-router-dom";
import { apiForgotPassword } from "@/lib/api";

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email.trim()) { setError("Please enter your email"); return; }
    setLoading(true);
    try {
      await apiForgotPassword(email.trim());
      setSent(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
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
          {!sent ? (
            <>
              <h1 className="font-head text-xl font-bold text-center mb-1">Forgot password</h1>
              <p className="text-[12px] text-muted-foreground text-center mb-6">Enter your email to reset your password</p>
              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div>
                  <label className="text-[11px] text-muted-foreground uppercase tracking-widest font-head font-semibold mb-1.5 block">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-background text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 transition-colors" />
                </div>
                {error && <p className="text-[11px] text-destructive">{error}</p>}
                <button type="submit" disabled={loading} className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-head font-bold text-sm tracking-wide hover:opacity-90 transition-all cursor-pointer disabled:opacity-50">
                  {loading ? "Checking…" : "Send Reset Link"}
                </button>
              </form>
            </>
          ) : (
            <div className="text-center py-4">
              <div className="w-14 h-14 rounded-full bg-secondary/10 flex items-center justify-center mx-auto mb-4 text-2xl">✉️</div>
              <h2 className="font-head text-lg font-bold mb-2">Check your email</h2>
              <p className="text-[12px] text-muted-foreground mb-4">We've sent a password reset link to <span className="text-foreground font-semibold">{email}</span></p>
              <Link to={`/reset-password?email=${encodeURIComponent(email)}`} className="text-[11px] text-primary hover:underline">Reset password now →</Link>
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
export default ForgotPasswordPage;

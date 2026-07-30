import { useState, useEffect } from "react";
import { useMlContext } from "@/lib/ml-context";
import { clearSession } from "@/lib/api";
import { useNavigate } from "react-router-dom";

const LiveClock = () => {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
      {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  );
};

const DashboardHeader = () => {
  const { pipelineReady, loadState } = useMlContext();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearSession();
    navigate("/login");
  };

  const isTraining = loadState === "loading";

  // Get user info
  let userName = "User";
  let userEmail = "";
  try {
    const u = JSON.parse(localStorage.getItem("energydiag_user") || "{}");
    userName = u.name || "User";
    userEmail = u.email || "";
  } catch {}

  const initials = userName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <header className="flex items-center justify-between px-8 py-4 border-b border-border bg-background/90 backdrop-blur-xl sticky top-0 z-50">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-lg shadow-[0_0_16px_rgba(0,229,255,0.2)]">
          ⚡
        </div>
        <div>
          <div className="font-head text-base font-extrabold tracking-tight leading-none">
            Energy<span className="text-primary">Diag</span>
          </div>
          <div className="text-[9px] text-muted-foreground uppercase tracking-widest mt-0.5">
            AI Diagnostics Platform
          </div>
        </div>
      </div>

      {/* Center: Status indicators */}
      <div className="hidden md:flex items-center gap-6">
        {/* Live clock */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-lg">
          <span className="text-[9px] text-muted-foreground uppercase tracking-widest">Local</span>
          <LiveClock />
        </div>

        {/* Pipeline status */}
        <div className="flex items-center gap-2">
          {isTraining ? (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-warn/8 border border-warn/20 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-warn animate-pulse-dot" />
              <span className="text-[10px] text-warn font-head font-semibold uppercase tracking-widest">Training</span>
            </div>
          ) : pipelineReady ? (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-secondary/8 border border-secondary/20 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse-dot" />
              <span className="text-[10px] text-secondary font-head font-semibold uppercase tracking-widest">Pipeline Ready</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 border border-border rounded-lg">
              <span className="w-2 h-2 rounded-full bg-muted-foreground/50" />
              <span className="text-[10px] text-muted-foreground font-head font-semibold uppercase tracking-widest">No Pipeline</span>
            </div>
          )}
        </div>
      </div>

      {/* Right: User + Logout */}
      <div className="flex items-center gap-3">
        {/* User avatar */}
        <div className="hidden sm:flex items-center gap-2.5 px-3 py-1.5 bg-card border border-border rounded-lg">
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-[9px] font-head font-extrabold text-background">
            {initials}
          </div>
          <div>
            <div className="text-[11px] font-head font-semibold text-foreground leading-none">{userName}</div>
            {userEmail && (
              <div className="text-[9px] text-muted-foreground leading-none mt-0.5">{userEmail}</div>
            )}
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="px-3 py-1.5 rounded-lg border border-border text-[11px] font-head font-semibold text-muted-foreground hover:text-foreground hover:bg-destructive/10 hover:border-destructive/30 transition-all cursor-pointer"
        >
          Logout
        </button>
      </div>
    </header>
  );
};

export default DashboardHeader;

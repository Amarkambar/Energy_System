import { useState, useEffect } from "react";
import { useMlContext } from "@/lib/ml-context";
import { clearSession } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { LayoutDashboard, LogOut, Settings } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type DashboardHeaderProps = {
  onOpenSettings: () => void;
  onOpenOverview: () => void;
};

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

const DashboardHeader = ({ onOpenSettings, onOpenOverview }: DashboardHeaderProps) => {
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
  } catch {
    // Keep the default user label when the saved profile is malformed.
  }

  const initials = userName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <header className="flex items-center justify-between gap-2 px-2.5 sm:gap-3 sm:px-8 py-4 border-b border-border bg-background/90 backdrop-blur-xl sticky top-0 z-50">
      {/* Left: Logo */}
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary text-base shadow-[0_0_16px_rgba(0,229,255,0.2)] sm:h-9 sm:w-9 sm:text-lg">
          ⚡
        </div>
        <div className="min-w-0">
          <div className="truncate font-head text-[11px] font-extrabold tracking-tight leading-none sm:text-base">
            Energy<span className="text-primary">Diag</span>
          </div>
          <div className="mt-0.5 hidden text-[9px] text-muted-foreground uppercase tracking-widest sm:block">
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

      {/* Right: Account menu */}
      <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label={`Open account menu for ${userName}`}
              className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card transition-colors hover:border-primary/50 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-[10px] font-head font-extrabold text-background">
                {initials}
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            sideOffset={10}
            collisionPadding={8}
            className="z-[60] max-h-[calc(100dvh-5.5rem)] w-[min(22rem,calc(100vw-1rem))] overflow-y-auto rounded-2xl border-border bg-card p-0 text-card-foreground shadow-2xl"
          >
            <div className="flex items-center gap-4 border-b border-border px-5 py-5">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-base font-head font-extrabold text-background">
                {initials}
              </div>
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-foreground">{userName}</p>
                {userEmail && <p className="truncate text-sm text-muted-foreground">{userEmail}</p>}
                <p className="mt-1 text-sm font-medium text-primary">Energy Diagnostics account</p>
              </div>
            </div>

            <div className="p-2">
              <DropdownMenuItem
                onSelect={onOpenOverview}
                className="min-h-11 cursor-pointer gap-3 rounded-lg px-3 text-sm focus:bg-accent"
              >
                <LayoutDashboard className="h-5 w-5 text-muted-foreground" />
                Dashboard overview
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={onOpenSettings}
                className="min-h-11 cursor-pointer gap-3 rounded-lg px-3 text-sm focus:bg-accent"
              >
                <Settings className="h-5 w-5 text-muted-foreground" />
                Settings
              </DropdownMenuItem>
            </div>

            <DropdownMenuSeparator className="my-0" />
            <div className="p-2">
              <DropdownMenuItem
                onSelect={handleLogout}
                className="min-h-11 cursor-pointer gap-3 rounded-lg px-3 text-sm text-destructive focus:bg-destructive/10 focus:text-destructive"
              >
                <LogOut className="h-5 w-5" />
                Sign out
              </DropdownMenuItem>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

export default DashboardHeader;

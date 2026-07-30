import { cn } from "@/lib/utils";

interface DashboardNavProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: "overview",  label: "Overview",    icon: "◈" },
  { id: "models",    label: "AI Models",   icon: "◉" },
  { id: "alerts",    label: "Alerts",      icon: "◬" },
  { id: "forecast",  label: "Forecast",    icon: "◎" },
  { id: "pipeline",  label: "Pipeline",    icon: "◫" },
  { id: "settings",  label: "Settings",    icon: "⚙" },
];

const DashboardNav = ({ activeTab, onTabChange }: DashboardNavProps) => (
  <nav className="flex gap-0 px-8 border-b border-border bg-background/95 backdrop-blur-sm sticky top-[69px] z-40">
    {tabs.map((tab) => {
      const isActive = activeTab === tab.id;
      return (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={cn(
            "relative flex items-center gap-1.5 px-5 py-3.5 font-head text-[12px] font-semibold tracking-wide",
            "transition-all duration-200 bg-transparent border-0 cursor-pointer outline-none",
            "hover:text-foreground",
            isActive
              ? "text-primary"
              : "text-muted-foreground"
          )}
        >
          {/* Tab icon */}
          <span className={cn(
            "text-[11px] transition-all duration-200",
            isActive ? "text-primary opacity-100" : "opacity-40"
          )}>
            {tab.icon}
          </span>

          {tab.label}

          {/* Active underline with glow */}
          {isActive && (
            <span
              className="absolute bottom-0 left-0 right-0 h-[2px] rounded-t-full"
              style={{
                background: "linear-gradient(90deg, transparent, hsl(187 100% 50%), transparent)",
                boxShadow: "0 0 8px hsl(187 100% 50% / 0.6)",
              }}
            />
          )}

          {/* Hover highlight */}
          {!isActive && (
            <span className="absolute inset-0 rounded-t-lg bg-primary/0 hover:bg-primary/[0.04] transition-colors" />
          )}
        </button>
      );
    })}
  </nav>
);

export default DashboardNav;

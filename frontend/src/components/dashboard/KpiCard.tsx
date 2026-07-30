import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  deltaType?: "up" | "down" | "neutral";
  icon?: string;
  variant?: "default" | "warn" | "danger" | "green";
  delay?: number;
}

const KpiCard = ({
  label,
  value,
  unit = "",
  delta = "",
  deltaType = "neutral",
  icon = "",
  variant = "default",
  delay = 0,
}: KpiCardProps) => {
  const topBarColor = {
    default: "from-primary via-primary/60 to-transparent",
    warn: "from-warn via-warn/60 to-transparent",
    danger: "from-destructive via-destructive/60 to-transparent",
    green: "from-secondary via-secondary/60 to-transparent",
  }[variant];

  const glowColor = {
    default:
      "hover:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_20px_rgba(0,229,255,0.08)]",
    warn:
      "hover:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_20px_rgba(255,184,0,0.08)]",
    danger:
      "hover:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_20px_rgba(255,61,90,0.08)]",
    green:
      "hover:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_20px_rgba(0,255,157,0.08)]",
  }[variant];

  const hoverBorder = {
    default: "hover:border-primary/25",
    warn: "hover:border-warn/25",
    danger: "hover:border-destructive/25",
    green: "hover:border-secondary/25",
  }[variant];

  const valueColor = {
    default: "text-foreground",
    warn: "text-warn",
    danger: "text-destructive",
    green: "text-secondary",
  }[variant];

  const deltaConfig = {
    up: {
      color: "text-destructive",
      arrow: "↑",
    },
    down: {
      color: "text-secondary",
      arrow: "↓",
    },
    neutral: {
      color: "text-muted-foreground",
      arrow: "",
    },
  }[deltaType];

  return (
    <div
      className={cn(
        "relative overflow-hidden bg-card border border-border rounded-xl p-5 animate-fade-up",
        "transition-all duration-300",
        "hover:-translate-y-0.5",
        glowColor,
        hoverBorder
      )}
      style={{ animationDelay: `${delay}s` }}
    >
      {/* Top Border */}
      <div
        className={cn(
          "absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r",
          topBarColor
        )}
      />

      {/* Background Icon */}
      {icon && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[40px] opacity-[0.06] select-none pointer-events-none">
          {icon}
        </div>
      )}

      {/* Label */}
      <div className="text-[9px] uppercase tracking-[2px] text-muted-foreground mb-3 font-semibold">
        {label}
      </div>

      {/* Value */}
      <div
        className={cn(
          "text-[26px] font-extrabold leading-none mb-2",
          valueColor
        )}
      >
        {value}
        {unit && (
          <span className="ml-1.5 text-xs font-normal text-muted-foreground">
            {unit}
          </span>
        )}
      </div>

      {/* Delta */}
      {delta && (
        <div
          className={cn(
            "text-[10px] flex items-center gap-1",
            deltaConfig.color
          )}
        >
          {deltaConfig.arrow && (
            <span className="font-bold">{deltaConfig.arrow}</span>
          )}
          <span>{delta}</span>
        </div>
      )}
    </div>
  );
};

export default KpiCard;
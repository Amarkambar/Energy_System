import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  titleRight?: string;
  delay?: number;
  className?: string;
  action?: ReactNode;
}

const ChartCard = ({ title, subtitle, children, titleRight, delay = 0, className, action }: ChartCardProps) => (
  <div
    className={cn(
      "bg-card border border-border rounded-xl p-5 animate-fade-up",
      "transition-all duration-300",
      "hover:border-border2/60",
      className
    )}
    style={{ animationDelay: `${delay}s` }}
  >
    <div className="flex items-start justify-between gap-3 mb-1">
      <div className="font-head text-[13px] font-bold text-foreground">{title}</div>
      <div className="flex items-center gap-2">
        {action}
        {titleRight && (
          <span className="text-[10px] text-muted-foreground font-inter shrink-0">{titleRight}</span>
        )}
      </div>
    </div>
    <div className="text-[9px] text-muted-foreground uppercase tracking-[1.8px] mb-4 font-head">{subtitle}</div>
    {children}
  </div>
);

export default ChartCard;

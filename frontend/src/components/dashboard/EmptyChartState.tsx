import { Upload } from "lucide-react";

interface EmptyChartStateProps {
  message?: string;
  height?: number;
}

const EmptyChartState = ({
  message = "Upload a CSV file and run analytics to see data",
  height = 180,
}: EmptyChartStateProps) => (
  <div className="flex flex-col items-center justify-center text-center" style={{ height }}>
    <div className="w-14 h-14 rounded-2xl bg-muted/30 border border-border flex items-center justify-center mb-4 animate-float">
      <Upload className="w-6 h-6 text-muted-foreground/40" />
    </div>
    <p className="text-[11px] text-muted-foreground/50 max-w-[200px] leading-relaxed font-inter">{message}</p>
    <div className="mt-3 flex gap-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-1 h-1 rounded-full bg-muted-foreground/20 animate-pulse"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  </div>
);

export default EmptyChartState;

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type CalendarProps = {
  selected?: Date;
  onSelect?: (date: Date | undefined) => void;
  fromYear?: number;
  toYear?: number;
  className?: string;
  initialFocus?: boolean;
  mode?: string;
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function Calendar({ selected, onSelect, fromYear = 2000, toYear = 2035, className }: CalendarProps) {
  const today = new Date();
  const [viewYear, setViewYear] = React.useState(selected?.getFullYear() ?? today.getFullYear());
  const [viewMonth, setViewMonth] = React.useState(selected?.getMonth() ?? today.getMonth());
  const [mode, setMode] = React.useState<"day" | "month" | "year">("day");

  const years = Array.from({ length: toYear - fromYear + 1 }, (_, i) => fromYear + i);

  // Build calendar grid
  const firstDay = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const daysInPrev = new Date(viewYear, viewMonth, 0).getDate();
  const cells: { day: number; current: boolean }[] = [];

  for (let i = firstDay - 1; i >= 0; i--)
    cells.push({ day: daysInPrev - i, current: false });
  for (let d = 1; d <= daysInMonth; d++)
    cells.push({ day: d, current: true });
  while (cells.length % 7 !== 0)
    cells.push({ day: cells.length - firstDay - daysInMonth + 1, current: false });

  const isSelected = (day: number) =>
    selected &&
    selected.getFullYear() === viewYear &&
    selected.getMonth() === viewMonth &&
    selected.getDate() === day;

  const isToday = (day: number) =>
    today.getFullYear() === viewYear &&
    today.getMonth() === viewMonth &&
    today.getDate() === day;

  const handleDayClick = (day: number, current: boolean) => {
    if (!current) return;
    const d = new Date(viewYear, viewMonth, day);
    onSelect?.(d);
  };

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
    else setViewMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
    else setViewMonth(m => m + 1);
  };

  // ── Styles ──────────────────────────────────────────────
  const navBtn = "w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all cursor-pointer border border-transparent hover:border-primary/20";

  return (
    <div className={cn("select-none w-[280px]", className)}>

      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-4 px-1">
        {mode === "day" && (
          <button onClick={prevMonth} className={navBtn}>
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}

        <div className="flex items-center gap-1 mx-auto">
          {/* Month selector */}
          <button
            onClick={() => setMode(mode === "month" ? "day" : "month")}
            className={cn(
              "px-3 py-1.5 rounded-lg text-[13px] font-head font-bold tracking-wide transition-all cursor-pointer",
              mode === "month"
                ? "bg-primary text-background shadow-[0_0_16px_rgba(0,229,255,0.3)]"
                : "text-foreground hover:bg-primary/10 hover:text-primary"
            )}
          >
            {MONTHS[viewMonth]}
          </button>

          {/* Year selector */}
          <button
            onClick={() => setMode(mode === "year" ? "day" : "year")}
            className={cn(
              "px-3 py-1.5 rounded-lg text-[13px] font-head font-bold tracking-wide transition-all cursor-pointer",
              mode === "year"
                ? "bg-primary text-background shadow-[0_0_16px_rgba(0,229,255,0.3)]"
                : "text-foreground hover:bg-primary/10 hover:text-primary"
            )}
          >
            {viewYear}
          </button>
        </div>

        {mode === "day" && (
          <button onClick={nextMonth} className={navBtn}>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* ── Month picker ── */}
      {mode === "month" && (
        <div className="grid grid-cols-3 gap-2 px-1 pb-2">
          {MONTHS.map((m, i) => (
            <button
              key={m}
              onClick={() => { setViewMonth(i); setMode("day"); }}
              className={cn(
                "py-2 rounded-lg text-[12px] font-head font-semibold transition-all cursor-pointer",
                i === viewMonth
                  ? "bg-primary text-background shadow-[0_0_12px_rgba(0,229,255,0.3)]"
                  : "text-muted-foreground hover:bg-primary/10 hover:text-primary border border-transparent hover:border-primary/20"
              )}
            >
              {m.slice(0, 3)}
            </button>
          ))}
        </div>
      )}

      {/* ── Year picker ── */}
      {mode === "year" && (
        <div className="grid grid-cols-4 gap-1.5 px-1 pb-2 max-h-[220px] overflow-y-auto scrollbar-thin">
          {years.map((y) => (
            <button
              key={y}
              onClick={() => { setViewYear(y); setMode("day"); }}
              className={cn(
                "py-2 rounded-lg text-[11px] font-head font-semibold transition-all cursor-pointer",
                y === viewYear
                  ? "bg-primary text-background shadow-[0_0_12px_rgba(0,229,255,0.3)]"
                  : y === today.getFullYear()
                    ? "text-primary border border-primary/30 hover:bg-primary/10"
                    : "text-muted-foreground hover:bg-primary/10 hover:text-primary border border-transparent hover:border-primary/20"
              )}
            >
              {y}
            </button>
          ))}
        </div>
      )}

      {/* ── Day grid ── */}
      {mode === "day" && (
        <>
          {/* Day headers */}
          <div className="grid grid-cols-7 mb-1">
            {DAYS.map((d) => (
              <div key={d} className="h-8 flex items-center justify-center text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                {d}
              </div>
            ))}
          </div>

          {/* Days */}
          <div className="grid grid-cols-7 gap-y-0.5">
            {cells.map((cell, i) => {
              const sel = cell.current && isSelected(cell.day);
              const tod = cell.current && isToday(cell.day);
              return (
                <button
                  key={i}
                  onClick={() => handleDayClick(cell.day, cell.current)}
                  disabled={!cell.current}
                  className={cn(
                    "h-9 w-full rounded-lg text-[12px] font-mono transition-all duration-150 relative",
                    !cell.current && "text-muted-foreground/20 cursor-default",
                    cell.current && !sel && !tod && "text-foreground hover:bg-primary/10 hover:text-primary cursor-pointer",
                    tod && !sel && "text-primary font-bold cursor-pointer",
                    sel && "bg-primary text-background font-bold shadow-[0_0_16px_rgba(0,229,255,0.4)] cursor-pointer",
                  )}
                >
                  {cell.day}
                  {/* Today dot */}
                  {tod && !sel && (
                    <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Selected date display */}
          {selected && (
            <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Selected</span>
              <span className="text-[12px] font-head font-bold text-primary">
                {selected.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

Calendar.displayName = "Calendar";
export { Calendar };
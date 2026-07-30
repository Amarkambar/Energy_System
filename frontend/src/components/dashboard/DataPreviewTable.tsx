import { useState, useMemo } from "react";
import { Search, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight } from "lucide-react";
import { useCsvData, CsvRow } from "@/lib/csv-context";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

const DataPreviewTable = () => {
  const { rawData, columns } = useCsvData();
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
    setPage(0);
  };

  const filtered = useMemo(() => {
    if (!search.trim()) return rawData;
    const q = search.toLowerCase();
    return rawData.filter((row) =>
      columns.some((col) => String(row[col] ?? "").toLowerCase().includes(q))
    );
  }, [rawData, columns, search]);

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sortCol] ?? "";
      const bv = b[sortCol] ?? "";
      const an = Number(av);
      const bn = Number(bv);
      if (!isNaN(an) && !isNaN(bn)) return sortDir === "asc" ? an - bn : bn - an;
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [filtered, sortCol, sortDir]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageData = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  if (rawData.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h3 className="font-head text-sm font-bold text-foreground">Raw Data Preview</h3>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            {filtered.length} of {rawData.length} rows · {columns.length} columns
          </p>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Search rows…"
            className="pl-8 pr-3 py-1.5 rounded-md border border-border bg-background text-[11px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 w-56 transition-colors"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-auto max-h-[400px]">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-muted z-10">
            <tr>
              <th className="px-3 py-2 text-left text-muted-foreground font-head font-semibold w-12">#</th>
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3 py-2 text-left text-muted-foreground font-head font-semibold cursor-pointer hover:text-foreground transition-colors whitespace-nowrap select-none"
                >
                  <span className="inline-flex items-center gap-1">
                    {col}
                    {sortCol === col ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3 text-primary" /> : <ArrowDown className="w-3 h-3 text-primary" />
                    ) : (
                      <ArrowUpDown className="w-3 h-3 opacity-30" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, i) => (
              <tr key={i} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                <td className="px-3 py-1.5 text-muted-foreground">{page * PAGE_SIZE + i + 1}</td>
                {columns.map((col) => (
                  <td key={col} className="px-3 py-1.5 text-foreground whitespace-nowrap max-w-[200px] truncate">
                    {String(row[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-3 border-t border-border">
          <span className="text-[10px] text-muted-foreground">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className={cn(
                "p-1 rounded transition-colors",
                page === 0 ? "text-muted-foreground/30 cursor-not-allowed" : "text-muted-foreground hover:text-foreground cursor-pointer"
              )}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className={cn(
                "p-1 rounded transition-colors",
                page >= totalPages - 1 ? "text-muted-foreground/30 cursor-not-allowed" : "text-muted-foreground hover:text-foreground cursor-pointer"
              )}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataPreviewTable;

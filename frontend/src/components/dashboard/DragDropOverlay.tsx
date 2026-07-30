import { useState, useCallback, useEffect } from "react";
import { Upload } from "lucide-react";
import { useCsvData } from "@/lib/csv-context";

const DragDropOverlay = ({ children }: { children: React.ReactNode }) => {
  const { uploadCsv } = useCsvData();
  const [dragging, setDragging] = useState(false);
  const [dragCount, setDragCount] = useState(0);

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCount((c) => c + 1);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCount((c) => c - 1);
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCount(0);
    setDragging(false);

    const file = e.dataTransfer?.files?.[0];
    if (file && file.name.endsWith(".csv")) {
      uploadCsv(file);
    }
  }, [uploadCsv]);

  useEffect(() => {
    setDragging(dragCount > 0);
  }, [dragCount]);

  useEffect(() => {
    const el = document;
    el.addEventListener("dragenter", handleDragEnter);
    el.addEventListener("dragleave", handleDragLeave);
    el.addEventListener("dragover", handleDragOver);
    el.addEventListener("drop", handleDrop);
    return () => {
      el.removeEventListener("dragenter", handleDragEnter);
      el.removeEventListener("dragleave", handleDragLeave);
      el.removeEventListener("dragover", handleDragOver);
      el.removeEventListener("drop", handleDrop);
    };
  }, [handleDragEnter, handleDragLeave, handleDragOver, handleDrop]);

  return (
    <div className="relative">
      {children}
      {dragging && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-4 p-10 rounded-2xl border-2 border-dashed border-primary/60 bg-card/90">
            <Upload className="w-12 h-12 text-primary animate-bounce" />
            <p className="font-head text-lg font-bold text-foreground">Drop CSV file here</p>
            <p className="text-[12px] text-muted-foreground">Release to upload and analyze</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default DragDropOverlay;

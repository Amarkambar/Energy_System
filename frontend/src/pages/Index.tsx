import { lazy, Suspense, useState } from "react";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import DashboardNav from "@/components/dashboard/DashboardNav";
import DragDropOverlay from "@/components/dashboard/DragDropOverlay";
import { CsvProvider } from "@/lib/csv-context";
import { MLDataProvider } from "@/lib/ml-context";

const OverviewPage = lazy(() => import("@/components/dashboard/OverviewPage"));
const ModelsPage = lazy(() => import("@/components/dashboard/ModelsPage"));
const AlertsPage = lazy(() => import("@/components/dashboard/AlertsPage"));
const ForecastPage = lazy(() => import("@/components/dashboard/ForecastPage"));
const PipelinePage = lazy(() => import("@/components/dashboard/PipelinePage"));
const SettingsPage = lazy(() => import("@/components/dashboard/SettingsPage"));

const Index = () => {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <CsvProvider>
      <MLDataProvider>
        <DragDropOverlay>
          <div className="relative z-[1]">
            {/* Glow orbs */}
            <div className="fixed w-[500px] h-[500px] rounded-full bg-primary/[0.06] -top-[100px] -left-[100px] blur-[120px] pointer-events-none z-0" />
            <div className="fixed w-[400px] h-[400px] rounded-full bg-secondary/[0.05] bottom-[100px] -right-[100px] blur-[120px] pointer-events-none z-0" />

            <DashboardHeader
              onOpenSettings={() => setActiveTab("settings")}
              onOpenOverview={() => setActiveTab("overview")}
            />
            <DashboardNav activeTab={activeTab} onTabChange={setActiveTab} />

            <main className="p-7 px-8 max-md:p-4">
              <Suspense fallback={<div className="py-10 text-center text-sm text-muted-foreground">Loading dashboard…</div>}>
                {activeTab === "overview"  && <OverviewPage />}
                {activeTab === "models"    && <ModelsPage />}
                {activeTab === "alerts"    && <AlertsPage />}
                {activeTab === "forecast"  && <ForecastPage />}
                {activeTab === "pipeline"  && <PipelinePage />}
                {activeTab === "settings"  && <SettingsPage />}
              </Suspense>
            </main>
          </div>
        </DragDropOverlay>
      </MLDataProvider>
    </CsvProvider>
  );
};

export default Index;

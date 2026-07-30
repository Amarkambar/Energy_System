import { useState } from "react";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import DashboardNav from "@/components/dashboard/DashboardNav";
import OverviewPage from "@/components/dashboard/OverviewPage";
import ModelsPage from "@/components/dashboard/ModelsPage";
import AlertsPage from "@/components/dashboard/AlertsPage";
import ForecastPage from "@/components/dashboard/ForecastPage";
import PipelinePage from "@/components/dashboard/PipelinePage";
import SettingsPage from "@/components/dashboard/SettingsPage";
import DragDropOverlay from "@/components/dashboard/DragDropOverlay";
import { CsvProvider } from "@/lib/csv-context";
import { MLDataProvider } from "@/lib/ml-context";

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

            <DashboardHeader />
            <DashboardNav activeTab={activeTab} onTabChange={setActiveTab} />

            <main className="p-7 px-8 max-md:p-4">
              {activeTab === "overview"  && <OverviewPage />}
              {activeTab === "models"    && <ModelsPage />}
              {activeTab === "alerts"    && <AlertsPage />}
              {activeTab === "forecast"  && <ForecastPage />}
              {activeTab === "pipeline"  && <PipelinePage />}
              {activeTab === "settings"  && <SettingsPage />}
            </main>
          </div>
        </DragDropOverlay>
      </MLDataProvider>
    </CsvProvider>
  );
};

export default Index;

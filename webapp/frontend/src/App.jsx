import { Navigate, Route, Routes } from "react-router-dom";
import { Waypoints } from "lucide-react";
import NavTabs from "./components/NavTabs";
import SampleDataTab from "./features/sampleData/SampleDataTab";
import RunPipelineTab from "./features/runPipeline/RunPipelineTab";
import ResultsTab from "./features/results/ResultsTab";

const TABS = [
  { path: "/sample", label: "Sample Data" },
  { path: "/run", label: "Run Pipeline" },
  { path: "/results", label: "Results" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line-soft bg-white/70 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
              <Waypoints size={20} strokeWidth={2.25} />
            </span>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-ink">
                Candidate Data Transformer
              </h1>
              <p className="text-sm text-ink-soft">
                HR data pipeline — sample, run, inspect
              </p>
            </div>
          </div>
          <NavTabs tabs={TABS} />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/sample" replace />} />
          <Route path="/sample" element={<SampleDataTab />} />
          <Route path="/run" element={<RunPipelineTab />} />
          <Route path="/results" element={<ResultsTab />} />
          <Route path="*" element={<Navigate to="/sample" replace />} />
        </Routes>
      </main>
    </div>
  );
}

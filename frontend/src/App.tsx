import { useState } from "react";
import { ChevronDown } from "lucide-react";
import PaperUpload from "./components/PaperUpload";
import TranslatorPanel from "./components/TranslatorPanel";

function App() {
  const [uploadOpen, setUploadOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
      {/* Header */}
      <header className="border-b border-slate-200/80 bg-white/70 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/favicon.png" alt="GAIA Lab" className="w-9 h-9 rounded-lg shadow-sm" />
            <div>
              <h1 className="text-lg font-bold text-slate-800 tracking-tight">
                GAIA Translator
              </h1>
              <p className="text-[11px] text-slate-400 -mt-0.5">
                Interdisciplinary Geohazard Knowledge Bridge
              </p>
            </div>
          </div>

          <button
            onClick={() => setUploadOpen((v) => !v)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                       text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50
                       transition-colors"
          >
            Add Paper
            <ChevronDown
              className={`w-3.5 h-3.5 transition-transform ${uploadOpen ? "rotate-180" : ""}`}
            />
          </button>
        </div>
      </header>

      {/* Upload panel */}
      {uploadOpen && (
        <div className="max-w-6xl mx-auto px-6 pt-4">
          <PaperUpload />
        </div>
      )}

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <TranslatorPanel />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/60 mt-12">
        <div className="max-w-6xl mx-auto px-6 py-4 text-center">
          <p className="text-[11px] text-slate-400">
            GAIA -- Bridging soil understanding across hydrology, seismology, atmospheric science,
            climatology, geology, computer science, and applied mathematics
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;

import { Upload } from "lucide-react";
import { useCallback, useState } from "react";
import TranslatorPanel from "./components/TranslatorPanel";
import { triggerIngest } from "./lib/api";

function App() {
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<string | null>(null);

  const handleIngest = useCallback(async () => {
    setIngesting(true);
    setIngestResult(null);
    try {
      const result = await triggerIngest();
      if (result.papers_ingested === 0) {
        setIngestResult("No new papers found in data/papers/");
      } else {
        setIngestResult(
          `Ingested ${result.papers_ingested} paper(s): ${result.total_chunks} chunks, ${result.total_figures} figures`
        );
      }
    } catch {
      setIngestResult("Ingestion failed -- is the backend running?");
    } finally {
      setIngesting(false);
    }
  }, []);

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
            onClick={handleIngest}
            disabled={ingesting}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium 
                       text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 
                       transition-colors disabled:opacity-50"
          >
            <Upload className="w-3.5 h-3.5" />
            {ingesting ? "Ingesting..." : "Ingest Papers"}
          </button>
        </div>
      </header>

      {/* Ingest notification */}
      {ingestResult && (
        <div className="max-w-6xl mx-auto px-6 pt-3">
          <div className="text-xs px-3 py-2 rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
            {ingestResult}
          </div>
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

import { Image, X } from "lucide-react";
import { useState } from "react";
import { getFigureUrl } from "../lib/api";
import type { FigureRef } from "../types";

interface Props {
  figures: FigureRef[];
}

export default function FigureViewer({ figures }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (figures.length === 0) return null;

  return (
    <>
      <div className="border-t border-slate-200 bg-slate-50/50">
        <div className="px-5 py-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Referenced Figures
          </h3>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {figures.map((fig) => (
              <button
                key={fig.figure_id}
                onClick={() => setExpanded(fig.figure_id)}
                className="flex-shrink-0 group relative rounded-lg border border-slate-200 bg-white 
                           overflow-hidden hover:border-blue-400 transition-colors w-32"
              >
                <div className="aspect-[4/3] bg-slate-100 flex items-center justify-center">
                  <img
                    src={getFigureUrl(fig.figure_id)}
                    alt={fig.caption || "Figure"}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                      (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
                    }}
                  />
                  <Image className="w-8 h-8 text-slate-300 hidden" />
                </div>
                <div className="p-2">
                  <p className="text-[10px] text-slate-500 truncate">
                    {fig.caption || `Page ${fig.page}`}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {expanded && (
        <div
          className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-8"
          onClick={() => setExpanded(null)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b">
              <p className="text-sm font-medium text-slate-700">
                {figures.find((f) => f.figure_id === expanded)?.caption || "Figure"}
              </p>
              <button
                onClick={() => setExpanded(null)}
                className="p-1 hover:bg-slate-100 rounded"
              >
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>
            <div className="p-4 flex items-center justify-center">
              <img
                src={getFigureUrl(expanded)}
                alt="Figure"
                className="max-w-full max-h-[60vh] object-contain"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

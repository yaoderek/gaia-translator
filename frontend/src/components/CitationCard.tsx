import { ExternalLink, FileText } from "lucide-react";
import type { Citation } from "../types";

interface Props {
  citations: Citation[];
}

export default function CitationPanel({ citations }: Props) {
  if (citations.length === 0) return null;

  return (
    <div className="border-t border-slate-200 bg-slate-50/50">
      <div className="px-5 py-3">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          References
        </h3>
        <div className="space-y-2">
          {citations.map((c) => (
            <a
              key={c.index}
              href={`/api/papers/${c.paper_id}/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 bg-white rounded-lg border border-slate-200 p-3 
                         hover:border-blue-400 hover:bg-blue-50/30 transition-colors cursor-pointer
                         no-underline group"
            >
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 
                             text-xs font-bold flex items-center justify-center mt-0.5">
                {c.index}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800 leading-snug group-hover:text-blue-700 transition-colors">
                  {c.title || "Untitled paper"}
                </p>
                {c.authors && (
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{c.authors}</p>
                )}
                {c.excerpt && (
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{c.excerpt}</p>
                )}
                {c.doi && (
                  <span
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      window.open(`https://doi.org/${c.doi}`, "_blank");
                    }}
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 mt-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    {c.doi}
                  </span>
                )}
              </div>
              <FileText className="w-4 h-4 text-slate-300 group-hover:text-blue-400 flex-shrink-0 mt-0.5 transition-colors" />
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

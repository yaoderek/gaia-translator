import { ArrowRightLeft, Loader2, Sparkles } from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslate } from "../hooks/useTranslate";
import type { Discipline } from "../types";
import ChatThread from "./ChatThread";
import CitationPanel from "./CitationCard";
import DisciplineSelector from "./DisciplineSelector";
import FigureViewer from "./FigureViewer";
import TranslationOutput from "./TranslationOutput";

export default function TranslatorPanel() {
  const [sourceDiscipline, setSourceDiscipline] = useState<Discipline>("seismology");
  const [targetDiscipline, setTargetDiscipline] = useState<Discipline>("hydrology");
  const [inputText, setInputText] = useState("");

  const {
    translationText,
    citations,
    figures,
    followUpQuestions,
    isStreaming,
    error,
    translate,
  } = useTranslate();

  const handleTranslate = useCallback(() => {
    if (!inputText.trim() || isStreaming) return;
    translate(inputText, sourceDiscipline, targetDiscipline);
  }, [inputText, sourceDiscipline, targetDiscipline, isStreaming, translate]);

  const handleSwap = useCallback(() => {
    setSourceDiscipline(targetDiscipline);
    setTargetDiscipline(sourceDiscipline);
  }, [sourceDiscipline, targetDiscipline]);

  const handleFollowUp = useCallback(
    (text: string) => {
      setInputText(text);
      translate(text, sourceDiscipline, targetDiscipline);
    },
    [sourceDiscipline, targetDiscipline, translate]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleTranslate();
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Discipline selectors */}
      <div className="flex items-center justify-center gap-4 mb-6">
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] uppercase tracking-widest text-slate-400 font-medium">
            From
          </span>
          <DisciplineSelector
            value={sourceDiscipline}
            onChange={setSourceDiscipline}
          />
        </div>

        <button
          onClick={handleSwap}
          className="p-2 rounded-full border border-slate-200 hover:border-blue-400 
                     hover:bg-blue-50 transition-all mt-4"
          title="Swap disciplines"
        >
          <ArrowRightLeft className="w-4 h-4 text-slate-500" />
        </button>

        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] uppercase tracking-widest text-slate-400 font-medium">
            To
          </span>
          <DisciplineSelector
            value={targetDiscipline}
            onChange={setTargetDiscipline}
          />
        </div>
      </div>

      {/* Main two-panel area */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-0 bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
        {/* Input panel */}
        <div className="flex flex-col border-r border-slate-200">
          <div className="flex-1 relative">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Enter ${sourceDiscipline.replace(/_/g, " ")} text to translate...`}
              className="w-full h-full min-h-[280px] p-4 text-sm text-slate-800 
                         placeholder:text-slate-400 resize-none border-0 focus:outline-none 
                         focus:ring-0 bg-transparent leading-relaxed"
            />
          </div>
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50/50">
            <span className="text-xs text-slate-400">
              {inputText.length > 0 ? `${inputText.split(/\s+/).filter(Boolean).length} words` : ""}
            </span>
            <button
              onClick={handleTranslate}
              disabled={!inputText.trim() || isStreaming}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white 
                         text-sm font-medium rounded-lg hover:bg-blue-600 transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {isStreaming ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Translating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Translate
                </>
              )}
            </button>
          </div>
        </div>

        {/* Output panel */}
        <div className="flex flex-col">
          <div className="flex-1 min-h-[280px]">
            <TranslationOutput
              text={translationText}
              isStreaming={isStreaming}
              error={error}
            />
          </div>
        </div>
      </div>

      {/* Citations and figures */}
      {(citations.length > 0 || figures.length > 0) && (
        <div className="mt-0 bg-white rounded-b-xl shadow-lg border border-t-0 border-slate-200 overflow-hidden -mt-px">
          <CitationPanel citations={citations} />
          <FigureViewer figures={figures} />
        </div>
      )}

      {/* Follow-up thread */}
      {(followUpQuestions.length > 0 || translationText) && !isStreaming && (
        <div className="mt-4 bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
          <ChatThread
            followUpQuestions={followUpQuestions}
            onSend={handleFollowUp}
            disabled={isStreaming}
          />
        </div>
      )}
    </div>
  );
}

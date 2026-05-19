import { ArrowRightLeft, Loader2, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTranslate } from "../hooks/useTranslate";
import type { Discipline, TargetDiscipline } from "../types";
import ChatThread from "./ChatThread";
import CitationPanel from "./CitationCard";
import DisciplineSelector from "./DisciplineSelector";
import FigureViewer from "./FigureViewer";
import TranslationOutput from "./TranslationOutput";

const DISCIPLINES: Discipline[] = [
  "hydrology",
  "seismology",
  "atmospheric_science",
  "climatology",
  "geology",
  "computer_science",
  "applied_mathematics",
];

export default function TranslatorPanel() {
  const { user, me } = useAuth();
  const [sourceDiscipline, setSourceDiscipline] = useState<Discipline>("seismology");
  const [targetDiscipline, setTargetDiscipline] = useState<TargetDiscipline>("hydrology");
  const [inputText, setInputText] = useState("");

  const {
    translationText,
    citations,
    figures,
    followUpQuestions,
    isStreaming,
    error,
    isPersonalized,
    translate,
  } = useTranslate();

  useEffect(() => {
    if (user) {
      setTargetDiscipline((prev) => (prev === "personalized" ? prev : "personalized"));
    } else {
      setTargetDiscipline((prev) => (prev === "personalized" ? "hydrology" : prev));
    }
  }, [user]);

  const resolveTargetForApi = useCallback((): Discipline => {
    if (targetDiscipline !== "personalized") return targetDiscipline;
    const personaDisc = me?.persona?.discipline;
    return personaDisc && DISCIPLINES.includes(personaDisc as Discipline)
      ? (personaDisc as Discipline)
      : "computer_science";
  }, [targetDiscipline, me?.persona?.discipline]);

  const handleTranslate = useCallback(() => {
    if (!inputText.trim() || isStreaming) return;
    translate(inputText, sourceDiscipline, resolveTargetForApi());
  }, [inputText, sourceDiscipline, resolveTargetForApi, isStreaming, translate]);

  const handleSwap = useCallback(() => {
    if (targetDiscipline === "personalized") {
      setTargetDiscipline(sourceDiscipline);
      setSourceDiscipline("hydrology");
    } else {
      setSourceDiscipline(targetDiscipline);
      setTargetDiscipline(sourceDiscipline);
    }
  }, [sourceDiscipline, targetDiscipline]);

  const handleFollowUp = useCallback(
    (text: string) => {
      setInputText(text);
      translate(text, sourceDiscipline, resolveTargetForApi());
    },
    [sourceDiscipline, resolveTargetForApi, translate]
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
            exclude={targetDiscipline === "personalized" ? undefined : targetDiscipline}
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
          {user ? (
            <DisciplineSelector
              allowPersonalized
              value={targetDiscipline}
              onChange={setTargetDiscipline}
              exclude={sourceDiscipline}
            />
          ) : (
            <DisciplineSelector
              value={targetDiscipline as Discipline}
              onChange={setTargetDiscipline}
              exclude={sourceDiscipline}
            />
          )}
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
          {isPersonalized && (
            <div className="px-4 py-1.5 border-b border-slate-100 bg-blue-50/70 flex items-center gap-1.5 text-xs text-blue-700">
              <Sparkles className="w-3.5 h-3.5" />
              Personalized to you
            </div>
          )}
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

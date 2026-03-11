import { Loader2 } from "lucide-react";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { AccordionSection } from "./Accordion";

interface Props {
  text: string;
  isStreaming: boolean;
  error: string | null;
}

interface ParsedSections {
  overview: string;
  relevance: string;
  workstreams: string;
}

const SECTION_RE = /<!--\s*SECTION:\s*(overview|relevance|workstreams)\s*-->/gi;

function parseSections(text: string): ParsedSections | null {
  const markers = [...text.matchAll(SECTION_RE)];
  if (markers.length === 0) return null;

  const sectionMap: Record<string, string> = {};
  for (let i = 0; i < markers.length; i++) {
    const key = markers[i][1].toLowerCase();
    const start = markers[i].index! + markers[i][0].length;
    const end = i + 1 < markers.length ? markers[i + 1].index! : text.length;
    sectionMap[key] = text.slice(start, end).trim();
  }

  if (!sectionMap.overview && !sectionMap.relevance && !sectionMap.workstreams) {
    return null;
  }

  return {
    overview: sectionMap.overview || "",
    relevance: sectionMap.relevance || "",
    workstreams: sectionMap.workstreams || "",
  };
}

const SECTION_TITLES: Record<keyof ParsedSections, string> = {
  overview: "Overview",
  relevance: "Why This Matters",
  workstreams: "Domain Workstreams",
};

const proseClasses =
  "prose prose-sm prose-slate max-w-none leading-relaxed prose-strong:text-slate-900 prose-p:my-2";

function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className={proseClasses}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

export default function TranslationOutput({ text, isStreaming, error }: Props) {
  const sections = useMemo(() => parseSections(text), [text]);

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-red-500 text-sm bg-red-50 rounded-lg p-4 max-w-md">
          <p className="font-medium mb-1">Translation failed</p>
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!text && !isStreaming) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <p className="text-slate-400 text-sm text-center leading-relaxed max-w-xs">
          Translation will appear here. Select your disciplines and enter text
          to translate.
        </p>
      </div>
    );
  }

  const streamingIndicator = isStreaming && (
    <span className="inline-flex items-center gap-1 mt-2 text-blue-500">
      <Loader2 className="w-3 h-3 animate-spin" />
      <span className="text-xs">translating...</span>
    </span>
  );

  if (!sections) {
    return (
      <div className="h-full p-4 overflow-y-auto">
        <div className={proseClasses}>
          <ReactMarkdown>{text}</ReactMarkdown>
        </div>
        {streamingIndicator}
      </div>
    );
  }

  return (
    <div className="h-full p-4 overflow-y-auto space-y-2">
      {(["overview", "relevance", "workstreams"] as const).map(
        (key) =>
          sections[key] && (
            <AccordionSection key={key} title={SECTION_TITLES[key]}>
              <MarkdownBlock content={sections[key]} />
            </AccordionSection>
          )
      )}
      {streamingIndicator}
    </div>
  );
}

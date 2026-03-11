import { Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Props {
  text: string;
  isStreaming: boolean;
  error: string | null;
}

export default function TranslationOutput({ text, isStreaming, error }: Props) {
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
          Translation will appear here. Select your disciplines and enter text to translate.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full p-4 overflow-y-auto">
      <div className="prose prose-sm prose-slate max-w-none leading-relaxed
                      prose-strong:text-slate-900 prose-p:my-2">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
      {isStreaming && (
        <span className="inline-flex items-center gap-1 mt-1 text-blue-500">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span className="text-xs">translating...</span>
        </span>
      )}
    </div>
  );
}

import { ArrowUp } from "lucide-react";
import { useState } from "react";

interface Props {
  followUpQuestions: string[];
  onSend: (text: string) => void;
  disabled: boolean;
}

export default function ChatThread({ followUpQuestions, onSend, disabled }: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <div className="border-t border-slate-200 bg-white">
      {followUpQuestions.length > 0 && (
        <div className="px-5 py-3 border-b border-slate-100">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Potentially Relevant Domain Workstreams
          </p>
          <div className="flex flex-wrap gap-2">
            {followUpQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => onSend(q)}
                disabled={disabled}
                className="text-xs bg-blue-50 text-blue-700 rounded-full px-3 py-1.5
                           hover:bg-blue-100 transition-colors disabled:opacity-50 
                           disabled:cursor-not-allowed text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-5 py-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a follow-up question..."
          disabled={disabled}
          className="flex-1 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2
                     placeholder:text-slate-400 focus:outline-none focus:border-blue-400 
                     focus:ring-1 focus:ring-blue-400 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 
                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}

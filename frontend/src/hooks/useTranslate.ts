import { useCallback, useRef, useState } from "react";
import type { Citation, Discipline, FigureRef } from "../types";

interface TranslateState {
  translationText: string;
  citations: Citation[];
  figures: FigureRef[];
  followUpQuestions: string[];
  isStreaming: boolean;
  error: string | null;
}

export function useTranslate() {
  const [state, setState] = useState<TranslateState>({
    translationText: "",
    citations: [],
    figures: [],
    followUpQuestions: [],
    isStreaming: false,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const translate = useCallback(
    async (text: string, source: Discipline, target: Discipline) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState({
        translationText: "",
        citations: [],
        figures: [],
        followUpQuestions: [],
        isStreaming: true,
        error: null,
      });

      try {
        const resp = await fetch("/api/translate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text,
            source_discipline: source,
            target_discipline: target,
          }),
          signal: controller.signal,
        });

        if (!resp.ok) {
          throw new Error(`Server error: ${resp.status}`);
        }

        const reader = resp.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let fullText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data:")) continue;
            const payload = trimmed.slice(5).trim();
            if (payload === "[DONE]") continue;

            try {
              const event = JSON.parse(payload);
              if (event.type === "metadata") {
                setState((prev) => ({
                  ...prev,
                  citations: event.citations || [],
                  figures: event.figures || [],
                }));
              } else if (event.type === "token") {
                fullText += event.content;
                setState((prev) => ({
                  ...prev,
                  translationText: fullText,
                }));
              } else if (event.type === "follow_ups") {
                setState((prev) => ({
                  ...prev,
                  followUpQuestions: event.questions || [],
                }));
              }
            } catch {
              // skip malformed events
            }
          }
        }

        setState((prev) => ({ ...prev, isStreaming: false }));
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: err instanceof Error ? err.message : "Translation failed",
        }));
      }
    },
    []
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  return { ...state, translate, cancel };
}

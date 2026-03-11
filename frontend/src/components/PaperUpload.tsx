import { FileUp, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { uploadPaper } from "../lib/api";

type UploadStatus =
  | { state: "idle" }
  | { state: "uploading"; filename: string }
  | { state: "success"; message: string }
  | { state: "error"; message: string };

export default function PaperUpload() {
  const [status, setStatus] = useState<UploadStatus>({ state: "idle" });
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setStatus({ state: "error", message: "Only PDF files are accepted" });
      return;
    }
    setStatus({ state: "uploading", filename: file.name });
    try {
      const result = await uploadPaper(file);
      if (result.status === "skipped") {
        setStatus({ state: "success", message: `"${file.name}" was already ingested` });
      } else {
        setStatus({
          state: "success",
          message: `Ingested "${result.title || file.name}": ${result.num_chunks} chunks, ${result.num_figures} figures`,
        });
      }
    } catch (err) {
      setStatus({
        state: "error",
        message: err instanceof Error ? err.message : "Upload failed",
      });
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = "";
    },
    [handleFile]
  );

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed
                    rounded-lg p-6 cursor-pointer transition-colors text-center
                    ${
                      dragOver
                        ? "border-blue-400 bg-blue-50/50"
                        : "border-slate-200 hover:border-blue-300 hover:bg-slate-50/50"
                    }`}
      >
        {status.state === "uploading" ? (
          <>
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
            <p className="text-sm text-slate-600">
              Ingesting <span className="font-medium">{status.filename}</span>...
            </p>
            <p className="text-xs text-slate-400">
              Extracting text, figures, and generating embeddings
            </p>
          </>
        ) : (
          <>
            <FileUp className="w-6 h-6 text-slate-400" />
            <p className="text-sm text-slate-600">
              Drop a PDF here or <span className="text-blue-600 font-medium">browse</span>
            </p>
            <p className="text-xs text-slate-400">Papers are processed and added to the knowledge base</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          onChange={onFileSelect}
          className="hidden"
        />
      </div>

      {status.state === "success" && (
        <div className="flex items-start gap-2 text-xs px-3 py-2 rounded-lg bg-green-50 text-green-700 border border-green-200">
          <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>{status.message}</span>
        </div>
      )}
      {status.state === "error" && (
        <div className="flex items-start gap-2 text-xs px-3 py-2 rounded-lg bg-red-50 text-red-700 border border-red-200">
          <XCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>{status.message}</span>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { fetchDisciplines, updatePersona } from "../lib/api";
import type { DisciplineInfo } from "../types";

interface PersonaModalProps {
  open: boolean;
  onClose: () => void;
}

const SUGGESTED_TAGS = [
  "machine learning", "time series", "landslide", "earthquake", "flood",
  "remote sensing", "numerical modeling", "data assimilation", "field work",
  "signal processing", "GIS", "Python", "MATLAB", "R",
];

export default function PersonaModal({ open, onClose }: PersonaModalProps) {
  const { me, refetchMe } = useAuth();
  const [disciplines, setDisciplines] = useState<DisciplineInfo[]>([]);
  const [username, setUsername] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [bio, setBio] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDisciplines().then(setDisciplines);
  }, []);

  useEffect(() => {
    if (open && me) {
      setUsername(me.persona?.username ?? me.username ?? "");
      setDiscipline(me.persona?.discipline ?? "");
      setBio(me.persona?.bio ?? "");
      const existingTags = (me.persona?.tags ?? "")
        .split(",")
        .map((t) => t.trim())
        .filter((t): t is string => t.length > 0);
      setTags(existingTags);
      setError(null);
      setSaved(false);
    }
  }, [open, me]);

  const addTag = (tag: string) => {
    const t = tag.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags((prev) => [...prev, t]);
    setTagInput("");
  };

  const removeTag = (tag: string) => setTags((prev) => prev.filter((t) => t !== tag));

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(tagInput);
    } else if (e.key === "Backspace" && !tagInput && tags.length > 0) {
      setTags((prev) => prev.slice(0, -1));
    }
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await updatePersona({
        username: username.trim() || undefined,
        discipline: discipline || undefined,
        bio: bio || undefined,
        tags: tags.join(", ") || undefined,
      });
      await refetchMe();
      setSaved(true);
      setTimeout(onClose, 800);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      const fallback = err instanceof Error ? err.message : "Save failed";
      setError(typeof msg === "string" ? msg : Array.isArray(msg) ? (msg as string[]).join(", ") : fallback);
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-800">My profile</h2>
        <p className="mt-1 text-xs text-slate-500">
          Tell us about yourself so translations can be tailored to your background and vocabulary.
        </p>

        <form onSubmit={save} className="mt-4 space-y-4">
          {/* Username */}
          <div>
            <label className="block text-xs font-medium text-slate-600">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. mdenolle"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </div>

          {/* Primary discipline */}
          <div>
            <label className="block text-xs font-medium text-slate-600">Primary discipline</label>
            <select
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
            >
              <option value="">— Select —</option>
              {disciplines.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </div>

          {/* Bio */}
          <div>
            <label className="block text-xs font-medium text-slate-600">About your work</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="e.g. I build ML pipelines for landslide prediction; I care about temporal resolution and feature engineering; I'm less familiar with seismic velocity but need to connect it to model inputs."
              rows={4}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm resize-none"
            />
            <p className="mt-1 text-[11px] text-slate-400">
              The translator uses this to match your vocabulary and workstreams.
            </p>
          </div>

          {/* Specialization tags */}
          <div>
            <label className="block text-xs font-medium text-slate-600">Specialization tags</label>
            <div className="mt-1 flex flex-wrap gap-1.5 min-h-[36px] rounded-lg border border-slate-200 px-2 py-1.5 focus-within:ring-1 focus-within:ring-blue-400">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs"
                >
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)} className="hover:text-blue-900 leading-none">×</button>
                </span>
              ))}
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                onBlur={() => tagInput.trim() && addTag(tagInput)}
                placeholder={tags.length === 0 ? "Type a tag and press Enter…" : ""}
                className="flex-1 min-w-[120px] outline-none text-xs py-0.5 bg-transparent"
              />
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {SUGGESTED_TAGS.filter((t) => !tags.includes(t)).slice(0, 8).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => addTag(t)}
                  className="px-2 py-0.5 rounded-full border border-slate-200 text-[11px] text-slate-500 hover:border-blue-300 hover:text-blue-600"
                >
                  + {t}
                </button>
              ))}
            </div>
          </div>

          {saved && <p className="text-xs text-green-600 font-medium">Saved!</p>}
          {error && (
            <p className="text-xs text-red-600 rounded bg-red-50 px-2 py-1.5" role="alert">{error}</p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save profile"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              Close
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

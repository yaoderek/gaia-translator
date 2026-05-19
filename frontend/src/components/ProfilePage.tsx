import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { fetchDisciplines, updatePersona } from "../lib/api";
import type { DisciplineInfo } from "../types";

interface ProfilePageProps {
  onClose?: () => void;
}

const FIELD_HINTS = {
  papers_of_interest:
    "Papers you've read, written, or want to reference. One per line. Titles, DOIs, or short refs (e.g. 'Denolle 2025 — ambient field seismology').",
  concepts_focus:
    "Concepts and topics you want translations to emphasize. One per line or comma-separated (e.g. 'pore pressure, coda waves, slope stability').",
  methods_focus:
    "Methodologies you want to use or learn about. (e.g. 'ambient-noise interferometry, finite-element modeling, deep learning for time series').",
  tech_stack:
    "Tools, languages, libraries you work with. Translations will frame examples in these terms. (e.g. 'Python, ObsPy, PyTorch, GMT, QGIS').",
};

export default function ProfilePage({ onClose }: ProfilePageProps) {
  const { me, refetchMe } = useAuth();
  const [disciplines, setDisciplines] = useState<DisciplineInfo[]>([]);
  const [form, setForm] = useState({
    username: "",
    discipline: "",
    bio: "",
    tags: "",
    papers_of_interest: "",
    concepts_focus: "",
    methods_focus: "",
    tech_stack: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDisciplines().then(setDisciplines);
  }, []);

  useEffect(() => {
    if (me?.persona) {
      setForm({
        username: me.persona.username || me.username || "",
        discipline: me.persona.discipline || "",
        bio: me.persona.bio || "",
        tags: me.persona.tags || "",
        papers_of_interest: me.persona.papers_of_interest || "",
        concepts_focus: me.persona.concepts_focus || "",
        methods_focus: me.persona.methods_focus || "",
        tech_stack: me.persona.tech_stack || "",
      });
    }
  }, [me]);

  const update = <K extends keyof typeof form>(key: K, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await updatePersona({
        username: form.username.trim() || undefined,
        discipline: form.discipline || "",
        bio: form.bio || "",
        tags: form.tags || "",
        papers_of_interest: form.papers_of_interest || "",
        concepts_focus: form.concepts_focus || "",
        methods_focus: form.methods_focus || "",
        tech_stack: form.tech_stack || "",
      });
      await refetchMe();
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      const fallback = err instanceof Error ? err.message : "Save failed";
      setError(typeof msg === "string" ? msg : fallback);
    } finally {
      setSaving(false);
    }
  };

  if (!me) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-sm text-slate-600">Log in to access your profile.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-800">My profile</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            The translator uses these fields to personalize retrieval and framing.
            Leave any field blank to skip it.
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-50"
          >
            ← Back to translator
          </button>
        )}
      </div>

      <form onSubmit={save} className="px-6 py-5 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600">Username</label>
            <input
              type="text"
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              placeholder="e.g. mdenolle"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600">Primary discipline</label>
            <select
              value={form.discipline}
              onChange={(e) => update("discipline", e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm bg-white"
            >
              <option value="">— Select —</option>
              {disciplines.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600">About your work</label>
          <textarea
            value={form.bio}
            onChange={(e) => update("bio", e.target.value)}
            placeholder="A few sentences on what you do and what kind of explanations you want."
            rows={3}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm resize-y"
          />
        </div>

        <FieldArea
          label="Papers of interest"
          hint={FIELD_HINTS.papers_of_interest}
          value={form.papers_of_interest}
          onChange={(v) => update("papers_of_interest", v)}
          rows={5}
        />
        <FieldArea
          label="Concepts to focus on"
          hint={FIELD_HINTS.concepts_focus}
          value={form.concepts_focus}
          onChange={(v) => update("concepts_focus", v)}
          rows={3}
        />
        <FieldArea
          label="Methodologies"
          hint={FIELD_HINTS.methods_focus}
          value={form.methods_focus}
          onChange={(v) => update("methods_focus", v)}
          rows={3}
        />
        <FieldArea
          label="Tech stack"
          hint={FIELD_HINTS.tech_stack}
          value={form.tech_stack}
          onChange={(v) => update("tech_stack", v)}
          rows={3}
        />

        <FieldArea
          label="Tags (comma-separated)"
          hint="Free-form tags. Useful for quick keyword matching."
          value={form.tags}
          onChange={(v) => update("tags", v)}
          rows={2}
        />

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
          {saved && <span className="text-xs text-green-600 font-medium">Saved.</span>}
          {error && (
            <span className="text-xs text-red-600 rounded bg-red-50 px-2 py-1">{error}</span>
          )}
        </div>
      </form>
    </div>
  );
}

function FieldArea({
  label,
  hint,
  value,
  onChange,
  rows,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  rows: number;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600">{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm resize-y font-mono leading-relaxed"
      />
      <p className="mt-1 text-[11px] text-slate-400">{hint}</p>
    </div>
  );
}

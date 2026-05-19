import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
}

export default function LoginModal({ open, onClose }: LoginModalProps) {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const switchMode = () => {
    setIsSignUp((v) => !v);
    setError(null);
    setInfo(null);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setLoading(true);
    try {
      if (isSignUp) {
        await signUp(email, password, username.trim());
        setInfo("Check your email to confirm your account, then log in.");
      } else {
        await signIn(email, password);
        onClose();
        setEmail(""); setPassword(""); setUsername("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-800">
          {isSignUp ? "Create account" : "Log in"}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          {isSignUp
            ? "Sign up to upload your own papers and personalize translations."
            : "Log in to access your personal knowledge base and persona."}
        </p>

        <form onSubmit={submit} className="mt-4 space-y-3">
          {isSignUp && (
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              required
              autoComplete="username"
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            required
            autoComplete="email"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            required
            minLength={isSignUp ? 6 : undefined}
            autoComplete={isSignUp ? "new-password" : "current-password"}
          />

          {error && <p className="text-xs text-red-600 rounded bg-red-50 px-2 py-1.5">{error}</p>}
          {info && <p className="text-xs text-green-700 rounded bg-green-50 px-2 py-1.5">{info}</p>}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "..." : isSignUp ? "Create account" : "Log in"}
            </button>
            <button
              type="button"
              onClick={switchMode}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              {isSignUp ? "Log in" : "Sign up"}
            </button>
          </div>
        </form>

        <button
          type="button"
          onClick={onClose}
          className="mt-3 w-full text-xs text-slate-400 hover:text-slate-600"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

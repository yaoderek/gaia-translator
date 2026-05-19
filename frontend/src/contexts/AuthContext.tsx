import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getSupabase, initSupabase, setSession } from "../lib/supabase";

interface User {
  id: string;
  email?: string;
}

interface Persona {
  username: string;
  discipline: string;
  bio: string;
  tags: string;
  papers_of_interest: string;
  concepts_focus: string;
  methods_focus: string;
  tech_stack: string;
  updated_at: string | null;
}

interface Me {
  user_id: string;
  email: string | null;
  username: string;
  persona: Persona;
}

interface AuthContextValue {
  user: User | null;
  session: unknown;
  loading: boolean;
  me: Me | null;
  refetchMe: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, username: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<Me | null>(null);

  const refetchMe = useCallback(async () => {
    const client = getSupabase();
    if (!client) { setMe(null); return; }
    const { data: { session: s } } = await client.auth.getSession();
    const token = s?.access_token;
    if (!token) { setMe(null); return; }
    try {
      const r = await fetch("/api/me", { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) setMe(await r.json());
      else setMe(null);
    } catch {
      setMe(null);
    }
  }, []);

  // Initialize Supabase (may be async in production) then set up auth listeners.
  useEffect(() => {
    let unsub: (() => void) | null = null;

    initSupabase().then((client) => {
      if (!client) {
        setLoading(false);
        return;
      }

      client.auth.getSession().then(({ data: { session: s } }) => {
        setSessionState(s);
        setSession(s);
        setLoading(false);
      });

      const { data: { subscription } } = client.auth.onAuthStateChange((event, s) => {
        setSessionState(s);
        setSession(s);
        if (event === "SIGNED_IN" || event === "USER_UPDATED") setLoading(false);
      });
      unsub = () => subscription.unsubscribe();
    });

    return () => { unsub?.(); };
  }, []);

  // Handle email confirmation redirect — Supabase puts tokens in the URL hash.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (!hash || (!hash.includes("access_token") && !hash.includes("refresh_token"))) return;
    initSupabase().then((client) => {
      if (!client) return;
      client.auth.getSession().then(({ data: { session: s } }) => {
        setSessionState(s);
        setSession(s);
        window.history.replaceState(null, "", window.location.pathname + window.location.search);
      });
    });
  }, []);

  useEffect(() => {
    if (session) refetchMe();
    else setMe(null);
  }, [session, refetchMe]);

  const signIn = useCallback(async (email: string, password: string) => {
    const client = getSupabase() ?? await initSupabase();
    if (!client) throw new Error("Auth not configured — SUPABASE_ANON_KEY not set on the server.");
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
  }, []);

  const signUp = useCallback(async (email: string, password: string, username: string) => {
    const client = getSupabase() ?? await initSupabase();
    if (!client) throw new Error("Auth not configured — SUPABASE_ANON_KEY not set on the server.");
    const { error } = await client.auth.signUp({
      email,
      password,
      options: { data: { username } },
    });
    if (error) throw new Error(error.message);
  }, []);

  const signOut = useCallback(async () => {
    const client = getSupabase();
    if (!client) return;
    await client.auth.signOut();
    setMe(null);
  }, []);

  const user: User | null =
    session && typeof session === "object" && "user" in session
      ? {
          id: (session as { user: { id: string } }).user.id,
          email: (session as { user: { email?: string } }).user.email,
        }
      : null;

  return (
    <AuthContext.Provider value={{ user, session, loading, me, refetchMe, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

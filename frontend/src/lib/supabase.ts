import { createClient, type Session, type SupabaseClient } from "@supabase/supabase-js";

type Client = SupabaseClient;

let _client: Client | null = null;
let _initPromise: Promise<Client | null> | null = null;

// In local dev, env vars are available at build time — use them immediately.
const _buildUrl = (import.meta.env.VITE_SUPABASE_URL ?? "").trim();
const _buildKey = (import.meta.env.VITE_SUPABASE_ANON_KEY ?? "").trim();
if (_buildUrl && _buildKey) {
  _client = createClient(_buildUrl, _buildKey);
}

/**
 * Lazily initialize the Supabase client from the backend /api/config endpoint.
 * In production the frontend is built without VITE_* vars, so we fetch them at runtime.
 * Safe to call multiple times — resolves immediately if already initialized.
 */
export async function initSupabase(): Promise<Client | null> {
  if (_client) return _client;
  if (_initPromise) return _initPromise;
  _initPromise = (async () => {
    try {
      const res = await fetch("/api/config");
      if (!res.ok) return null;
      const cfg = await res.json();
      if (cfg.supabase_url && cfg.supabase_anon_key) {
        _client = createClient(cfg.supabase_url, cfg.supabase_anon_key);
        return _client;
      }
    } catch {
      // backend unreachable or config missing
    }
    return null;
  })();
  return _initPromise;
}

/** Current Supabase client — null until initSupabase() resolves. */
export function getSupabase(): Client | null {
  return _client;
}

/** @deprecated use getSupabase() after awaiting initSupabase() */
export const supabase: Client | null = _client;

let _authToken: string | null = null;

export function setAuthToken(token: string | null) {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

export async function getAuthTokenAsync(): Promise<string | null> {
  const client = _client;
  if (!client) return null;
  const { data: { session } } = await client.auth.getSession();
  setAuthToken(session?.access_token ?? null);
  return session?.access_token ?? null;
}

export function setSession(session: Session | null) {
  setAuthToken(session?.access_token ?? null);
}

export function getSupabaseConfigStatus(): { url: boolean; anonKey: boolean } {
  return { url: !!_buildUrl, anonKey: !!_buildKey };
}

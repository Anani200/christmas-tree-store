import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from 'react';

const API_BASE = import.meta.env.VITE_API_URL as string;

export interface AuthUser {
  email: string;
}

interface Tokens {
  idToken: string;
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // epoch ms
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  confirmRegistration: (email: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  getIdToken: () => Promise<string>;
}

const TOKENS_KEY = 'cts_tokens';
const USER_KEY = 'cts_user';
const AUTH_TIMEOUT_MS = 10_000;

function loadTokens(): Tokens | null {
  try {
    const raw = sessionStorage.getItem(TOKENS_KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

function saveTokens(t: Tokens) {
  sessionStorage.setItem(TOKENS_KEY, JSON.stringify(t));
}

function clearTokens() {
  sessionStorage.removeItem(TOKENS_KEY);
  sessionStorage.removeItem(USER_KEY);
}

async function authFetch(path: string, body: unknown, accessToken?: string): Promise<unknown> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    const data = await res.json() as { message?: string };
    if (!res.ok) {
      throw new Error((data as { message?: string }).message ?? `Request failed (${res.status})`);
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [tokens, setTokens] = useState<Tokens | null>(loadTokens);
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    const t = loadTokens();
    if (t && t.expiresAt > Date.now()) {
      const raw = sessionStorage.getItem(USER_KEY);
      if (raw) setUser(JSON.parse(raw) as AuthUser);
      setTokens(t);
    } else if (t) {
      // Attempt silent refresh
      void refreshSilent(t.refreshToken);
    }
    setLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshSilent(refreshToken: string): Promise<Tokens | null> {
    try {
      const data = await authFetch('/auth/refresh', { refreshToken }) as {
        idToken: string; accessToken: string; expiresIn: number;
      };
      const next: Tokens = {
        idToken: data.idToken,
        accessToken: data.accessToken,
        refreshToken,
        expiresAt: Date.now() + data.expiresIn * 1000,
      };
      saveTokens(next);
      setTokens(next);
      return next;
    } catch {
      clearTokens();
      setTokens(null);
      setUser(null);
      return null;
    }
  }

  async function login(email: string, password: string) {
    const data = await authFetch('/auth/login', { email, password }) as {
      idToken: string; accessToken: string; refreshToken: string; expiresIn: number;
    };
    const t: Tokens = {
      idToken: data.idToken,
      accessToken: data.accessToken,
      refreshToken: data.refreshToken,
      expiresAt: Date.now() + data.expiresIn * 1000,
    };
    const u: AuthUser = { email };
    saveTokens(t);
    sessionStorage.setItem(USER_KEY, JSON.stringify(u));
    setTokens(t);
    setUser(u);
  }

  async function register(email: string, password: string) {
    await authFetch('/auth/register', { email, password });
  }

  async function confirmRegistration(email: string, code: string) {
    await authFetch('/auth/confirm', { email, code });
  }

  async function logout() {
    if (tokens?.accessToken) {
      await authFetch('/auth/logout', {}, tokens.accessToken).catch(() => {/* best-effort */});
    }
    clearTokens();
    setTokens(null);
    setUser(null);
  }

  const getIdToken = useCallback(async (): Promise<string> => {
    let t = tokens;
    if (t && t.expiresAt < Date.now() + 60_000) {
      // Proactively refresh when within 1 minute of expiry
      t = await refreshSilent(t.refreshToken);
    }
    if (!t?.idToken) throw new Error('Not authenticated');
    return t.idToken;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokens]);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: user !== null,
        login,
        register,
        confirmRegistration,
        logout,
        getIdToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}




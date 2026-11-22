import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, setAccessToken, setAuthLostHandler, silentRefresh } from "@/shared/api/client";
import type { TokenOut, User, Profile } from "@/shared/api/types";
import { dropLegacy, forgetUser, setStorageUser } from "@/shared/lib/userStore";

dropLegacy();

interface Ctx {
  user: User | null; ready: boolean;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string, name: string): Promise<void>;
  google(credential: string): Promise<void>;
  logout(): Promise<void>;
  refresh(): Promise<void>;
  saveProfile(p: Profile): Promise<User>;
}
const AuthCtx = createContext<Ctx>(null as never);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const qc = useQueryClient();

  const own = useCallback((u: User | null) => { setStorageUser(u?.id ?? null); setUser(u); }, []);
  const adopt = useCallback((t: TokenOut) => { setAccessToken(t.access_token); qc.clear(); own(t.user); }, [qc, own]);   // a new account starts with an empty cache
  const clear = useCallback(() => { setUser((u) => { forgetUser(u?.id ?? null); return null; }); setStorageUser(null); setAccessToken(null); qc.clear(); }, [qc]);

  useEffect(() => {
    setAuthLostHandler(clear);
    (async () => {
      const tok = await silentRefresh();
      if (tok) { setAccessToken(tok); try { own(await api.get<User>("/auth/me")); } catch { /* signed out */ } }
      setReady(true);
    })();
  }, [clear, own]);

  const value = useMemo<Ctx>(() => ({
    user, ready,
    login: async (email, password) => adopt(await api.post<TokenOut>("/auth/login", { email, password })),
    register: async (email, password, name) => adopt(await api.post<TokenOut>("/auth/register", { email, password, name })),
    refresh: async () => { try { own(await api.get<User>("/auth/me")); } catch { /* not signed in */ } },
    google: async (credential) => adopt(await api.post<TokenOut>("/auth/google", { credential })),
    logout: async () => { try { await api.post("/auth/logout"); } finally { clear(); } },
    saveProfile: async (p) => { const u = await api.put<User>("/auth/profile", p); own(u); return u; },
  }), [user, ready, adopt, clear, own]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

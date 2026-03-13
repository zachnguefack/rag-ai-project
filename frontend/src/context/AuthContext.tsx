import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { authApi } from '../lib/api/auth';
import { tokenStorage } from '../lib/api/client';
import type { MeResponse } from '../types/api';

type AuthContextValue = {
  user: MeResponse | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = async () => {
    try {
      const profile = await authApi.me();
      setUser(profile);
    } catch {
      tokenStorage.clear();
      setUser(null);
    }
  };

  useEffect(() => {
    if (!tokenStorage.get()) {
      setLoading(false);
      return;
    }
    refreshProfile().finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const token = await authApi.login(username, password);
    tokenStorage.set(token.access_token);
    await refreshProfile();
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      tokenStorage.clear();
      setUser(null);
    }
  };

  const value = useMemo(() => ({ user, loading, login, logout, refreshProfile }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

export type SessionUser = {
  id: string;
  full_name: string;
  email: string;
  roles: string[];
  permissions: string[];
  is_active: boolean;
};

type AuthState = {
  user: SessionUser | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (code: string) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setReady(true);
      return;
    }
    api.get("/auth/me").then(setUser).catch(() => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }).finally(() => setReady(true));
  }, []);

  async function login(email: string, password: string) {
    const tokens = await api.post("/auth/login", { email, password });
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    setUser(await api.get("/auth/me"));
  }

  async function logout() {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) await api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => undefined);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }

  function can(code: string) {
    return !!user?.permissions?.includes(code);
  }

  return <AuthContext.Provider value={{ user, ready, login, logout, can }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is missing");
  return value;
}

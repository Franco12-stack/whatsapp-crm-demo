import { createContext, useContext, useState, type ReactNode } from "react";
import { getToken, setToken as persistToken } from "../api/client";
import type { UserOut } from "../types";

interface AuthContextValue {
  user: UserOut | null;
  login: (token: string, user: UserOut) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const USER_KEY = "demo_user";

function loadStoredUser(): UserOut | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserOut;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(() => (getToken() ? loadStoredUser() : null));

  function login(token: string, newUser: UserOut) {
    persistToken(token);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
    setUser(newUser);
  }

  function logout() {
    persistToken(null);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

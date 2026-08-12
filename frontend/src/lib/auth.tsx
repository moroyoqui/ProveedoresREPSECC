/**
 * Lightweight auth context.
 *
 * Phase 2 only owns the shape; the actual session resolution against
 * `GET /api/v1/auth/me` lands in Phase 3 (US1, T059 + T079).
 */

import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Role = "admin" | "manager" | "viewer" | "supplier";

export type AuthUser = {
  id: number;
  email: string;
  displayName: string;
  role: Role;
  supplierId?: number | null;
  organization: {
    id: number;
    legalName: string;
    rfc: string;
    timezone: string;
    expiringSoonThresholdDays: number;
  };
};

type AuthState = {
  user: AuthUser | null;
  setUser: (u: AuthUser | null) => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const value = useMemo(() => ({ user, setUser }), [user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

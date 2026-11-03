import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";

import { ApiError, api, UNAUTHORIZED_EVENT } from "./api";
import type { CurrentUser, Role } from "./types";

interface AuthValue {
  user: CurrentUser;
  isStaff: boolean;
  isAdmin: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export const isStaffRole = (role: Role) => role === "ADMIN" || role === "COORDINATOR";

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Administrator",
  COORDINATOR: "Coordinator",
  FACULTY: "Faculty",
};

/** The current session: ``undefined`` while loading, ``null`` when signed out. */
export function useSession() {
  const queryClient = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api.me();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: Infinity,
    retry: false,
  });

  useEffect(() => {
    const expired = () => queryClient.setQueryData(["me"], null);
    window.addEventListener(UNAUTHORIZED_EVENT, expired);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, expired);
  }, [queryClient]);

  return me;
}

export function AuthProvider({ user, children }: { user: CurrentUser; children: ReactNode }) {
  const queryClient = useQueryClient();
  const signOut = useCallback(async () => {
    await api.logout().catch(() => undefined);
    queryClient.clear();
    queryClient.setQueryData(["me"], null);
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{ user, isStaff: isStaffRole(user.role), isAdmin: user.role === "ADMIN", signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}

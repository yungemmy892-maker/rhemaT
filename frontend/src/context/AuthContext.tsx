import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi, type AuthUser } from "@/services/api";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/services/client";
import { queryKeys } from "@/hooks/queries/keys";

export type User = AuthUser;

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  /** True once the initial session check (or lack thereof) has resolved. */
  isReady: boolean;
  signInGoogle: (idToken: string) => Promise<User>;
  signInEmail: (email: string, password: string) => Promise<User>;
  registerEmail: (name: string, email: string, password: string) => Promise<User>;
  signOut: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateProfile: (name: string) => Promise<User>;
  uploadAvatar: (file: File) => Promise<User>;
  changePassword: (currentPassword: string | undefined, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  // Start as true so the landing page, /privacy, /terms, /help, /auth
  // all render immediately without waiting for a network session check.
  // app.tsx's guard re-checks isReady/user before showing /app/* content.
  const [isReady, setIsReady] = useState(false);
  const queryClient = useQueryClient();

  const loadSession = useCallback(async () => {
    if (!getAccessToken()) {
      // No token — immediately ready with no user. Landing page renders
      // right away, no spinner, no delay.
      setIsReady(true);
      return;
    }
    // Token exists — verify it's still valid before showing the app.
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsReady(true);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  // If the axios interceptor gives up on refreshing (refresh token expired
  // or revoked), drop the local session so routes correctly redirect to /auth.
  useEffect(() => {
    const handler = () => {
      clearTokens();
      setUser(null);
    };
    window.addEventListener("verseid:auth-expired", handler);
    return () => window.removeEventListener("verseid:auth-expired", handler);
  }, []);

  const signInGoogle = useCallback(async (idToken: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.google(idToken);
      setTokens(res.access_token, res.refresh_token);
      setUser(res.user);
      return res.user;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signInEmail = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.login({ email, password });
      setTokens(res.access_token, res.refresh_token);
      setUser(res.user);
      return res.user;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const registerEmail = useCallback(async (name: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.register({ name, email, password });
      setTokens(res.access_token, res.refresh_token);
      setUser(res.user);
      return res.user;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // Already invalid/expired — fine to proceed with local cleanup.
      }
    }
    clearTokens();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const deleteAccount = useCallback(async () => {
    await authApi.deleteAccount();
    clearTokens();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
    queryClient.setQueryData(queryKeys.me, me);
  }, [queryClient]);

  const updateProfile = useCallback(
    async (name: string) => {
      const updated = await authApi.updateProfile({ name });
      setUser(updated);
      queryClient.setQueryData(queryKeys.me, updated);
      return updated;
    },
    [queryClient],
  );

  const uploadAvatar = useCallback(
    async (file: File) => {
      const updated = await authApi.uploadAvatar(file);
      setUser(updated);
      queryClient.setQueryData(queryKeys.me, updated);
      return updated;
    },
    [queryClient],
  );

  const changePassword = useCallback(
    async (currentPassword: string | undefined, newPassword: string) => {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      // A successful password change should keep the user signed in on
      // this device but invalidates the mental model of "what my password
      // is" — refresh the user object in case hasPassword flipped from
      // false to true (first-time password set on a Google-only account).
      await refreshUser();
    },
    [refreshUser],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isReady,
      signInGoogle,
      signInEmail,
      registerEmail,
      signOut,
      deleteAccount,
      refreshUser,
      updateProfile,
      uploadAvatar,
      changePassword,
    }),
    [
      user,
      isLoading,
      isReady,
      signInGoogle,
      signInEmail,
      registerEmail,
      signOut,
      deleteAccount,
      refreshUser,
      updateProfile,
      uploadAvatar,
      changePassword,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

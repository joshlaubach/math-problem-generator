/**
 * Auth user identity hook for Phase 10 JWT authentication
 *
 * Manages:
 * - JWT token and backend user_id
 * - Legacy anonymous UUID
 * - Role-based access control
 * - Login/register/logout flows
 */

import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { authAPI } from "../services/http_client";
import { UserRole } from "../types/api_types";

const STORAGE_LEGACY_USER_ID_KEY = "mpg_legacy_user_id";
const STORAGE_TOKEN_KEY = "mpg_token";
const STORAGE_USER_INFO_KEY = "mpg_user_info";

interface UserInfo {
  user_id: string;
  role: "student" | "teacher" | "admin";
  email?: string;
  display_name?: string;
}

interface UseAuthUserReturn {
  // IDs
  backendUserId: string | null;
  legacyUserId: string;

  // User info
  email: string | null;
  displayName: string | null;
  role: UserRole;

  // Auth state
  authToken: string | null;
  isAuthenticated: boolean;
  isTeacher: boolean;
  isAdmin: boolean;

  // Auth actions
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    role?: "student" | "teacher";
    displayName?: string;
  }) => Promise<void>;
  logout: () => void;

  // Error handling
  error: string | null;
  clearError: () => void;
}

export function useAuthUser(): UseAuthUserReturn {
  // User IDs
  const [backendUserId, setBackendUserId] = useState<string | null>(null);
  const [legacyUserId, setLegacyUserId] = useState<string>(() => {
    const stored = localStorage.getItem(STORAGE_LEGACY_USER_ID_KEY);
    if (stored) return stored;
    const newId = uuidv4();
    localStorage.setItem(STORAGE_LEGACY_USER_ID_KEY, newId);
    return newId;
  });

  // User info
  const [email, setEmail] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole>("anonymous");

  // Auth state
  const [authToken, setAuthTokenState] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Error handling
  const [error, setError] = useState<string | null>(null);

  // Hydrate auth state on mount
  useEffect(() => {
    const token = localStorage.getItem(STORAGE_TOKEN_KEY);
    const userInfoStr = localStorage.getItem(STORAGE_USER_INFO_KEY);

    if (token && userInfoStr) {
      try {
        const userInfo: UserInfo = JSON.parse(userInfoStr);
        setAuthTokenState(token);
        setBackendUserId(userInfo.user_id);
        setRole(userInfo.role);
        setEmail(userInfo.email ?? null);
        setDisplayName(userInfo.display_name ?? null);
        setIsAuthenticated(true);
      } catch (e) {
        console.error("Failed to hydrate auth state:", e);
        // Clear invalid data
        localStorage.removeItem(STORAGE_TOKEN_KEY);
        localStorage.removeItem(STORAGE_USER_INFO_KEY);
      }
    }
  }, []);

  const handleLogin = async (
    emailInput: string,
    password: string
  ): Promise<void> => {
    try {
      setError(null);
      const response = await authAPI.login({ email: emailInput, password });

      setAuthTokenState(response.access_token);
      setBackendUserId(response.user_id);
      setRole(response.role);
      setEmail(response.email ?? null);
      setDisplayName(response.display_name ?? null);
      setIsAuthenticated(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  };

  const handleRegister = async (payload: {
    email: string;
    password: string;
    role?: "student" | "teacher";
    displayName?: string;
  }): Promise<void> => {
    try {
      setError(null);
      const response = await authAPI.register({
        email: payload.email,
        password: payload.password,
        role: payload.role || "student",
        display_name: payload.displayName,
        legacy_user_id: legacyUserId,
      });

      setAuthTokenState(response.access_token);
      setBackendUserId(response.user_id);
      setRole(response.role);
      setEmail(response.email ?? null);
      setDisplayName(response.display_name ?? null);
      setIsAuthenticated(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
      throw err;
    }
  };

  const handleLogout = (): void => {
    authAPI.logout();
    setAuthTokenState(null);
    setBackendUserId(null);
    setRole("anonymous");
    setEmail(null);
    setDisplayName(null);
    setIsAuthenticated(false);
    setError(null);
  };

  const clearError = (): void => {
    setError(null);
  };

  return {
    // IDs
    backendUserId,
    legacyUserId,

    // User info
    email,
    displayName,
    role,

    // Auth state
    authToken,
    isAuthenticated,
    isTeacher: role === "teacher" || role === "admin",
    isAdmin: role === "admin",

    // Auth actions
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,

    // Error handling
    error,
    clearError,
  };
}

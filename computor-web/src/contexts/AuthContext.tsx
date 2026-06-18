'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthUser, AuthResponse } from '../types/auth';
import { UserScopes } from '../generated/types/users';
import { SSOAuthService } from '../services/ssoAuthService';
import { AuthService } from '../services/authService';
import { apiFetch } from '../utils/apiClient';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
// Side-effect import: wires the auth providers into the shared `apiClient`
// singleton (used by all generated clients) so a 401 there refreshes the token
// and clears the cached session on failure instead of bailing out blindly.
import '../config/apiConfig';

interface AuthContextType {
  user: AuthUser | null;
  views: string[];
  scopes: UserScopes | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<AuthResponse>;
  loginWithSSO: (provider?: string) => void;
  logout: () => Promise<void>;
  refreshSession: () => Promise<AuthResponse>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [views, setViews] = useState<string[]>([]);
  const [scopes, setScopes] = useState<UserScopes | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch the authoritative per-scope role maps + view list from the backend.
  // `/user/scopes` (is_admin + organization/course_family/course role maps) and
  // `/user/views` (lecturer/student/tutor/user_manager) drive all role-gated UI.
  const loadPermissions = async () => {
    try {
      const [viewsRes, scopesRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/user/views`),
        apiFetch(`${API_BASE_URL}/user/scopes`),
      ]);
      if (viewsRes.ok) setViews(await viewsRes.json());
      if (scopesRes.ok) setScopes(await scopesRes.json());
    } catch {
      // Transient failure — keep whatever we already have rather than wiping gating.
    }
  };

  // Initialize auth services
  const ssoAuthService = new SSOAuthService();
  const authService = new AuthService();

  // Check for existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);

      // Demo mode (NEXT_PUBLIC_ANALYTICS_DEMO=1): skip the real auth backend so
      // the analytics dashboard renders against synthetic data with no server.
      // Off by default; never set in production.
      if (process.env.NEXT_PUBLIC_ANALYTICS_DEMO === '1') {
        setUser({
          id: 'demo-lecturer',
          username: 'demo.lecturer',
          email: 'demo@example.org',
          givenName: 'Demo',
          familyName: 'Lecturer',
          role: 'lecturer',
          systemRoles: [],
          permissions: [],
          courses: [],
        });
        setIsLoading(false);
        return;
      }

      // Try SSO first
      const ssoUser = ssoAuthService.getCurrentUser();
      if (ssoUser) {
        // Show the cached user immediately to avoid a flash of "logged out",
        // then verify the session is actually still alive on the backend.
        // The cached user can outlive its HttpOnly cookies (e.g. Firefox
        // restores sessionStorage after a restart), so trusting it blindly
        // leaves a stale "Sign Out" button for a dead session.
        setUser(ssoUser);
        setViews(authService.getCurrentViews());

        const status = await ssoAuthService.validateSession();
        if (status === 'invalid') {
          // Cookies are gone/expired — reflect the real logged-out state.
          setUser(null);
          setViews([]);
          setScopes(null);
        } else if (status === 'valid') {
          // Refresh from the (possibly updated) stored user.
          setUser(ssoAuthService.getCurrentUser());
          await loadPermissions();
        }
        // status === 'unreachable' (e.g. off VPN): keep the cached user as-is.

        setIsLoading(false);
        return;
      }

      // Fall back to auth service
      const authUser = authService.getCurrentUser();
      if (authUser) {
        setUser(authUser);
        setViews(authService.getCurrentViews());
        await loadPermissions();
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  // Proactive token refresh. This MUST fire well within Keycloak's SSO Session
  // Idle (30 min on the computor realm): only /auth/refresh resets that idle timer
  // — ordinary API calls hit the backend's own session, not Keycloak — so if we
  // wait longer than the idle window the Keycloak session expires and the refresh
  // (and thus the user's session) dies. 15 min gives two attempts per idle window.
  useEffect(() => {
    if (!user) return;

    // Refresh interval: 15 minutes — comfortably under the 30-min Keycloak SSO idle.
    const REFRESH_INTERVAL = 15 * 60 * 1000;

    // Set up interval to refresh token periodically
    const refreshInterval = setInterval(async () => {
      console.log('Proactively refreshing token...');
      const result = await refreshSession();
      if (!result.success) {
        console.error('Proactive token refresh failed');
      }
    }, REFRESH_INTERVAL);

    return () => {
      clearInterval(refreshInterval);
    };
  }, [user]);

  const login = async (username: string, password: string): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authService.login({ username, password });

      if (response.success && response.user) {
        setUser(response.user);
        setViews(authService.getCurrentViews());
        await loadPermissions();
      }

      return response;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithSSO = (provider: string = 'keycloak') => {
    ssoAuthService.initiateSSO(provider);
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      // Try SSO logout first
      if (ssoAuthService.isAuthenticated()) {
        await ssoAuthService.logout();
      } else if (authService.isAuthenticated()) {
        await authService.logout();
      }

      setUser(null);
      setViews([]);
      setScopes(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshSession = async (): Promise<AuthResponse> => {
    try {
      let response: AuthResponse | null = null;

      if (ssoAuthService.isAuthenticated()) {
        response = await ssoAuthService.refreshSession();
      } else if (authService.isAuthenticated()) {
        response = await authService.refreshSession();
        if (response?.success) {
          setViews(authService.getCurrentViews());
        }
      }

      if (response?.success && response.user) {
        setUser(response.user);
        return response;
      }

      // Backend unreachable (e.g. off VPN): keep the current session intact —
      // a transient network failure must not log the user out.
      if (response?.error === 'unreachable') {
        return response;
      }

      // Genuine auth failure: drop the session.
      setUser(null);
      setViews([]);
      return response ?? {
        success: false,
        error: 'Session refresh failed',
      };
    } catch (error) {
      console.error('Session refresh failed:', error);
      setUser(null);
      setViews([]);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  };

  const value: AuthContextType = {
    user,
    views,
    scopes,
    isAuthenticated: !!user,
    isLoading,
    login,
    loginWithSSO,
    logout,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

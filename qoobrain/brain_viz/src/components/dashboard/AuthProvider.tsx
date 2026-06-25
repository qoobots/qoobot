/**
 * src/components/dashboard/AuthProvider.tsx — Authentication provider
 *
 * Stub auth provider for future multi-user access control.
 * Currently allows anonymous access (dev mode).
 */
'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';

interface AuthUser {
  id: string;
  name: string;
  role: 'operator' | 'developer' | 'viewer';
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isAuthenticated: false,
  login: async () => false,
  logout: () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Development mode: auto-login as operator
  const [user] = useState<AuthUser>({
    id: 'dev_user',
    name: '开发者',
    role: 'developer',
  });

  const login = useCallback(async (_username: string, _password: string) => {
    // Stub: always succeeds in dev mode
    return true;
  }, []);

  const logout = useCallback(() => {
    console.log('[Auth] Logout');
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: true, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

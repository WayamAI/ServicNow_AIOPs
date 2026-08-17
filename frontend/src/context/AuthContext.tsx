import { createContext, useCallback, useContext, useState } from 'react';
import type { ReactNode } from 'react';

const AUTH_STORAGE_KEY = 'wayam_auth_session';

interface AuthUser {
  email: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function readStoredUser(): AuthUser | null {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as AuthUser;
    return parsed?.email ? parsed : null;
  } catch {
    // Corrupt or foreign localStorage value — treat as logged out.
    return null;
  }
}

/**
 * Demo authentication layer.
 *
 * Accepts any syntactically valid email address with any non empty
 * password — there is no real backend auth service behind this yet.
 * The public surface (login/logout/user/isAuthenticated) is what the
 * rest of the app depends on, so swapping this for a real auth
 * provider later (e.g. a call to a `/auth/login` endpoint) only
 * requires changing the body of `login`, not any consuming component.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  // localStorage reads are synchronous, so restoring the session belongs
  // in the lazy initializer rather than an effect + setState round trip —
  // isLoading is always false here, kept in the public shape only so a
  // future async auth check can flip it without changing callers.
  const [user, setUser] = useState<AuthUser | null>(readStoredUser);
  const [isLoading] = useState(false);

  const login = useCallback(async (email: string, password: string) => {
    const trimmedEmail = email.trim();
    if (!isValidEmail(trimmedEmail)) {
      throw new Error('Enter a valid email address.');
    }
    if (!password.trim()) {
      throw new Error('Enter a password.');
    }

    // Simulate a network round trip so the login button's loading state
    // reads as real rather than an instant flash.
    await new Promise((resolve) => setTimeout(resolve, 500));

    const authedUser: AuthUser = { email: trimmedEmail };
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authedUser));
    setUser(authedUser);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { api, getStoredToken, setStoredToken, clearStoredToken } from '@/api/client';
import type { User, LoginRequest } from '@/api/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = getStoredToken();
      if (token) {
        try {
          const currentUser = await api.getCurrentUser();
          setUser(currentUser);
        } catch {
          // Token invalid or expired
          clearStoredToken();
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (credentials: LoginRequest) => {
    const response = await api.login(credentials);
    setStoredToken(response.token);
    const currentUser = await api.getCurrentUser();
    setUser(currentUser);
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // Ignore logout errors - we'll clear the token anyway
    } finally {
      clearStoredToken();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

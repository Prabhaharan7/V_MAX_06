import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

export type UserRole = "hse_officer" | "site_manager" | "admin";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  site_id?: number | null;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "sif_sentinel_token";
const USER_KEY = "sif_sentinel_user";

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
  });

  const [user, setUser] = useState<User | null>(() => {
    const cachedUser = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
    if (cachedUser) {
      try {
        return JSON.parse(cachedUser);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Validate or restore session on initial load
  useEffect(() => {
    const initializeAuth = async () => {
      if (token) {
        try {
          const res = await fetch("/api/auth/me", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (res.ok) {
            const userData: User = await res.json();
            setUser(userData);
            sessionStorage.setItem(USER_KEY, JSON.stringify(userData));
          } else {
            // Token expired or invalid
            logout();
          }
        } catch (err) {
          console.warn("Failed to verify user session:", err);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, [token]);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        setIsLoading(false);
        return {
          success: false,
          error: errorData.detail || "Authentication failed. Invalid credentials.",
        };
      }

      const data = await response.json();
      const accessToken = data.access_token;
      const currentUser: User = data.user;

      setToken(accessToken);
      setUser(currentUser);

      // In-memory + session storage handling
      sessionStorage.setItem(TOKEN_KEY, accessToken);
      sessionStorage.setItem(USER_KEY, JSON.stringify(currentUser));

      setIsLoading(false);
      return { success: true };
    } catch (err) {
      setIsLoading(false);
      return {
        success: false,
        error: "Network error connecting to SIF Sentinel API gateway.",
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const userData: User = await res.json();
        setUser(userData);
        sessionStorage.setItem(USER_KEY, JSON.stringify(userData));
      }
    } catch (e) {
      console.error("Error refreshing user profile:", e);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

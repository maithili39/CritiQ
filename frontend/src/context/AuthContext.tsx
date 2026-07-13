import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { getAuthToken, clearAuthToken, getMe, login as apiLogin, register as apiRegister } from "@/lib/api";

interface AuthContextValue {
  email: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!getAuthToken()) {
      setIsLoading(false);
      return;
    }
    getMe()
      .then((me) => setEmail(me.email))
      .catch(() => clearAuthToken())
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (loginEmail: string, password: string) => {
    const result = await apiLogin(loginEmail, password);
    setEmail(result.email);
  };

  const register = async (registerEmail: string, password: string) => {
    const result = await apiRegister(registerEmail, password);
    setEmail(result.email);
  };

  const logout = () => {
    clearAuthToken();
    setEmail(null);
  };

  return (
    <AuthContext.Provider value={{ email, isLoading, isAuthenticated: !!email, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

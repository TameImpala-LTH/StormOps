import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  User,
  ConversationSummary,
  SavedLocationItem,
} from '../types/auth';
import {
  getStoredToken,
  fetchCurrentUser,
  loginUser,
  registerUser,
  logoutUser,
  fetchUserHistory,
  fetchSavedLocations,
  deleteUserConversation,
  createSavedLocation as apiCreateSavedLocation,
  deleteSavedLocation as apiDeleteSavedLocation,
} from '../services/auth';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  history: ConversationSummary[];
  savedLocations: SavedLocationItem[];
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  refreshHistory: () => Promise<void>;
  refreshSavedLocations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  saveLocation: (name: string, latitude: number, longitude: number, country?: string) => Promise<void>;
  removeSavedLocation: (id: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [history, setHistory] = useState<ConversationSummary[]>([]);
  const [savedLocations, setSavedLocations] = useState<SavedLocationItem[]>([]);

  const refreshHistory = useCallback(async () => {
    try {
      if (getStoredToken()) {
        const items = await fetchUserHistory();
        setHistory(items);
      } else {
        setHistory([]);
      }
    } catch {
      // Ignore
    }
  }, []);

  const refreshSavedLocations = useCallback(async () => {
    try {
      if (getStoredToken()) {
        const items = await fetchSavedLocations();
        setSavedLocations(items);
      } else {
        setSavedLocations([]);
      }
    } catch {
      // Ignore
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const profile = await fetchCurrentUser();
        setUser(profile);
        await Promise.all([refreshHistory(), refreshSavedLocations()]);
      } catch {
        logoutUser();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();

    // Listen for custom token expiration event from Axios interceptor
    const handleExpired = () => {
      setUser(null);
      setHistory([]);
      setSavedLocations([]);
    };
    window.addEventListener('stormops_auth_expired', handleExpired);
    return () => window.removeEventListener('stormops_auth_expired', handleExpired);
  }, [refreshHistory, refreshSavedLocations]);

  const login = async (email: string, password: string) => {
    const res = await loginUser(email, password);
    setUser(res.user);
    await Promise.all([refreshHistory(), refreshSavedLocations()]);
  };

  const register = async (email: string, password: string, displayName: string) => {
    const res = await registerUser(email, password, displayName);
    setUser(res.user);
    await Promise.all([refreshHistory(), refreshSavedLocations()]);
  };

  const logout = () => {
    logoutUser();
    setUser(null);
    setHistory([]);
    setSavedLocations([]);
  };

  const deleteConversation = async (id: string) => {
    await deleteUserConversation(id);
    setHistory((prev) => prev.filter((c) => c.id !== id));
  };

  const saveLocation = async (name: string, latitude: number, longitude: number, country?: string) => {
    const created = await apiCreateSavedLocation(name, latitude, longitude, country);
    setSavedLocations((prev) => {
      if (prev.some((loc) => loc.id === created.id)) return prev;
      return [created, ...prev];
    });
  };

  const removeSavedLocation = async (id: string) => {
    await apiDeleteSavedLocation(id);
    setSavedLocations((prev) => prev.filter((loc) => loc.id !== id));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        history,
        savedLocations,
        login,
        register,
        logout,
        refreshHistory,
        refreshSavedLocations,
        deleteConversation,
        saveLocation,
        removeSavedLocation,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

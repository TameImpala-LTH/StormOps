/**
 * ThemeContext — centralized three-mode theme system.
 *
 * Modes: 'dark' | 'light' | 'night'
 *
 * - Persisted in localStorage (key: 'stormops-theme').
 * - Defaults to 'dark' when no preference is stored.
 * - Theme class is applied to <html> to prevent FOUC.
 * - No backend required.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

export type Theme = 'dark' | 'light' | 'night';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const STORAGE_KEY = 'stormops-theme';
const VALID_THEMES: Theme[] = ['dark', 'light', 'night'];
const DEFAULT_THEME: Theme = 'dark';

function resolveInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (stored && VALID_THEMES.includes(stored)) return stored;
  } catch {
    // localStorage unavailable — ignore
  }
  return DEFAULT_THEME;
}

function applyThemeToHTML(theme: Theme) {
  const root = document.documentElement;
  VALID_THEMES.forEach((t) => root.classList.remove(`theme-${t}`));
  root.classList.add(`theme-${theme}`);
}

// Apply theme synchronously before React renders to prevent FOUC.
if (typeof document !== 'undefined') {
  applyThemeToHTML(resolveInitialTheme());
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: DEFAULT_THEME,
  setTheme: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(resolveInitialTheme);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    applyThemeToHTML(newTheme);
    try {
      localStorage.setItem(STORAGE_KEY, newTheme);
    } catch {
      // localStorage unavailable — ignore
    }
  }, []);

  useEffect(() => {
    applyThemeToHTML(theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextValue => useContext(ThemeContext);

/**
 * ThemeContext — centralized theme system with Dark variants (Atheris & Vandal).
 *
 * Themes: 'dark' | 'light' | 'night'
 * Dark Variants: 'atheris' (default black + electric blue) | 'vandal' (black + neon red)
 *
 * - Persisted in localStorage:
 *     'stormops-theme' -> 'dark' | 'light' | 'night'
 *     'stormops-dark-variant' -> 'atheris' | 'vandal'
 * - Defaults to 'dark' and 'atheris' when no preference is stored.
 * - Theme and variant classes are applied to <html> to prevent FOUC.
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';

export type Theme = 'dark' | 'light' | 'night';
export type DarkVariant = 'atheris' | 'vandal';

export interface ThemeContextValue {
  theme: Theme;
  darkVariant: DarkVariant;
  setTheme: (theme: Theme) => void;
  setDarkVariant: (variant: DarkVariant) => void;
  accentColor: string;
}

const STORAGE_KEY = 'stormops-theme';
const VARIANT_STORAGE_KEY = 'stormops-dark-variant';
const VALID_THEMES: Theme[] = ['dark', 'light', 'night'];
const VALID_VARIANTS: DarkVariant[] = ['atheris', 'vandal'];
const DEFAULT_THEME: Theme = 'dark';
const DEFAULT_VARIANT: DarkVariant = 'atheris';

export function resolveInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (stored && VALID_THEMES.includes(stored)) return stored;
  } catch {
    // localStorage unavailable — ignore
  }
  return DEFAULT_THEME;
}

export function resolveInitialVariant(): DarkVariant {
  try {
    const stored = localStorage.getItem(VARIANT_STORAGE_KEY) as DarkVariant | null;
    if (stored && VALID_VARIANTS.includes(stored)) return stored;
  } catch {
    // localStorage unavailable — ignore
  }
  return DEFAULT_VARIANT;
}

export function getThemeAccentColor(theme: Theme, darkVariant: DarkVariant = 'atheris'): string {
  if (theme === 'night') return '#fbbf24';
  if (theme === 'light') return '#059669';
  return darkVariant === 'vandal' ? '#ff2a55' : '#38bdf8';
}

function applyThemeToHTML(theme: Theme, darkVariant: DarkVariant) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;

  // Set theme classes
  VALID_THEMES.forEach((t) => root.classList.remove(`theme-${t}`));
  root.classList.add(`theme-${theme}`);
  root.setAttribute('data-theme', theme);

  // Set dark variant classes
  VALID_VARIANTS.forEach((v) => root.classList.remove(`variant-${v}`));
  if (theme === 'dark') {
    root.classList.add(`variant-${darkVariant}`);
    root.setAttribute('data-dark-variant', darkVariant);
  } else {
    root.removeAttribute('data-dark-variant');
  }
}

// Apply theme synchronously before React renders to prevent FOUC.
if (typeof document !== 'undefined') {
  applyThemeToHTML(resolveInitialTheme(), resolveInitialVariant());
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: DEFAULT_THEME,
  darkVariant: DEFAULT_VARIANT,
  setTheme: () => {},
  setDarkVariant: () => {},
  accentColor: '#38bdf8',
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(resolveInitialTheme);
  const [darkVariant, setDarkVariantState] = useState<DarkVariant>(resolveInitialVariant);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    applyThemeToHTML(newTheme, darkVariant);
    try {
      localStorage.setItem(STORAGE_KEY, newTheme);
    } catch {
      // localStorage unavailable — ignore
    }
  }, [darkVariant]);

  const setDarkVariant = useCallback((newVariant: DarkVariant) => {
    setDarkVariantState(newVariant);
    // If setting a dark variant, also ensure theme is dark
    setThemeState('dark');
    applyThemeToHTML('dark', newVariant);
    try {
      localStorage.setItem(STORAGE_KEY, 'dark');
      localStorage.setItem(VARIANT_STORAGE_KEY, newVariant);
    } catch {
      // localStorage unavailable — ignore
    }
  }, []);

  useEffect(() => {
    applyThemeToHTML(theme, darkVariant);
  }, [theme, darkVariant]);

  const accentColor = useMemo(() => getThemeAccentColor(theme, darkVariant), [theme, darkVariant]);

  return (
    <ThemeContext.Provider value={{ theme, darkVariant, setTheme, setDarkVariant, accentColor }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextValue => useContext(ThemeContext);


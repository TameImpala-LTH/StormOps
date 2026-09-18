import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Star, Check } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, darkVariant, setTheme, setDarkVariant } = useTheme();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  const activeLabel =
    theme === 'dark'
      ? darkVariant === 'vandal'
        ? 'Dark · Vandal'
        : 'Dark · Atheris'
      : theme === 'light'
      ? 'Light'
      : 'Midnight';

  const ActiveIcon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Star;

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Current theme: ${activeLabel}. Click to change theme.`}
        title={`Theme: ${activeLabel}`}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2"
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
          color: 'var(--text-secondary)',
        }}
      >
        <ActiveIcon className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
        <span className="hidden sm:inline" style={{ color: 'var(--text-secondary)' }}>
          {activeLabel}
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          role="listbox"
          aria-label="Select theme"
          className="absolute right-0 top-full mt-1.5 z-50 rounded-xl border shadow-2xl min-w-[175px] overflow-hidden p-1 space-y-1"
          style={{
            backgroundColor: 'var(--surface)',
            borderColor: 'var(--border)',
          }}
        >
          {/* Dark Theme Group */}
          <div
            className="rounded-lg transition-colors"
            style={{
              backgroundColor: theme === 'dark' ? 'var(--accent-muted)' : 'transparent',
            }}
          >
            <button
              type="button"
              role="option"
              aria-selected={theme === 'dark'}
              onClick={() => {
                setTheme('dark');
              }}
              className="w-full flex items-center justify-between px-2.5 py-2 text-xs font-medium text-left cursor-pointer transition-colors"
              style={{
                color: theme === 'dark' ? 'var(--accent-text)' : 'var(--text-secondary)',
              }}
            >
              <div className="flex items-center gap-2">
                <Moon className="w-3.5 h-3.5 flex-shrink-0" />
                <span>Dark</span>
              </div>
              {theme === 'dark' && <Check className="w-3 h-3 text-[var(--accent)]" />}
            </button>

            {/* Dark Variant Sub-options: Atheris vs Vandal */}
            <div className="flex items-center gap-1 px-2 pb-2 pt-0.5">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setDarkVariant('atheris');
                }}
                className="flex-1 flex items-center justify-center gap-1.5 py-1 px-1.5 rounded-md text-[10px] font-mono transition-all cursor-pointer border"
                style={{
                  backgroundColor:
                    theme === 'dark' && darkVariant === 'atheris'
                      ? 'rgba(56, 189, 248, 0.16)'
                      : 'var(--surface-elevated)',
                  borderColor:
                    theme === 'dark' && darkVariant === 'atheris'
                      ? 'rgba(56, 189, 248, 0.40)'
                      : 'var(--border-muted)',
                  color:
                    theme === 'dark' && darkVariant === 'atheris'
                      ? '#38bdf8'
                      : 'var(--text-tertiary)',
                }}
                title="Atheris skin: pitch black with electric sky blue accent"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8]" />
                Atheris
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setDarkVariant('vandal');
                }}
                className="flex-1 flex items-center justify-center gap-1.5 py-1 px-1.5 rounded-md text-[10px] font-mono transition-all cursor-pointer border"
                style={{
                  backgroundColor:
                    theme === 'dark' && darkVariant === 'vandal'
                      ? 'rgba(255, 42, 85, 0.16)'
                      : 'var(--surface-elevated)',
                  borderColor:
                    theme === 'dark' && darkVariant === 'vandal'
                      ? 'rgba(255, 42, 85, 0.40)'
                      : 'var(--border-muted)',
                  color:
                    theme === 'dark' && darkVariant === 'vandal'
                      ? '#ff3366'
                      : 'var(--text-tertiary)',
                }}
                title="Vandal skin: pitch black with crisp neon red accent"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#ff2a55]" />
                Vandal
              </button>
            </div>
          </div>

          <div style={{ height: '1px', backgroundColor: 'var(--border-muted)', margin: '4px 0' }} />

          {/* Light Theme */}
          <button
            type="button"
            role="option"
            aria-selected={theme === 'light'}
            title="Light mode — warm daylight"
            onClick={() => {
              setTheme('light');
              setOpen(false);
            }}
            className="w-full flex items-center justify-between px-2.5 py-2 text-xs font-medium text-left cursor-pointer rounded-lg transition-colors"
            style={{
              backgroundColor: theme === 'light' ? 'var(--accent-muted)' : 'transparent',
              color: theme === 'light' ? 'var(--accent-text)' : 'var(--text-secondary)',
            }}
          >
            <div className="flex items-center gap-2">
              <Sun className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Light</span>
            </div>
            {theme === 'light' && <Check className="w-3 h-3 text-[var(--accent)]" />}
          </button>

          {/* Midnight Theme */}
          <button
            type="button"
            role="option"
            aria-selected={theme === 'night'}
            title="Midnight mode — deep purple / amber gold"
            onClick={() => {
              setTheme('night');
              setOpen(false);
            }}
            className="w-full flex items-center justify-between px-2.5 py-2 text-xs font-medium text-left cursor-pointer rounded-lg transition-colors"
            style={{
              backgroundColor: theme === 'night' ? 'var(--accent-muted)' : 'transparent',
              color: theme === 'night' ? 'var(--accent-text)' : 'var(--text-secondary)',
            }}
          >
            <div className="flex items-center gap-2">
              <Star className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Midnight</span>
            </div>
            {theme === 'night' && <Check className="w-3 h-3 text-[var(--accent)]" />}
          </button>
        </div>
      )}
    </div>
  );
};


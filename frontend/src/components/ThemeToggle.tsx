import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Star } from 'lucide-react';
import { useTheme, Theme } from '../context/ThemeContext';

interface ThemeOption {
  id: Theme;
  label: string;
  Icon: React.ElementType;
  title: string;
}

const THEME_OPTIONS: ThemeOption[] = [
  { id: 'dark',  label: 'Dark',  Icon: Moon, title: 'Dark mode — pitch black / sky blue' },
  { id: 'light', label: 'Light', Icon: Sun,  title: 'Light mode — warm daylight' },
  { id: 'night', label: 'Midnight', Icon: Star, title: 'Midnight mode — deep purple / amber gold' },
];

export const ThemeToggle: React.FC = () => {
  const { theme, setTheme } = useTheme();
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

  const active = THEME_OPTIONS.find((o) => o.id === theme) ?? THEME_OPTIONS[0];
  const ActiveIcon = active.Icon;

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Current theme: ${active.label}. Click to change theme.`}
        title={`Theme: ${active.label}`}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2"
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
          color: 'var(--text-secondary)',
        }}
      >
        <ActiveIcon className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
        <span className="hidden sm:inline" style={{ color: 'var(--text-secondary)' }}>
          {active.label}
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          role="listbox"
          aria-label="Select theme"
          className="absolute right-0 top-full mt-1.5 z-50 rounded-xl border shadow-xl min-w-[130px] overflow-hidden"
          style={{
            backgroundColor: 'var(--surface)',
            borderColor: 'var(--border)',
          }}
        >
          {THEME_OPTIONS.map(({ id, label, Icon, title }) => {
            const isActive = id === theme;
            return (
              <button
                key={id}
                type="button"
                role="option"
                aria-selected={isActive}
                title={title}
                onClick={() => { setTheme(id); setOpen(false); }}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium text-left cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset"
                style={{
                  backgroundColor: isActive ? 'var(--accent-muted)' : 'transparent',
                  color: isActive ? 'var(--accent-text)' : 'var(--text-secondary)',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-elevated)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = isActive ? 'var(--accent-muted)' : 'transparent';
                }}
              >
                <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{label}</span>
                {isActive && (
                  <span
                    className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: 'var(--accent)' }}
                  />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

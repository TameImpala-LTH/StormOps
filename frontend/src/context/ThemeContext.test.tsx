import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import React from 'react';
import { ThemeProvider, useTheme, getThemeAccentColor } from './ThemeContext';
import { ThemeToggle } from '../components/ThemeToggle';

describe('Phase 18.7.1: ThemeContext & Dark Variants (Atheris / Vandal)', () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    document.documentElement.className = '';
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.removeAttribute('data-dark-variant');
  });

  it('provides correct accent colors for themes and variants', () => {
    expect(getThemeAccentColor('dark', 'atheris')).toBe('#38bdf8'); // electric blue
    expect(getThemeAccentColor('dark', 'vandal')).toBe('#ff2a55');  // neon red
    expect(getThemeAccentColor('light', 'atheris')).toBe('#059669'); // emerald
    expect(getThemeAccentColor('light', 'vandal')).toBe('#059669');  // light ignores variant
    expect(getThemeAccentColor('night', 'atheris')).toBe('#fbbf24'); // amber
    expect(getThemeAccentColor('night', 'vandal')).toBe('#fbbf24');  // night ignores variant
  });

  const TestConsumer: React.FC = () => {
    const { theme, darkVariant, setTheme, setDarkVariant, accentColor } = useTheme();
    return (
      <div>
        <div data-testid="theme-val">{theme}</div>
        <div data-testid="variant-val">{darkVariant}</div>
        <div data-testid="accent-val">{accentColor}</div>
        <button onClick={() => setTheme('light')}>Set Light</button>
        <button onClick={() => setTheme('night')}>Set Midnight</button>
        <button onClick={() => setTheme('dark')}>Set Dark</button>
        <button onClick={() => setDarkVariant('vandal')}>Set Vandal</button>
        <button onClick={() => setDarkVariant('atheris')}>Set Atheris</button>
      </div>
    );
  };

  it('initializes with default Dark + Atheris and sets HTML classes', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-val').textContent).toBe('dark');
    expect(screen.getByTestId('variant-val').textContent).toBe('atheris');
    expect(screen.getByTestId('accent-val').textContent).toBe('#38bdf8');

    expect(document.documentElement.classList.contains('theme-dark')).toBe(true);
    expect(document.documentElement.classList.contains('variant-atheris')).toBe(true);
  });

  it('switches to Vandal variant and updates accent to neon red and HTML class', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByText('Set Vandal'));

    expect(screen.getByTestId('theme-val').textContent).toBe('dark');
    expect(screen.getByTestId('variant-val').textContent).toBe('vandal');
    expect(screen.getByTestId('accent-val').textContent).toBe('#ff2a55');

    expect(document.documentElement.classList.contains('variant-vandal')).toBe(true);
    expect(document.documentElement.classList.contains('variant-atheris')).toBe(false);
    expect(localStorage.getItem('stormops-dark-variant')).toBe('vandal');
  });

  it('preserves Vandal variant preference when switching to Light and back to Dark', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    );

    // 1. Choose Vandal
    fireEvent.click(screen.getByText('Set Vandal'));
    expect(screen.getByTestId('variant-val').textContent).toBe('vandal');

    // 2. Switch to Light
    fireEvent.click(screen.getByText('Set Light'));
    expect(screen.getByTestId('theme-val').textContent).toBe('light');
    expect(screen.getByTestId('accent-val').textContent).toBe('#059669');
    expect(document.documentElement.classList.contains('theme-light')).toBe(true);
    expect(document.documentElement.classList.contains('variant-vandal')).toBe(false);

    // 3. Switch back to Dark -> restores Vandal!
    fireEvent.click(screen.getByText('Set Dark'));
    expect(screen.getByTestId('theme-val').textContent).toBe('dark');
    expect(screen.getByTestId('variant-val').textContent).toBe('vandal');
    expect(screen.getByTestId('accent-val').textContent).toBe('#ff2a55');
    expect(document.documentElement.classList.contains('variant-vandal')).toBe(true);
  });

  it('ThemeToggle allows switching between Atheris and Vandal via dropdown', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    // Open dropdown
    const triggerBtn = screen.getByRole('button', { name: /Dark · Atheris/i });
    fireEvent.click(triggerBtn);

    // Click Vandal in dropdown
    const vandalBtn = screen.getByRole('button', { name: /Vandal/i });
    fireEvent.click(vandalBtn);

    // Now trigger should show Dark · Vandal
    expect(screen.getByRole('button', { name: /Dark · Vandal/i })).toBeDefined();
    expect(document.documentElement.classList.contains('variant-vandal')).toBe(true);
  });
});

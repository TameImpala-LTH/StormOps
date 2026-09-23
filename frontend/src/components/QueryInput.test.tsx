import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { QueryInput } from './QueryInput';

describe('Phase UI-04: Unified Omnibar & Discovery Canvas Tests', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders in discovery mode with capability cue and preset examples', () => {
    const handleSubmit = vi.fn();
    const handleLangChange = vi.fn();

    render(
      <QueryInput
        variant="discovery"
        onQuerySubmit={handleSubmit}
        selectedLanguage="auto"
        onLanguageChange={handleLangChange}
      />
    );

    // Capability cue check
    expect(screen.getByText(/Search beyond cities/i)).toBeDefined();
    expect(screen.getByText(/Cities · Towns · Villages · Localities/i)).toBeDefined();

    // Preset examples check
    expect(screen.getByText('Darjeeling')).toBeDefined();
    expect(screen.getByText('Koramangala')).toBeDefined();
    expect(screen.getByText('Cherrapunji')).toBeDefined();
  });

  it('submits query when typing and clicking submit button', () => {
    const handleSubmit = vi.fn();
    const handleLangChange = vi.fn();

    render(
      <QueryInput
        variant="discovery"
        onQuerySubmit={handleSubmit}
        selectedLanguage="auto"
        onLanguageChange={handleLangChange}
      />
    );

    const input = screen.getByRole('textbox', { name: /Search weather by location or question/i });
    fireEvent.change(input, { target: { value: 'Will it rain in Darjeeling?' } });

    const submitBtn = screen.getByRole('button', { name: /Submit weather query/i });
    expect(submitBtn).toBeDefined();
    expect(submitBtn.hasAttribute('disabled')).toBe(false);

    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledWith('Will it rain in Darjeeling?', undefined, 'auto');
  });

  it('clears query input when pressing Escape or clicking clear button', () => {
    const handleSubmit = vi.fn();
    const handleLangChange = vi.fn();

    render(
      <QueryInput
        variant="discovery"
        onQuerySubmit={handleSubmit}
        selectedLanguage="auto"
        onLanguageChange={handleLangChange}
      />
    );

    const input = screen.getByRole('textbox', { name: /Search weather by location or question/i });
    fireEvent.change(input, { target: { value: 'Kolkata rain' } });
    expect((input as HTMLInputElement).value).toBe('Kolkata rain');

    // Press Escape
    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
    expect((input as HTMLInputElement).value).toBe('');
  });

  it('clicks preset example and triggers query submit immediately', () => {
    const handleSubmit = vi.fn();
    const handleLangChange = vi.fn();

    render(
      <QueryInput
        variant="discovery"
        onQuerySubmit={handleSubmit}
        selectedLanguage="auto"
        onLanguageChange={handleLangChange}
      />
    );

    const darjeelingBtn = screen.getByText('Darjeeling');
    fireEvent.click(darjeelingBtn);

    expect(handleSubmit).toHaveBeenCalledWith("What's the weather in Darjeeling?", undefined, 'auto');
  });

  it('renders in docked mode without capability cue or preset examples', () => {
    const handleSubmit = vi.fn();
    const handleLangChange = vi.fn();

    render(
      <QueryInput
        variant="docked"
        onQuerySubmit={handleSubmit}
        selectedLanguage="auto"
        onLanguageChange={handleLangChange}
      />
    );

    // Capability cue and examples must NOT be present in docked mode
    expect(screen.queryByText(/Search beyond cities/i)).toBeNull();
    expect(screen.queryByText('Darjeeling')).toBeNull();

    // Docked placeholder
    const input = screen.getByRole('textbox', { name: /Search weather by location or question/i });
    expect(input.getAttribute('placeholder')).toBe('Search or ask follow-up...');
  });
});

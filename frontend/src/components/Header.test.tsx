import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { Header } from './Header';
import { LiveWeatherHeader } from './LiveWeatherHeader';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { DeviceLocationProvider } from '../context/DeviceLocationContext';

afterEach(() => {
  cleanup();
  window.innerWidth = 1024;
  window.dispatchEvent(new Event('resize'));
});

describe('UI-10: Header & Location Control Responsiveness', () => {
  it('renders primary brand WeatherGPT, search slot, live weather, Bell button, and compact Profile button', () => {
    window.innerWidth = 1024;
    window.dispatchEvent(new Event('resize'));

    const onOpenEventsMock = vi.fn();

    render(
      <ThemeProvider>
        <AuthProvider>
          <DeviceLocationProvider>
            <Header
              searchSlot={<div data-testid="search-slot">Search Input</div>}
              onOpenEvents={onOpenEventsMock}
              eventCount={2}
            />
          </DeviceLocationProvider>
        </AuthProvider>
      </ThemeProvider>
    );

    // Primary Brand: WeatherGPT is dominant
    expect(screen.getByText('WeatherGPT')).toBeDefined();

    // Search Slot (rendered without duplicate inputs)
    expect(screen.getAllByTestId('search-slot').length).toBe(1);

    // Bell / Events & Information Entry Point (with active badge count)
    const bellBtn = screen.getByRole('button', { name: /Events and regional information/i });
    expect(bellBtn).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();

    fireEvent.click(bellBtn);
    expect(onOpenEventsMock).toHaveBeenCalledTimes(1);

    // Auth / Profile Button (compact icon button with aria-label)
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeDefined();

    // Theme toggle is cleanly moved out of primary header
    expect(screen.queryByRole('button', { name: /Click to change theme/i })).toBeNull();
  });

  it('renders mobile search trigger and toggles search slot on mobile viewport', async () => {
    // Simulate mobile viewport width
    window.innerWidth = 390;
    window.dispatchEvent(new Event('resize'));

    const { unmount } = render(
      <ThemeProvider>
        <AuthProvider>
          <DeviceLocationProvider>
            <Header
              searchSlot={<div data-testid="search-slot">Search Input</div>}
            />
          </DeviceLocationProvider>
        </AuthProvider>
      </ThemeProvider>
    );

    // On mobile initially closed: search slot is not rendered, but mobile search button is visible
    const searchToggleBtn = screen.getByRole('button', { name: /Search location or weather/i });
    expect(searchToggleBtn).toBeDefined();
    expect(screen.queryByTestId('search-slot')).toBeNull();

    // Click to expand mobile search
    fireEvent.click(searchToggleBtn);
    expect(screen.getByTestId('search-slot')).toBeDefined();
    expect(screen.getByRole('button', { name: /Close search/i })).toBeDefined();

    // Cleanup resize
    window.innerWidth = 1024;
    window.dispatchEvent(new Event('resize'));
    unmount();
  });

  it('renders LiveWeatherHeader with time formatted without seconds', () => {
    const mockLoc = {
      name: 'Mumbai',
      admin1: 'Maharashtra',
      country: 'India',
      latitude: 19.07,
      longitude: 72.87,
      timezone: 'Asia/Kolkata',
    };

    render(
      <LiveWeatherHeader
        location={mockLoc}
        temperature={29}
        isLocating={false}
      />
    );

    expect(screen.getByText('Mumbai')).toBeDefined();
    expect(screen.getByText('29°C')).toBeDefined();

    // Time: formatted as H:MM or HH:MM (without seconds)
    const timeRegex = /\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b/;
    const timeMatches = screen.queryAllByText(timeRegex);
    expect(timeMatches.length).toBeGreaterThan(0);
  });
});

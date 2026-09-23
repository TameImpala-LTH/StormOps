import { describe, it, expect, afterEach } from 'vitest';
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

describe('Header & Location Control Responsiveness', () => {
  it('renders brand, search slot, live weather, and theme toggle', () => {
    window.innerWidth = 1024;
    window.dispatchEvent(new Event('resize'));

    render(
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

    // Brand
    expect(screen.getByText('StormOps')).toBeDefined();
    expect(screen.getByText('WeatherGPT')).toBeDefined();

    // Search Slot (rendered without duplicate inputs)
    expect(screen.getAllByTestId('search-slot').length).toBe(1);

    // Theme Toggle
    const themeBtn = screen.getByRole('button', { name: /Click to change theme/i });
    expect(themeBtn).toBeDefined();

    // Auth / Sign In
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeDefined();
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

    // Ticking clock format should have AM or PM and no seconds colon count of 2
    // E.g. "4:35 PM" (one colon), not "4:35:12 PM" (two colons)
    const timeElements = screen.getAllByText(/(?:AM|PM)/i);
    expect(timeElements.length).toBeGreaterThanOrEqual(1);
    const timeText = timeElements[0].textContent || '';
    const colonCount = (timeText.match(/:/g) || []).length;
    expect(colonCount).toBe(1);
  });
});

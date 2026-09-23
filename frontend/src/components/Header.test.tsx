import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from './Header';
import { LiveWeatherHeader } from './LiveWeatherHeader';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { DeviceLocationProvider } from '../context/DeviceLocationContext';

describe('Header & Location Control Responsiveness', () => {
  it('renders brand, search slot, live weather, and theme toggle', () => {
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

    // Search Slot (rendered in desktop bar and mobile docked area)
    expect(screen.getAllByTestId('search-slot').length).toBe(2);

    // Theme Toggle
    const themeBtn = screen.getByRole('button', { name: /Click to change theme/i });
    expect(themeBtn).toBeDefined();

    // Auth / Sign In
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeDefined();
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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import {
  WeatherMap,
  createMarkerHtml,
  createPopupHtml,
  getOptimalZoom,
  getTileFilter,
} from './WeatherMap';
import { GeocodedLocationSchema, TargetPeriodWeather } from '../types/weather';
import { OfficialAdvisory } from '../types/advisory';
import { ThemeProvider } from '../context/ThemeContext';

describe('Phase UI-07: Spatial Intelligence / WeatherMap Tests', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    if (typeof window !== 'undefined') {
      const MockResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
      };
      (window as unknown as { ResizeObserver: unknown }).ResizeObserver = MockResizeObserver;
      (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = MockResizeObserver;
    }
  });

  afterEach(() => {
    cleanup();
  });

  const mockLocation: GeocodedLocationSchema = {
    name: 'Kolkata',
    city: 'Kolkata',
    district: 'Kolkata',
    admin1: 'West Bengal',
    country: 'India',
    latitude: 22.5726,
    longitude: 88.3639,
    timezone: 'Asia/Kolkata',
  };

  const mockWeather: TargetPeriodWeather = {
    period_label: 'Today',
    temperature: 28.4,
    feels_like: 33.2,
    condition: 'Humid & Overcast',
    weather_code: 3,
    humidity: 82,
    wind_speed: 18,
    precipitation: 1.2,
    precipitation_probability: 75,
    peak_hour: '18:00',
  };

  const mockAdvisory: OfficialAdvisory = {
    id: 'adv-geo-1',
    source_id: 'imd-kol-1',
    authority: 'IMD',
    hazard_type: 'heavy_rainfall',
    severity: 'orange',
    official_level: 'Alert (Be Prepared)',
    issued_at: '2026-09-23T10:00:00Z',
    effective_at: '2026-09-23T10:00:00Z',
    expires_at: '2026-09-23T22:00:00Z',
    is_active: true,
    latitude: 22.57,
    longitude: 88.36,
    radius_km: 25,
    headline: 'Heavy Rainfall Alert across Kolkata Metropolitan Area',
    description: 'Intense rain showers expected with waterlogging risk.',
    granularity: 'district',
    created_at: '2026-09-23T10:00:00Z',
    updated_at: '2026-09-23T10:00:00Z',
  };

  it('renders spatial context section header, location breadcrumbs, and compact legend', () => {
    render(
      <ThemeProvider>
        <WeatherMap
          location={mockLocation}
          weather={mockWeather}
          periodLabel="Today"
          advisories={[mockAdvisory]}
        />
      </ThemeProvider>
    );

    // Section header identity
    expect(screen.getByText('Spatial Context')).toBeDefined();
    expect(screen.getByText('· Evidence')).toBeDefined();
    expect(screen.getByText(/Kolkata · West Bengal · India — Geographic orientation & official advisory coverage/i)).toBeDefined();

    // Controls
    expect(screen.getByRole('button', { name: /Recenter map/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Expand map fullscreen/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Toggle official advisories/i })).toBeDefined();

    // Compact Legend
    expect(screen.getByText('Selected location')).toBeDefined();
    expect(screen.getByText('Official advisory')).toBeDefined();
  });

  it('toggles advisory layer on and off via the map header control', () => {
    render(
      <ThemeProvider>
        <WeatherMap
          location={mockLocation}
          weather={mockWeather}
          periodLabel="Today"
          advisories={[mockAdvisory]}
        />
      </ThemeProvider>
    );

    const toggleBtn = screen.getByRole('button', { name: /Toggle official advisories/i });
    expect(toggleBtn.textContent).toContain('Advisories On');

    // Click to toggle off
    fireEvent.click(toggleBtn);
    expect(toggleBtn.textContent).toContain('Advisories Off');

    // Click to toggle back on
    fireEvent.click(toggleBtn);
    expect(toggleBtn.textContent).toContain('Advisories On');
  });

  it('toggles fullscreen mode and exits upon Escape key', () => {
    render(
      <ThemeProvider>
        <WeatherMap
          location={mockLocation}
          weather={mockWeather}
          periodLabel="Today"
        />
      </ThemeProvider>
    );

    const expandBtn = screen.getByRole('button', { name: /Expand map fullscreen/i });
    fireEvent.click(expandBtn);

    // Now in fullscreen
    const exitBtn = screen.getByRole('button', { name: /Exit fullscreen map/i });
    expect(exitBtn).toBeDefined();

    // Press Escape
    fireEvent.keyDown(window, { key: 'Escape' });

    // Should return to normal mode
    expect(screen.getByRole('button', { name: /Expand map fullscreen/i })).toBeDefined();
  });

  it('determines optimal camera zoom based on locality vs city granularity', () => {
    const localityLoc: GeocodedLocationSchema = {
      ...mockLocation,
      locality: 'Park Street',
    };
    expect(getOptimalZoom(localityLoc)).toBe(12);

    const cityLoc: GeocodedLocationSchema = {
      ...mockLocation,
      locality: undefined,
      city: 'Kolkata',
    };
    expect(getOptimalZoom(cityLoc)).toBe(11);

    const stateLoc: GeocodedLocationSchema = {
      ...mockLocation,
      locality: undefined,
      city: undefined,
      district: undefined,
    };
    expect(getOptimalZoom(stateLoc)).toBe(10);
  });

  it('generates grounded selected location marker HTML with beacon and condition halo', () => {
    const markerHtml = createMarkerHtml('Kolkata', mockWeather, '#38bdf8', '#38bdf8', true);
    expect(markerHtml).toContain('stormops-focal-marker');
    expect(markerHtml).toContain('stormops-condition-halo');
    expect(markerHtml).toContain('Kolkata');
    expect(markerHtml).toContain('28&deg;C');
    expect(markerHtml).toContain('75%');
  });

  it('generates concise selected location popup HTML with breadcrumbs and telemetry', () => {
    const popupHtml = createPopupHtml(mockLocation, mockWeather, 'Today');
    expect(popupHtml).toContain('Kolkata');
    expect(popupHtml).toContain('West Bengal · India');
    expect(popupHtml).toContain('28&deg;C');
    expect(popupHtml).toContain('Feels:');
    expect(popupHtml).toContain('33&deg;C');
    expect(popupHtml).toContain('Rain:');
    expect(popupHtml).toContain('75%');
    expect(popupHtml).toContain('Wind:');
    expect(popupHtml).toContain('18 km/h');
  });

  it('supports comparison mode displaying Comparison badge and dual locations', () => {
    const mockLocationB: GeocodedLocationSchema = {
      name: 'Mumbai',
      admin1: 'Maharashtra',
      country: 'India',
      latitude: 19.076,
      longitude: 72.8777,
      timezone: 'Asia/Kolkata',
    };
    const mockWeatherB: TargetPeriodWeather = {
      ...mockWeather,
      temperature: 31,
    };

    render(
      <ThemeProvider>
        <WeatherMap
          location={mockLocation}
          weather={mockWeather}
          locationB={mockLocationB}
          weatherB={mockWeatherB}
          periodLabel="Today"
        />
      </ThemeProvider>
    );

    expect(screen.getByText(/Comparison: A vs B/i)).toBeDefined();
    expect(screen.getByText('Comparison location')).toBeDefined();
  });

  it('sanitizes potential XSS in location and condition strings', () => {
    const unsafeLoc: GeocodedLocationSchema = {
      ...mockLocation,
      name: '<script>alert("hack")</script>City',
    };
    const unsafeWeather: TargetPeriodWeather = {
      ...mockWeather,
      condition: '<img src=x onerror=alert(1)>Sunny',
    };
    const popup = createPopupHtml(unsafeLoc, unsafeWeather, 'Today');
    expect(popup).not.toContain('<script>');
    expect(popup).toContain('&lt;script&gt;');
    expect(popup).not.toContain('<img src=x');
  });

  it('calculates verified CSS tile filters for all themes', () => {
    // Vandal: deep maroon/burgundy
    const vandalFilter = getTileFilter('dark', 'vandal');
    expect(vandalFilter).toContain('invert(100%)');
    expect(vandalFilter).toContain('sepia(100%)');
    expect(vandalFilter).toContain('hue-rotate(305deg)');
    expect(vandalFilter).toContain('saturate(2.4)');

    // Atheris: cool dark blue-grey
    const atherisFilter = getTileFilter('dark', 'atheris');
    expect(atherisFilter).toContain('invert(100%)');
    expect(atherisFilter).toContain('hue-rotate(185deg)');

    // Midnight: cosmic purple
    const midnightFilter = getTileFilter('night', 'atheris');
    expect(midnightFilter).toContain('invert(100%)');
    expect(midnightFilter).toContain('hue-rotate(235deg)');

    // Light: clean natural
    expect(getTileFilter('light', 'atheris')).toBe('none');
  });

  it('generates redesigned focal marker hierarchy with central anchor dot and adjacent compact label', () => {
    const markerHtml = createMarkerHtml('Kolkata', mockWeather, '#ff2a55', '#ff2a55', true);
    // 1. Primary Focal Anchor Point
    expect(markerHtml).toContain('stormops-focal-dot');
    expect(markerHtml).toContain('stormops-beacon-outer');
    expect(markerHtml).toContain('stormops-beacon-inner');
    expect(markerHtml).toContain('stormops-condition-halo');

    // 2. Compact Adjacent Weather Label
    expect(markerHtml).toContain('stormops-focal-label');
    expect(markerHtml).toContain('stormops-label-temp');
    expect(markerHtml).toContain('28&deg;C');
    expect(markerHtml).toContain('stormops-label-place');
    expect(markerHtml).toContain('Kolkata');
    expect(markerHtml).toContain('stormops-label-rain');
    expect(markerHtml).toContain('75%');
  });

  it('attaches data-map-theme attribute to canvas container matching active theme', () => {
    const { container } = render(
      <ThemeProvider>
        <WeatherMap
          location={mockLocation}
          weather={mockWeather}
          periodLabel="Today"
        />
      </ThemeProvider>
    );

    const canvas = container.querySelector('.stormops-map-canvas');
    expect(canvas).toBeDefined();
    expect(canvas?.getAttribute('data-map-theme')).toBe('atheris');

    const overlay = container.querySelector('.stormops-map-atmosphere-overlay');
    expect(overlay).toBeDefined();
  });
});

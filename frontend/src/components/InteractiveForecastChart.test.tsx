import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import { InteractiveForecastChart } from './InteractiveForecastChart';
import { WeatherAnswerSurface } from './WeatherAnswerSurface';
import { HourlyForecast, QueryResponse } from '../types/weather';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthProvider } from '../context/AuthContext';

describe('Phase UI-06: 24-Hour Forecast Intelligence Tests', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  const mockHourlyItems: HourlyForecast[] = Array.from({ length: 24 }, (_, i) => {
    const hour = (i + 6) % 24; // 06:00 to 05:00 next day
    const hourStr = String(hour).padStart(2, '0');
    return {
      time: `2026-09-23T${hourStr}:00:00Z`,
      temperature: 24 + Math.sin(i / 3) * 6,
      feels_like: 26 + Math.sin(i / 3) * 7,
      condition: i >= 10 && i <= 14 ? 'heavy rain' : 'partly cloudy',
      weather_code: i >= 10 && i <= 14 ? 65 : 2,
      precipitation_probability: i >= 10 && i <= 14 ? 85 : 15,
      precipitation: i >= 10 && i <= 14 ? 4.5 : 0,
      wind_speed: 12 + i,
    };
  });

  it('renders 24-hour forecast header, legend, and SVG timeline', () => {
    render(
      <ThemeProvider>
        <InteractiveForecastChart
          items={mockHourlyItems}
          periodTitle="Today"
          timezone="Asia/Kolkata"
        />
      </ThemeProvider>
    );

    // Header & Evidence context
    expect(screen.getByText(/24-Hour Forecast Timeline/i)).toBeDefined();
    expect(screen.getByText(/· Evidence/i)).toBeDefined();
    expect(screen.getByText(/Hourly temperature progression and precipitation timing for Today/i)).toBeDefined();

    // Legend
    expect(screen.getByText('Temperature')).toBeDefined();
    expect(screen.getByText('Feels like')).toBeDefined();
    expect(screen.getByText('Rain %')).toBeDefined();

    // NOW marker
    expect(screen.getByText('NOW')).toBeDefined();

    // Midnight crossing marker (00:00)
    expect(screen.getAllByText('00:00').length).toBeGreaterThanOrEqual(1);
  });

  it('triggers onInspectHour and displays tooltip on mouse interaction', () => {
    const handleInspect = vi.fn();

    const { container } = render(
      <ThemeProvider>
        <InteractiveForecastChart
          items={mockHourlyItems}
          periodTitle="Today"
          timezone="Asia/Kolkata"
          onInspectHour={handleInspect}
        />
      </ThemeProvider>
    );

    const svg = container.querySelector('svg[aria-label="24-hour weather timeline chart"]');
    expect(svg).toBeDefined();

    // Mock bounding rect for SVG
    if (svg) {
      vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
        left: 0,
        top: 0,
        right: 640,
        bottom: 200,
        width: 640,
        height: 200,
        x: 0,
        y: 0,
        toJSON: () => {},
      });

      // Hover around middle of chart (~12th point)
      fireEvent.mouseMove(svg, { clientX: 320, clientY: 100 });

      expect(handleInspect).toHaveBeenCalled();
      const inspectedArg = handleInspect.mock.calls[0][0];
      expect(inspectedArg).toBeDefined();
      expect(typeof inspectedArg.temperature).toBe('number');

      // Floating tooltip should be rendered
      const tooltip = screen.getByRole('tooltip');
      expect(tooltip).toBeDefined();

      // Mouse leave should clear inspection
      fireEvent.mouseLeave(svg);
      expect(handleInspect).toHaveBeenCalledWith(null);
      expect(screen.queryByRole('tooltip')).toBeNull();
    }
  });

  it('supports keyboard navigation via ArrowRight, ArrowLeft, and Escape', () => {
    const handleInspect = vi.fn();

    render(
      <ThemeProvider>
        <InteractiveForecastChart
          items={mockHourlyItems}
          periodTitle="Today"
          timezone="Asia/Kolkata"
          onInspectHour={handleInspect}
        />
      </ThemeProvider>
    );

    const region = screen.getByRole('region', { name: /24-hour weather forecast timeline/i });
    expect(region).toBeDefined();

    // ArrowRight moves to next hour
    fireEvent.keyDown(region, { key: 'ArrowRight' });
    expect(handleInspect).toHaveBeenCalled();

    // ArrowLeft moves back
    fireEvent.keyDown(region, { key: 'ArrowLeft' });
    expect(handleInspect).toHaveBeenCalled();

    // Escape resets inspection
    fireEvent.keyDown(region, { key: 'Escape' });
    expect(handleInspect).toHaveBeenCalledWith(null);
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('handles missing feels_like and handles touch end timeout', () => {
    vi.useFakeTimers();

    const itemsNoFeelsLike: HourlyForecast[] = mockHourlyItems.map((item) => ({
      ...item,
      feels_like: null,
      precipitation: 0,
      precipitation_probability: null,
    }));

    const handleInspect = vi.fn();

    const { container } = render(
      <ThemeProvider>
        <InteractiveForecastChart
          items={itemsNoFeelsLike}
          periodTitle="Today"
          timezone="Asia/Kolkata"
          onInspectHour={handleInspect}
        />
      </ThemeProvider>
    );

    const svg = container.querySelector('svg[aria-label="24-hour weather timeline chart"]');
    if (svg) {
      vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
        left: 0,
        top: 0,
        right: 640,
        bottom: 200,
        width: 640,
        height: 200,
        x: 0,
        y: 0,
        toJSON: () => {},
      });

      // Touch start
      fireEvent.touchStart(svg, {
        touches: [{ clientX: 200, clientY: 100 }],
      });
      expect(handleInspect).toHaveBeenCalled();

      // Touch end
      fireEvent.touchEnd(svg);

      // Fast forward past 2.5s touch reset delay
      act(() => {
        vi.advanceTimersByTime(2600);
      });

      expect(handleInspect).toHaveBeenCalledWith(null);
    }

    vi.useRealTimers();
  });

  describe('Briefing ↔ Forecast Integration in WeatherAnswerSurface', () => {
    const mockResponse: QueryResponse = {
      query: {
        original_query: 'Forecast for Kolkata',
        intent: 'weather_query',
        extracted_location: 'Kolkata',
        date_context: 'today',
        time_period: 'day',
        language: 'en',
      },
      location: {
        name: 'Kolkata',
        admin1: 'West Bengal',
        country: 'India',
        latitude: 22.57,
        longitude: 88.36,
        timezone: 'Asia/Kolkata',
      },
      current: {
        temperature: 28,
        feels_like: 32,
        condition: 'scattered clouds',
        weather_code: 2,
        humidity: 75,
        wind_speed: 12,
        precipitation: 0,
        precipitation_probability: 10,
        time: '2026-09-23T12:00:00Z',
      },
      forecast: mockHourlyItems,
      summary: 'Warm day with evening rain expected.',
      key_insight: 'Thunderstorms and rain likely to develop by late afternoon.',
      official_advisories: [],
      timestamp: '2026-09-23T12:00:00Z',
    };

    it('updates telemetry strip when scrubbing forecast and allows reset to current', async () => {
      const { container } = render(
        <ThemeProvider>
          <AuthProvider>
            <WeatherAnswerSurface response={mockResponse} />
          </AuthProvider>
        </ThemeProvider>
      );

      // Initially shows current temperature 28°
      expect(screen.getByText('28°')).toBeDefined();
      expect(screen.queryByText(/Previewing Forecast:/i)).toBeNull();

      // Find forecast chart SVG
      const svg = container.querySelector('svg[aria-label="24-hour weather timeline chart"]');
      expect(svg).toBeDefined();

      if (svg) {
        vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
          left: 0,
          top: 0,
          right: 640,
          bottom: 200,
          width: 640,
          height: 200,
          x: 0,
          y: 0,
          toJSON: () => {},
        });

        // Hover over peak rain hour (~hour index 12 in mock: heavy rain, 85% rain)
        fireEvent.mouseMove(svg, { clientX: 330, clientY: 100 });

        // Telemetry should now show the preview banner
        expect(screen.getByText(/Previewing Forecast:/i)).toBeDefined();
        const resetBtn = screen.getByRole('button', { name: /Back to Current/i });
        expect(resetBtn).toBeDefined();

        // Clicking reset button clears preview back to current
        fireEvent.click(resetBtn);
        expect(screen.queryByText(/Previewing Forecast:/i)).toBeNull();
      }

      // WeatherGPT headline should remain intact and unchanged
      expect(
        screen.getByRole('heading', {
          level: 2,
          name: /Thunderstorms and rain likely to develop by late afternoon/i,
        })
      ).toBeDefined();
    });
  });
});

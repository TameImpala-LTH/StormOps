import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { WeatherLocationIdentity, buildLocationBreadcrumb } from './WeatherLocationIdentity';
import { WeatherGPTHero } from './WeatherGPTHero';
import { WeatherTelemetry } from './WeatherTelemetry';
import { WeatherAnswerSurface } from '../WeatherAnswerSurface';
import { QueryResponse, GeocodedLocationSchema } from '../../types/weather';
import { OfficialAdvisory } from '../../types/advisory';
import { AuthProvider } from '../../context/AuthContext';
import { ThemeProvider } from '../../context/ThemeContext';

describe('Phase UI-05: Weather Briefing Components & Hierarchy Tests', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('WeatherLocationIdentity', () => {
    it('builds authentic deduplicated hierarchy breadcrumb without fabrication', () => {
      const loc1: GeocodedLocationSchema = {
        name: 'Park Street',
        city: 'Kolkata',
        district: 'Kolkata',
        admin1: 'West Bengal',
        country: 'India',
        latitude: 22.55,
        longitude: 88.35,
        timezone: 'Asia/Kolkata',
      };
      // Should deduplicate "Kolkata" and skip primary name
      expect(buildLocationBreadcrumb(loc1)).toBe('Kolkata · West Bengal · India');

      const loc2: GeocodedLocationSchema = {
        name: 'Kolkata',
        admin1: 'West Bengal',
        country: 'India',
        latitude: 22.57,
        longitude: 88.36,
        timezone: 'Asia/Kolkata',
      };
      expect(buildLocationBreadcrumb(loc2)).toBe('West Bengal · India');

      const loc3: GeocodedLocationSchema = {
        name: 'London',
        country: 'United Kingdom',
        latitude: 51.5,
        longitude: -0.12,
        timezone: 'Europe/London',
      };
      expect(buildLocationBreadcrumb(loc3)).toBe('United Kingdom');
    });

    it('renders location name, real breadcrumb, and period context', () => {
      const loc: GeocodedLocationSchema = {
        name: 'Darjeeling',
        district: 'Darjeeling',
        admin1: 'West Bengal',
        country: 'India',
        latitude: 27.04,
        longitude: 88.26,
        timezone: 'Asia/Kolkata',
      };

      const handleSave = vi.fn();
      render(
        <WeatherLocationIdentity
          location={loc}
          periodTitle="Today"
          isLocationSaved={false}
          isAuthenticated={true}
          onToggleSaveLocation={handleSave}
          isEnvPanelOpen={false}
          onToggleEnvPanel={vi.fn()}
        />
      );

      expect(screen.getByRole('heading', { level: 1 }).textContent).toContain('Darjeeling');
      expect(screen.getByText('West Bengal · India')).toBeDefined();
      expect(screen.getByText('Today')).toBeDefined();

      const saveBtn = screen.getByRole('button', { name: /Save to favorites/i });
      fireEvent.click(saveBtn);
      expect(handleSave).toHaveBeenCalled();
    });
  });

  describe('WeatherGPTHero', () => {
    it('renders 3-level WeatherGPT hierarchy: headline, scannable bullets, and collapsible interpretation', () => {
      render(
        <WeatherGPTHero
          keyInsight="Heavy monsoon showers expected to intensify by evening."
          detailedSummary="Sustained rainfall with occasional thunderstorms throughout the night."
          condition="heavy rain"
          weatherCode={65}
          weather={{
            temperature: 28,
            feels_like: 33,
            condition: 'heavy rain',
            weather_code: 65,
            humidity: 85,
            wind_speed: 15,
            precipitation: 12.5,
            precipitation_probability: 90,
            peak_hour: '18:00',
          }}
          periodTitle="Today"
        />
      );

      // Level 1: Synthesis Headline & condition
      expect(screen.getByText(/WeatherGPT Briefing/i)).toBeDefined();
      expect(screen.getByText('heavy rain')).toBeDefined();
      expect(
        screen.getByRole('heading', { level: 2, name: /Heavy monsoon showers expected to intensify by evening/i })
      ).toBeDefined();

      // Level 2: Scannable Briefing Bullets
      expect(screen.getByText('Conditions & Comfort')).toBeDefined();
      expect(screen.getByText(/Feels warmer than actual temperature/i)).toBeDefined();
      expect(screen.getByText('Rain & Timing')).toBeDefined();
      expect(screen.getByText(/High likelihood of precipitation \(90%\), peaking around 18:00/i)).toBeDefined();
      expect(screen.getByText('Wind & Air')).toBeDefined();
      expect(screen.getByText('Practical Advice')).toBeDefined();

      // Level 3: Collapsible Detailed Interpretation (collapsed by default)
      const toggleBtn = screen.getByRole('button', { name: /Read Detailed Interpretation/i });
      expect(toggleBtn).toBeDefined();
      expect(toggleBtn.getAttribute('aria-expanded')).toBe('false');
      expect(screen.queryByText(/Sustained rainfall with occasional thunderstorms/i)).toBeNull();

      // Expand disclosure
      fireEvent.click(toggleBtn);
      expect(toggleBtn.getAttribute('aria-expanded')).toBe('true');
      expect(screen.getByText(/Sustained rainfall with occasional thunderstorms/i)).toBeDefined();

      // Collapse disclosure
      fireEvent.click(toggleBtn);
      expect(toggleBtn.getAttribute('aria-expanded')).toBe('false');
      expect(screen.queryByText(/Sustained rainfall with occasional thunderstorms/i)).toBeNull();
    });

    it('renders action recommendation pill and real confidence only when backend decision exists', () => {
      render(
        <WeatherGPTHero
          keyInsight="Continuous rain anticipated across south Kolkata."
          condition="rain"
          weatherCode={61}
          periodTitle="Today"
          decision={{
            type: 'umbrella',
            recommendation: 'umbrella_recommended',
            confidence: 'high',
            summary: 'Umbrella strongly advised for outdoors',
            factors: [],
          }}
        />
      );

      expect(screen.getByText('umbrella recommended')).toBeDefined();
      expect(screen.getByText('high confidence')).toBeDefined();
    });

    it('renders unavailable forecast state when period data is missing', () => {
      render(
        <WeatherGPTHero
          keyInsight=""
          condition="unknown"
          weatherCode={0}
          isUnavailable={true}
          periodTitle="Tomorrow Evening"
        />
      );

      expect(screen.getByText(/Forecast Unavailable for Tomorrow Evening/i)).toBeDefined();
      expect(screen.getByText(/Current observation values are strictly not substituted/i)).toBeDefined();
    });

    it('gracefully renders multilingual WeatherGPT synthesis without truncation', () => {
      const hindiInsight = 'आज शाम कोलकाता में भारी बारिश की संभावना है।';
      const { rerender } = render(
        <WeatherGPTHero
          keyInsight={hindiInsight}
          condition="rain"
          weatherCode={61}
          periodTitle="Today"
        />
      );

      expect(screen.getByText(hindiInsight)).toBeDefined();

      const bengaliInsight = 'আজ সন্ধ্যায় কলকাতায় মাঝারি থেকে ভারী বৃষ্টির সম্ভাবনা রয়েছে।';
      rerender(
        <WeatherGPTHero
          keyInsight={bengaliInsight}
          condition="rain"
          weatherCode={61}
          periodTitle="Today"
        />
      );

      expect(screen.getByText(bengaliInsight)).toBeDefined();
    });
  });

  describe('WeatherTelemetry', () => {
    it('renders single borderless telemetry strip with connected temperature and feels-like', () => {
      render(
        <WeatherTelemetry
          weather={{
            temperature: 28.4,
            feels_like: 33.2,
            condition: 'Humid & Overcast',
            weather_code: 3,
            humidity: 82,
            wind_speed: 18,
            precipitation: 1.2,
            precipitation_probability: 75,
            peak_hour: '18:00',
          }}
        />
      );

      // Tabular temperature and connected feels-like
      expect(screen.getByText('28°')).toBeDefined();
      expect(screen.getByText(/Feels 33°C/i)).toBeDefined();

      // Rain probability and peak hour
      expect(screen.getByText('75%')).toBeDefined();
      expect(screen.getByText('Peak 18:00')).toBeDefined();

      // Wind and humidity
      expect(screen.getByText('km/h')).toBeDefined();
      expect(screen.getByText('Moderate breeze')).toBeDefined();
      expect(screen.getByText('82%')).toBeDefined();
      expect(screen.getByText('Humid')).toBeDefined();

      // AQI omitted when no AQI advisory present, ensuring balanced 4-column desktop grid
      expect(screen.queryByText(/Air Quality/i)).toBeNull();
      const grid4 = screen.getByTestId('telemetry-grid');
      expect(grid4.className).toContain('sm:grid-cols-4');
      expect(grid4.className).not.toContain('sm:grid-cols-5');
      expect(grid4.className).not.toContain('lg:grid-cols-5');

      // Verify each column contains centered content structure avoiding leftward skew
      expect(grid4.children[0].className).toContain('justify-start sm:justify-center');
      expect(grid4.children[3].className).toContain('justify-start sm:justify-center');
    });

    it('renders AQI in telemetry when official air quality advisory is present with 5 columns', () => {
      const aqiAdvisory: OfficialAdvisory = {
        id: 'adv-cpcb-01',
        source_id: 'cpcb-dl-01',
        authority: 'CPCB',
        hazard_type: 'air_quality',
        severity: 'orange',
        official_level: 'AQI 280 (POOR)',
        issued_at: '2026-09-23T10:00:00Z',
        effective_at: '2026-09-23T10:00:00Z',
        expires_at: '2026-09-23T22:00:00Z',
        is_active: true,
        granularity: 'district',
        headline: 'Poor air quality advisory in Delhi NCR',
        description: 'Elevated PM2.5 levels detected across NCR stations.',
        created_at: '2026-09-23T10:00:00Z',
        updated_at: '2026-09-23T10:00:00Z',
      };

      render(
        <WeatherTelemetry
          weather={{
            temperature: 31,
            feels_like: 35,
            condition: 'Hazy',
            weather_code: 5,
            humidity: 50,
            wind_speed: 10,
            precipitation: 0,
            precipitation_probability: 10,
          }}
          advisories={[aqiAdvisory]}
        />
      );

      expect(screen.getByText(/Air Quality/i)).toBeDefined();
      expect(screen.getByText('AQI 280')).toBeDefined();
      expect(screen.getByText('Poor')).toBeDefined();

      const grid5 = screen.getByTestId('telemetry-grid');
      expect(grid5.className).toContain('sm:grid-cols-5');
    });
  });

  describe('WeatherAnswerSurface Integration', () => {
    const mockResponse: QueryResponse = {
      query: {
        original_query: 'Will it rain in Kolkata today?',
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
        temperature: 29.2,
        feels_like: 34.1,
        condition: 'scattered clouds',
        weather_code: 2,
        humidity: 78,
        wind_speed: 14,
        precipitation: 0,
        precipitation_probability: 25,
        time: '2026-09-23T12:00:00Z',
      },
      summary: 'Partly cloudy conditions with warm temperatures and low precipitation chance.',
      key_insight: 'Warm and humid conditions persist throughout Kolkata with minimal rain risk.',
      official_advisories: [],
      timestamp: '2026-09-23T12:00:00Z',
    };

    it('renders the complete intelligence briefing hierarchy without duplicate metrics', () => {
      render(
        <ThemeProvider>
          <AuthProvider>
            <WeatherAnswerSurface response={mockResponse} />
          </AuthProvider>
        </ThemeProvider>
      );

      // 1. Location identity
      expect(screen.getByRole('heading', { level: 1 }).textContent).toContain('Kolkata');
      expect(screen.getByText('West Bengal · India')).toBeDefined();

      // 2. WeatherGPT synthesis headline
      expect(
        screen.getByRole('heading', {
          level: 2,
          name: /Warm and humid conditions persist throughout Kolkata/i,
        })
      ).toBeDefined();

      // 3. Telemetry strip
      expect(screen.getByText('29°')).toBeDefined();
      expect(screen.getByText(/Feels 34°C/i)).toBeDefined();

      // Verify absence of old duplicate 5xl hero temperature block
      const tempMatches = screen.getAllByText('29°');
      // Exactly ONE primary temperature numeral in the entire surface
      expect(tempMatches.length).toBe(1);
    });

    it('places official active warning above WeatherGPT synthesis when advisory exists', () => {
      const now = Date.now();
      const redAdvisory: OfficialAdvisory = {
        id: 'adv-imd-red-1',
        source_id: 'imd-red-1',
        authority: 'IMD',
        hazard_type: 'heavy_rainfall',
        severity: 'red',
        headline: 'RED ALERT: Extremely heavy rainfall expected in Coastal Bengal',
        description: 'Very heavy rainfall with localized inundation.',
        issued_at: new Date(now - 3600000).toISOString(),
        effective_at: new Date(now - 3600000).toISOString(),
        expires_at: new Date(now + 36000000).toISOString(),
        is_active: true,
        granularity: 'district',
        district: 'Kolkata',
        state: 'West Bengal',
        created_at: new Date(now - 3600000).toISOString(),
        updated_at: new Date(now - 3600000).toISOString(),
      };

      const responseWithAdvisory: QueryResponse = {
        ...mockResponse,
        official_advisories: [redAdvisory],
      };

      render(
        <ThemeProvider>
          <AuthProvider>
            <WeatherAnswerSurface response={responseWithAdvisory} />
          </AuthProvider>
        </ThemeProvider>
      );

      // Official Red Alert banner should render
      expect(screen.getAllByText(/RED ALERT: Extremely heavy rainfall/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Official Government Advisory/i)).toBeDefined();

      // WeatherGPT hero should also render below it
      expect(
        screen.getByRole('heading', {
          level: 2,
          name: /Warm and humid conditions persist throughout Kolkata/i,
        })
      ).toBeDefined();
    });
  });
});

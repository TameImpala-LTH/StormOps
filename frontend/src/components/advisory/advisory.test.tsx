import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { AdvisorySeverityBadge } from './AdvisorySeverityBadge';
import { OfficialAdvisoryBanner } from './OfficialAdvisoryBanner';
import { OfficialAdvisoryCard } from './OfficialAdvisoryCard';
import { AirQualityCard } from './AirQualityCard';
import { OfficialAdvisorySection } from './OfficialAdvisorySection';
import { EnvironmentalEventIndicator } from '../EnvironmentalEventIndicator';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../../types/advisory';
import {
  getAdvisoryGeometryType,
  getSeverityTokens,
  escapeHtml,
  formatAdvisoryTime,
  createAdvisoryMarkerHtml,
  createAdvisoryTooltipHtml,
  createAdvisoryPopupHtml,
} from '../WeatherMap';

afterEach(() => {
  cleanup();
});

const mockRedAdvisory: OfficialAdvisory = {
  id: 'adv-001',
  source_id: 'imd-rain-001',
  authority: 'IMD',
  hazard_type: 'EXTREME_RAIN',
  severity: 'red',
  official_level: 'Warning (Take Action)',
  issued_at: new Date(Date.now() - 3600000).toISOString(),
  effective_at: new Date(Date.now() - 1800000).toISOString(),
  expires_at: new Date(Date.now() + 18000000).toISOString(),
  is_active: true,
  granularity: 'district',
  district: 'Kolkata',
  state: 'West Bengal',
  headline: 'Extremely Heavy Rainfall Expected in Kolkata',
  description: 'Inundation and waterlogging likely in low lying municipal wards.',
  action_guidance: 'Avoid stepping outdoors unless strictly emergency. Secure loose items.',
  source_url: 'https://mausam.imd.gov.in',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockOrangeAdvisory: OfficialAdvisory = {
  id: 'adv-002',
  source_id: 'imd-cyclone-002',
  authority: 'IMD',
  hazard_type: 'CYCLONE',
  severity: 'orange',
  official_level: 'Alert (Be Prepared)',
  issued_at: new Date(Date.now() - 7200000).toISOString(),
  effective_at: new Date(Date.now() - 3600000).toISOString(),
  expires_at: new Date(Date.now() + 36000000).toISOString(),
  is_active: true,
  granularity: 'state',
  state: 'Odisha',
  headline: 'Cyclonic Storm Approaching Coastal Odisha',
  description: 'Wind speeds up to 90 kmph expected along coastline.',
  source_url: 'https://mausam.imd.gov.in',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockUpcomingAdvisory: OfficialAdvisory = {
  id: 'adv-003',
  source_id: 'imd-fog-003',
  authority: 'IMD',
  hazard_type: 'DENSE_FOG',
  severity: 'yellow',
  official_level: 'Watch (Be Updated)',
  issued_at: new Date().toISOString(),
  effective_at: new Date(Date.now() + 43200000).toISOString(), // Starts in 12h
  expires_at: new Date(Date.now() + 86400000).toISOString(),
  is_active: true,
  granularity: 'district',
  district: 'Patna',
  state: 'Bihar',
  headline: 'Dense Fog Watch for Morning Commute',
  description: 'Visibility may drop below 200m during early morning hours.',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockAqiAdvisory: OfficialAdvisory = {
  id: 'adv-aqi-004',
  source_id: 'cpcb-delhi-004',
  authority: 'CPCB',
  hazard_type: 'AIR_QUALITY',
  severity: 'red',
  official_level: 'AQI 412 (Severe)',
  issued_at: new Date().toISOString(),
  effective_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 14400000).toISOString(),
  is_active: true,
  granularity: 'station',
  district: 'Delhi',
  state: 'Delhi',
  headline: 'CPCB Air Quality Bulletin: Delhi is Severe',
  description: 'Station: Anand Vihar. Prominent pollutant is PM2.5.',
  action_guidance: 'Avoid physical exertion outdoors. Keep air purifiers operational.',
  source_url: 'https://app.cpcbccr.com/caaqm',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('Advisory UI Component Suite', () => {
  // 1. Severity Badge Tests
  it('renders severity badge with official level verbatim text', () => {
    render(<AdvisorySeverityBadge severity="red" officialLevel="Warning (Take Action)" />);
    expect(screen.getByText('WARNING (TAKE ACTION)')).toBeDefined();
  });

  it('renders default severity label when officialLevel is absent', () => {
    render(<AdvisorySeverityBadge severity="orange" />);
    expect(screen.getByText('ORANGE · ALERT')).toBeDefined();
  });

  // 2. Severe Alert Banner Tests
  it('renders active Orange/Red alert banner prominently near top', () => {
    render(<OfficialAdvisoryBanner advisories={[mockRedAdvisory]} />);
    expect(screen.getByText('Extremely Heavy Rainfall Expected in Kolkata')).toBeDefined();
    expect(screen.getByText(/India Meteorological Department/)).toBeDefined();
    expect(screen.getByText('Avoid stepping outdoors unless strictly emergency. Secure loose items.')).toBeDefined();
  });

  it('suppresses alert banner when only Yellow or Green advisories exist', () => {
    const { container } = render(<OfficialAdvisoryBanner advisories={[mockUpcomingAdvisory]} />);
    expect(container.firstChild).toBeNull();
  });

  it('supports multiple severe advisories in banner', () => {
    render(<OfficialAdvisoryBanner advisories={[mockRedAdvisory, mockOrangeAdvisory]} />);
    expect(screen.getByLabelText('View advisory 1 of 2')).toBeDefined();
    expect(screen.getByLabelText('View advisory 2 of 2')).toBeDefined();
  });

  // 3. Official Advisory Card Tests
  it('renders active advisory card with ACTIVE NOW status', () => {
    render(<OfficialAdvisoryCard advisory={mockRedAdvisory} />);
    expect(screen.getByText('ACTIVE NOW')).toBeDefined();
    expect(screen.getByText('EXTREME RAIN')).toBeDefined();
    expect(screen.getByText('Official Portal')).toBeDefined();
  });

  it('renders upcoming advisory card with UPCOMING status', () => {
    render(<OfficialAdvisoryCard advisory={mockUpcomingAdvisory} />);
    expect(screen.getByText('UPCOMING')).toBeDefined();
    expect(screen.getByText('Dense Fog Watch for Morning Commute')).toBeDefined();
  });

  // 4. Air Quality Card Tests
  it('renders AQI bulletin strictly separated from meteorological storm warnings', () => {
    render(<AirQualityCard advisory={mockAqiAdvisory} />);
    expect(screen.getByText('412')).toBeDefined();
    expect(screen.getByText('SEVERE')).toBeDefined();
    expect(screen.getByText(/Central Pollution Control Board/)).toBeDefined();
    expect(screen.getByText('Station: Delhi')).toBeDefined();
  });

  // 5. Official Advisory Section Tests
  it('renders active, upcoming, and AQI sections in structured hierarchy', () => {
    render(
      <OfficialAdvisorySection
        advisories={[mockRedAdvisory, mockUpcomingAdvisory, mockAqiAdvisory]}
        locationName="Kolkata"
      />
    );
    expect(screen.getByText('AIR QUALITY BULLETIN')).toBeDefined();
    expect(screen.getByText('ACTIVE ADVISORIES NOW')).toBeDefined();
    expect(screen.getByText('UPCOMING WATCHES & ADVANCE ALERTS')).toBeDefined();
  });

  it('renders restrained empty state when zero advisories and showEmptyState is true', () => {
    render(<OfficialAdvisorySection advisories={[]} locationName="Jaipur" showEmptyState={true} />);
    expect(
      screen.getByText('No active official advisories are currently available for this location.')
    ).toBeDefined();
  });

  it('renders null when zero advisories and showEmptyState is false', () => {
    const { container } = render(
      <OfficialAdvisorySection advisories={[]} locationName="Jaipur" showEmptyState={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  // 6. Header Indicator Tests
  it('displays combined count and alert styling in EnvironmentalEventIndicator', () => {
    render(
      <EnvironmentalEventIndicator
        advisories={[mockRedAdvisory]}
        events={[
          {
            id: 'ev-1',
            title: 'Durga Puja',
            category: 'cultural',
            geographic_scope: ['Kolkata'],
            occurrences: [],
            environmental_pressures: [],
            advisory_summary: 'Crowd density high',
            key_recommendations: [],
            source_metadata: 'StormOps',
          },
        ]}
        isOpen={false}
        onToggle={() => {}}
      />
    );
    // 1 advisory + 1 civic event = 2 total
    expect(screen.getByText('2')).toBeDefined();
    expect(screen.getByTitle('1 Official Advisory · 1 Civic Event')).toBeDefined();
  });

  // 7. Phase 18.7 — Map Advisory Geometry & Visualization Tests
  describe('Phase 18.7: Map Advisory Geometry & Styling Rules', () => {
    it('Rule 1: identifies polygon_geojson as polygon geometry', () => {
      const advWithPolygon: OfficialAdvisory = {
        ...mockRedAdvisory,
        polygon_geojson: JSON.stringify({
          type: 'Polygon',
          coordinates: [
            [
              [88.3, 22.5],
              [88.4, 22.5],
              [88.4, 22.6],
              [88.3, 22.6],
              [88.3, 22.5],
            ],
          ],
        }),
      };
      expect(getAdvisoryGeometryType(advWithPolygon)).toBe('polygon');
    });

    it('Rule 1: identifies MultiPolygon GeoJSON as polygon geometry', () => {
      const advWithMultiPoly: OfficialAdvisory = {
        ...mockOrangeAdvisory,
        polygon_geojson: JSON.stringify({
          type: 'MultiPolygon',
          coordinates: [
            [
              [
                [85.8, 20.2],
                [85.9, 20.2],
                [85.9, 20.3],
                [85.8, 20.3],
                [85.8, 20.2],
              ],
            ],
          ],
        }),
      };
      expect(getAdvisoryGeometryType(advWithMultiPoly)).toBe('polygon');
    });

    it('Rule 2: identifies lat + lng + radius_km as circle geometry', () => {
      const advWithCircle: OfficialAdvisory = {
        ...mockRedAdvisory,
        polygon_geojson: null,
        latitude: 22.5726,
        longitude: 88.3639,
        radius_km: 25,
      };
      expect(getAdvisoryGeometryType(advWithCircle)).toBe('circle');
    });

    it('Rule 3: identifies lat + lng without radius as point marker geometry', () => {
      const advWithPoint: OfficialAdvisory = {
        ...mockRedAdvisory,
        polygon_geojson: null,
        latitude: 22.5726,
        longitude: 88.3639,
        radius_km: null,
      };
      expect(getAdvisoryGeometryType(advWithPoint)).toBe('point');
    });

    it('Rule 4: strictly rejects district/state-only advisories without geometry (no fake polygons)', () => {
      const advDistrictOnly: OfficialAdvisory = {
        ...mockRedAdvisory,
        polygon_geojson: null,
        latitude: null,
        longitude: null,
        radius_km: null,
        district: 'Kolkata',
        state: 'West Bengal',
      };
      expect(getAdvisoryGeometryType(advDistrictOnly)).toBeNull();
    });

    it('handles malformed GeoJSON gracefully by falling back to coordinates', () => {
      const advMalformedGeo: OfficialAdvisory = {
        ...mockRedAdvisory,
        polygon_geojson: 'NOT_VALID_JSON{foo}',
        latitude: 22.57,
        longitude: 88.36,
        radius_km: 15,
      };
      // Safely catches JSON parse error and falls back to circle
      expect(getAdvisoryGeometryType(advMalformedGeo)).toBe('circle');
    });

    it('provides correct theme severity tokens for all severity levels', () => {
      const redTokens = getSeverityTokens('red');
      expect(redTokens.stroke).toBe('#f43f5e');
      expect(redTokens.label).toContain('RED');

      const orangeTokens = getSeverityTokens('orange');
      expect(orangeTokens.stroke).toBe('#f97316');
      expect(orangeTokens.label).toContain('ORANGE');

      const yellowTokens = getSeverityTokens('yellow');
      expect(yellowTokens.stroke).toBe('#eab308');
      expect(yellowTokens.label).toContain('YELLOW');

      const greenTokens = getSeverityTokens('green');
      expect(greenTokens.stroke).toBe('#10b981');
      expect(greenTokens.label).toContain('GREEN');

      const unknownTokens = getSeverityTokens('unknown');
      expect(unknownTokens.stroke).toBe('#a1a1aa');
      expect(unknownTokens.label).toBe('ADVISORY');
    });

    it('formats active vs upcoming advisory previews appropriately', () => {
      const activeTokens = getSeverityTokens('red');
      const activeHtml = createAdvisoryTooltipHtml(mockRedAdvisory, activeTokens, false);
      expect(activeHtml).toContain('Expires:');
      expect(activeHtml).not.toContain('(UPCOMING)');

      const upcomingTokens = getSeverityTokens('yellow');
      const upcomingHtml = createAdvisoryTooltipHtml(mockUpcomingAdvisory, upcomingTokens, true);
      expect(upcomingHtml).toContain('(UPCOMING)');
      expect(upcomingHtml).toContain('Effective:');
    });

    it('formats marker HTML with dashed border for upcoming and solid for active', () => {
      const activeMarker = createAdvisoryMarkerHtml(getSeverityTokens('red'), false);
      expect(activeMarker).toContain('solid');

      const upcomingMarker = createAdvisoryMarkerHtml(getSeverityTokens('yellow'), true);
      expect(upcomingMarker).toContain('dashed');
    });

    it('properly sanitizes XSS strings in advisory popup HTML', () => {
      const maliciousAdv: OfficialAdvisory = {
        ...mockRedAdvisory,
        headline: '<script>alert("xss")</script>Flood Alert',
        description: '<img src=x onerror=alert(1)>Critical inundation',
        authority: 'IMD & NDMA',
      };
      const popupHtml = createAdvisoryPopupHtml(maliciousAdv, getSeverityTokens('red'), false);
      expect(popupHtml).not.toContain('<script>');
      expect(popupHtml).toContain('&lt;script&gt;');
      expect(popupHtml).not.toContain('<img src=x');
      expect(popupHtml).toContain('&lt;img src=x');
      expect(popupHtml).toContain('IMD &amp; NDMA');
    });

    it('escapeHtml escapes dangerous HTML characters and handles empty input', () => {
      expect(escapeHtml('<div class="test">It\'s a test & more</div>')).toBe(
        '&lt;div class=&quot;test&quot;&gt;It&#039;s a test &amp; more&lt;/div&gt;'
      );
      expect(escapeHtml(null)).toBe('');
      expect(escapeHtml(undefined)).toBe('');
    });

    it('formatAdvisoryTime formats ISO strings cleanly and handles invalid values', () => {
      const formatted = formatAdvisoryTime('2026-09-19T10:30:00Z');
      expect(formatted).toBeTruthy();
      expect(formatAdvisoryTime(null)).toBe('');
      expect(formatAdvisoryTime('invalid-date')).toBe('');
    });
  });

  // 8. Phase 18.7.1 — Temporal Validity State Evaluation
  describe('Phase 18.7.1: Advisory Temporal-State Validation', () => {
    const fixedNow = new Date('2026-09-19T12:00:00Z');

    it('identifies ACTIVE advisory when effective_at <= now < expires_at', () => {
      const activeAdv = {
        effective_at: '2026-09-19T10:00:00Z', // 2 hours ago
        expires_at: '2026-09-19T18:00:00Z',   // in 6 hours
        is_active: true,
      };
      expect(getAdvisoryTemporalState(activeAdv, fixedNow)).toBe('ACTIVE');
    });

    it('identifies UPCOMING advisory when effective_at > now', () => {
      const upcomingAdv = {
        effective_at: '2026-09-19T15:00:00Z', // in 3 hours
        expires_at: '2026-09-20T00:00:00Z',
        is_active: false,
      };
      expect(getAdvisoryTemporalState(upcomingAdv, fixedNow)).toBe('UPCOMING');
    });

    it('identifies EXPIRED advisory when expires_at <= now', () => {
      const expiredAdv = {
        effective_at: '2026-09-19T06:00:00Z',
        expires_at: '2026-09-19T11:59:59Z', // 1 sec ago
        is_active: false,
      };
      expect(getAdvisoryTemporalState(expiredAdv, fixedNow)).toBe('EXPIRED');
    });

    it('does NOT assume is_active === false implies UPCOMING (expired is EXPIRED)', () => {
      const expiredWithFalse = {
        effective_at: '2026-09-18T00:00:00Z',
        expires_at: '2026-09-19T00:00:00Z', // expired 12 hours ago
        is_active: false,
      };
      expect(getAdvisoryTemporalState(expiredWithFalse, fixedNow)).toBe('EXPIRED');
    });

    it('handles multiple advisories with different temporal states accurately', () => {
      const advisoriesList: OfficialAdvisory[] = [
        {
          ...mockRedAdvisory,
          id: 'adv-active',
          effective_at: '2026-09-19T10:00:00Z',
          expires_at: '2026-09-19T16:00:00Z',
        },
        {
          ...mockUpcomingAdvisory,
          id: 'adv-upcoming',
          effective_at: '2026-09-19T14:00:00Z',
          expires_at: '2026-09-19T20:00:00Z',
        },
        {
          ...mockOrangeAdvisory,
          id: 'adv-expired',
          effective_at: '2026-09-18T08:00:00Z',
          expires_at: '2026-09-19T08:00:00Z',
        },
      ];

      const active = advisoriesList.filter((a) => getAdvisoryTemporalState(a, fixedNow) === 'ACTIVE');
      const upcoming = advisoriesList.filter((a) => getAdvisoryTemporalState(a, fixedNow) === 'UPCOMING');
      const expired = advisoriesList.filter((a) => getAdvisoryTemporalState(a, fixedNow) === 'EXPIRED');

      expect(active.map((a) => a.id)).toEqual(['adv-active']);
      expect(upcoming.map((a) => a.id)).toEqual(['adv-upcoming']);
      expect(expired.map((a) => a.id)).toEqual(['adv-expired']);
    });

    it('renders ACTIVE NOW, UPCOMING, and EXPIRED badges correctly in OfficialAdvisoryCard', () => {
      const activeCardAdv: OfficialAdvisory = {
        ...mockRedAdvisory,
        effective_at: new Date(Date.now() - 3600000).toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };
      const { rerender } = render(<OfficialAdvisoryCard advisory={activeCardAdv} />);
      expect(screen.getByText('ACTIVE NOW')).toBeDefined();

      const upcomingCardAdv: OfficialAdvisory = {
        ...mockUpcomingAdvisory,
        effective_at: new Date(Date.now() + 7200000).toISOString(),
        expires_at: new Date(Date.now() + 18000000).toISOString(),
      };
      rerender(<OfficialAdvisoryCard advisory={upcomingCardAdv} />);
      expect(screen.getByText('UPCOMING')).toBeDefined();

      const expiredCardAdv: OfficialAdvisory = {
        ...mockOrangeAdvisory,
        effective_at: new Date(Date.now() - 7200000).toISOString(),
        expires_at: new Date(Date.now() - 3600000).toISOString(),
      };
      rerender(<OfficialAdvisoryCard advisory={expiredCardAdv} />);
      expect(screen.getByText('EXPIRED')).toBeDefined();
    });
  });
});


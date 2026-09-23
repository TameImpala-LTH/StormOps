import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { EventsDrawer } from './EventsDrawer';
import { WeatherLocationIdentity } from '../briefing/WeatherLocationIdentity';
import { EnvironmentalEvent } from '../../types/weather';

afterEach(() => {
  cleanup();
});

const MOCK_EVENT: EnvironmentalEvent = {
  id: 'kolkata-durga-puja-2026',
  title: 'Durga Puja Festival',
  category: 'festival',
  geographic_scope: ['Kolkata', 'Howrah', 'West Bengal'],
  occurrences: [
    {
      year: 2026,
      start_date: '2026-10-16',
      end_date: '2026-10-21',
      post_event_days: 3,
    },
  ],
  environmental_pressures: [
    { type: 'traffic', level: 'severe', evidence_type: 'historical_pattern' },
    { type: 'congestion', level: 'high', evidence_type: 'observed' },
  ],
  advisory_summary: 'Major public gatherings and pandal installations across Kolkata.',
  key_recommendations: ['Expect road closures around central pandals.'],
  source_metadata: 'Verified 2026 West Bengal Official Holiday Calendar',
  days_until: 23,
};

describe('UI-10: EventsDrawer Surface & Workflow', () => {
  it('renders quiet empty state when no events are available', () => {
    const onClose = vi.fn();
    render(
      <EventsDrawer
        isOpen={true}
        onClose={onClose}
        events={[]}
      />
    );

    expect(screen.getByText(/Events & Information/i)).toBeDefined();
    expect(screen.getByTestId('events-empty-state')).toBeDefined();
    expect(
      screen.getByText(/No regional events or scheduled disruptions currently catalogued/i)
    ).toBeDefined();

    // Close button works
    const closeBtn = screen.getByRole('button', { name: /Close events panel/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders verified event cards with affected location buttons and executes workflow on selection', () => {
    const onSelectLocation = vi.fn();
    const onClose = vi.fn();

    render(
      <EventsDrawer
        isOpen={true}
        onClose={onClose}
        events={[MOCK_EVENT]}
        onSelectLocation={onSelectLocation}
        activeLocationName="Kolkata"
      />
    );

    // Event details
    expect(screen.getByText('Durga Puja Festival')).toBeDefined();
    expect(screen.getByText(/2026-10-16 to 2026-10-21/)).toBeDefined();
    expect(screen.getByText(/Starts in 23 days/i)).toBeDefined();
    expect(screen.getByText(MOCK_EVENT.advisory_summary)).toBeDefined();

    // Affected locations are rendered as clickable buttons
    const howrahBtn = screen.getByRole('button', { name: /View WeatherGPT forecast for Howrah/i });
    expect(howrahBtn).toBeDefined();

    // Workflow: Clicking Howrah invokes onSelectLocation('Howrah')
    fireEvent.click(howrahBtn);
    expect(onSelectLocation).toHaveBeenCalledWith('Howrah');
  });

  it('verifies WeatherLocationIdentity does NOT render inline CIVIC indicator', () => {
    const mockLocation = {
      name: 'Kolkata',
      admin1: 'West Bengal',
      country: 'India',
      latitude: 22.57,
      longitude: 88.36,
      timezone: 'Asia/Kolkata',
    };

    render(
      <WeatherLocationIdentity
        location={mockLocation}
        periodTitle="TODAY"
        isLocationSaved={false}
        isAuthenticated={true}
        onToggleSaveLocation={() => {}}
        environmentalEvents={[MOCK_EVENT]}
        advisories={[]}
        isEnvPanelOpen={false}
        onToggleEnvPanel={() => {}}
      />
    );

    // Location title renders purely
    expect(screen.getByRole('heading', { level: 1, name: 'Kolkata' })).toBeDefined();
    expect(screen.getByText(/West Bengal · India/i)).toBeDefined();

    // The inline CIVIC indicator is completely gone
    expect(screen.queryByText(/CIVIC/i)).toBeNull();
  });
});

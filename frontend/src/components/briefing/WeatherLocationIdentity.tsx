import React from 'react';
import { MapPin, Star } from 'lucide-react';
import { GeocodedLocationSchema, ComparisonResponse, EnvironmentalEvent } from '../../types/weather';
import { OfficialAdvisory } from '../../types/advisory';
import { EnvironmentalEventIndicator } from '../EnvironmentalEventIndicator';

interface WeatherLocationIdentityProps {
  location?: GeocodedLocationSchema | null;
  comparison?: ComparisonResponse | null;
  periodTitle: string;
  isLocationSaved: boolean;
  isAuthenticated: boolean;
  onToggleSaveLocation: (e: React.MouseEvent) => void;
  environmentalEvents?: EnvironmentalEvent[] | null;
  advisories?: OfficialAdvisory[];
  isEnvPanelOpen: boolean;
  onToggleEnvPanel: () => void;
}

/**
 * Builds an authentic, deduplicated administrative hierarchy line
 * from real geocoded fields only. Never invents or fabricates hierarchy.
 */
export function buildLocationBreadcrumb(location: GeocodedLocationSchema): string {
  const parts: string[] = [];
  const primaryName = (location.name || '').trim().toLowerCase();

  const candidateFields = [
    location.district,
    location.city,
    location.admin1,
    location.state,
    location.country,
  ];

  for (const field of candidateFields) {
    if (!field) continue;
    const trimmed = field.trim();
    if (!trimmed) continue;
    const lower = trimmed.toLowerCase();
    // Skip if identical to primary name or already added to parts
    if (lower === primaryName) continue;
    if (parts.some((p) => p.toLowerCase() === lower)) continue;
    parts.push(trimmed);
  }

  return parts.join(' · ');
}

export const WeatherLocationIdentity: React.FC<WeatherLocationIdentityProps> = ({
  location,
  comparison,
  periodTitle,
  isLocationSaved,
  isAuthenticated,
  onToggleSaveLocation,
  environmentalEvents,
  advisories = [],
  isEnvPanelOpen,
  onToggleEnvPanel,
}) => {
  const primaryTitle = comparison
    ? `${comparison.location_a.name} vs ${comparison.location_b.name}`
    : location?.name || 'Weather Intelligence';

  const secondaryBreadcrumb = location && !comparison ? buildLocationBreadcrumb(location) : null;
  const hasEnvIndicators = (environmentalEvents && environmentalEvents.length > 0) || advisories.length > 0;

  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 gap-2 border-b"
      style={{ borderColor: 'var(--border-subtle)' }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <MapPin className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
          <h1
            className="text-xl sm:text-2xl font-light tracking-tight truncate"
            style={{ color: 'var(--text-primary)' }}
          >
            {primaryTitle}
          </h1>

          {/* Star favorite toggle */}
          {location && !comparison && (
            <button
              type="button"
              onClick={onToggleSaveLocation}
              title={
                !isAuthenticated
                  ? 'Sign in to save this location'
                  : isLocationSaved
                  ? 'Remove from saved locations'
                  : 'Save location to favorites'
              }
              aria-label={isLocationSaved ? 'Remove from favorites' : 'Save to favorites'}
              className="p-1 rounded-md transition-transform hover:scale-110 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
              style={{
                color: isLocationSaved ? '#f59e0b' : 'var(--text-tertiary)',
              }}
            >
              <Star
                className={`w-4 h-4 ${
                  isLocationSaved
                    ? 'fill-amber-400 text-amber-400'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              />
            </button>
          )}

          {/* Environmental indicator pill */}
          {hasEnvIndicators && (
            <EnvironmentalEventIndicator
              events={environmentalEvents || []}
              advisories={advisories}
              isOpen={isEnvPanelOpen}
              onToggle={onToggleEnvPanel}
            />
          )}
        </div>

        {/* Secondary hierarchy breadcrumb (Real data only) */}
        {secondaryBreadcrumb && (
          <p
            className="text-xs sm:text-sm font-normal mt-0.5 tracking-wide"
            style={{ color: 'var(--text-secondary)' }}
          >
            {secondaryBreadcrumb}
          </p>
        )}
      </div>

      {/* Period context badge */}
      <div className="self-start sm:self-auto flex items-center gap-2 flex-shrink-0">
        <span
          className="type-label px-2.5 py-1 rounded-md"
          style={{
            backgroundColor: 'var(--surface-secondary)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {comparison ? `${periodTitle} Comparison` : periodTitle}
        </span>
      </div>
    </div>
  );
};

import React from 'react';
import { CloudRain, Wind, Droplets, Activity, RotateCcw } from 'lucide-react';
import { OfficialAdvisory } from '../../types/advisory';
import { getWeatherIcon } from '../../utils/weatherIcons';

export interface WeatherTelemetryData {
  temperature: number;
  feels_like: number;
  condition: string;
  weather_code: number;
  humidity: number;
  wind_speed: number;
  precipitation: number;
  precipitation_probability?: number | null;
  rain_duration_hours?: number;
  peak_hour?: string | null;
}

export interface WeatherTelemetryProps {
  weather: WeatherTelemetryData;
  advisories?: OfficialAdvisory[];
  inspectedTime?: string | null;
  onResetToCurrent?: () => void;
}

// Extract AQI details from official advisories if present
function extractAqiFromAdvisories(advisories?: OfficialAdvisory[]): {
  value?: string;
  category: string;
  color: string;
} | null {
  if (!advisories || advisories.length === 0) return null;
  const aqiAdv = advisories.find(
    (a) => a.hazard_type === 'air_quality' || a.authority === 'CPCB'
  );
  if (!aqiAdv) return null;

  const level = (aqiAdv.official_level || '').toUpperCase();
  let category = 'Moderate';
  let color = '#eab308'; // yellow

  const match = level.match(/AQI\s*(\d+)/i);
  const value = match ? match[1] : undefined;

  if (level.includes('SEVERE')) {
    category = 'Severe';
    color = '#ef4444';
  } else if (level.includes('VERY POOR')) {
    category = 'Very Poor';
    color = '#f43f5e';
  } else if (level.includes('POOR')) {
    category = 'Poor';
    color = '#f97316';
  } else if (level.includes('MODERATE')) {
    category = 'Moderate';
    color = '#eab308';
  } else if (level.includes('SATISFACTORY')) {
    category = 'Satisfactory';
    color = '#10b981';
  } else if (level.includes('GOOD')) {
    category = 'Good';
    color = '#10b981';
  }

  return { value, category, color };
}

export const WeatherTelemetry: React.FC<WeatherTelemetryProps> = ({
  weather,
  advisories,
  inspectedTime,
  onResetToCurrent,
}) => {
  const prob = weather.precipitation_probability ?? 0;
  const peakText = weather.peak_hour
    ? `Peak ${weather.peak_hour}`
    : weather.precipitation > 0
    ? `${weather.precipitation} mm`
    : prob > 0
    ? `${prob}% chance`
    : 'No rain expected';

  const windDesc =
    weather.wind_speed >= 30
      ? 'Strong wind'
      : weather.wind_speed >= 15
      ? 'Moderate breeze'
      : 'Light breeze';

  const humidityDesc =
    weather.humidity >= 70
      ? 'Humid'
      : weather.humidity >= 40
      ? 'Comfortable'
      : 'Dry';

  const aqi = extractAqiFromAdvisories(advisories);

  const tempDiff = Math.round(weather.feels_like) - Math.round(weather.temperature);
  const feelsText =
    tempDiff === 0
      ? `Feels ${Math.round(weather.feels_like)}°C`
      : `Feels ${Math.round(weather.feels_like)}°C (${tempDiff > 0 ? `+${tempDiff}` : tempDiff}°)`;

  // Dynamic grid column class: 4 equal columns when no AQI (25% each), 5 when AQI exists (20% each)
  const gridLayoutClass = aqi
    ? 'grid-cols-2 sm:grid-cols-5'
    : 'grid-cols-2 sm:grid-cols-4';

  return (
    <section
      aria-label="Core weather telemetry"
      className="w-full rounded-2xl px-4 sm:px-6 py-4 border transition-colors"
      style={{
        backgroundColor: 'var(--surface-secondary)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Subtle Inspected Forecast Hour State Indicator */}
      {inspectedTime && (
        <div
          data-testid="forecast-scrubbing-indicator"
          className="flex items-center justify-between pb-2 mb-2.5 border-b"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div className="flex items-center gap-1.5 text-[11px] font-mono tracking-wider">
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ backgroundColor: 'var(--accent-primary)' }}
            />
            <span style={{ color: 'var(--accent-primary)' }} className="font-semibold uppercase">
              FORECAST · {inspectedTime}
            </span>
          </div>
          {onResetToCurrent && (
            <button
              type="button"
              onClick={onResetToCurrent}
              aria-label="Return telemetry to current observation"
              className="inline-flex items-center gap-1 text-[10px] font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-primary)] transition-colors"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              <span>Back to Current</span>
            </button>
          )}
        </div>
      )}

      <div
        data-testid="telemetry-grid"
        className={`grid ${gridLayoutClass} gap-y-3.5 sm:gap-y-0 sm:divide-x sm:divide-[var(--border-subtle)] w-full`}
      >
        {/* 1. Temperature & Feels Like */}
        <div className="flex items-center justify-start sm:justify-center min-w-0 w-full px-2 sm:px-3 lg:px-4 py-1 sm:py-0">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: 'var(--surface-primary)',
                color: 'var(--accent-primary)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              {getWeatherIcon(weather.weather_code, 'w-4 h-4')}
            </div>
            <div className="min-w-0">
              <div
                className="type-label text-[11px] uppercase tracking-wider truncate"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Temp
              </div>
              <div className="flex items-baseline gap-0.5">
                <span
                  className="font-tabular text-base sm:text-lg font-medium leading-tight"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {Math.round(weather.temperature)}°
                </span>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  C
                </span>
              </div>
              <div className="type-meta text-[11px] truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {feelsText}
              </div>
            </div>
          </div>
        </div>

        {/* 2. Precipitation (Probability + Peak / Quantity) */}
        <div className="flex items-center justify-start sm:justify-center min-w-0 w-full px-2 sm:px-3 lg:px-4 py-1 sm:py-0">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: 'rgba(56, 189, 248, 0.10)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.20)',
              }}
            >
              <CloudRain className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div
                className="type-label text-[11px] uppercase tracking-wider truncate"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Rain
              </div>
              <div
                className="font-tabular text-base sm:text-lg font-medium leading-tight"
                style={{ color: 'var(--text-primary)' }}
              >
                {prob}%
              </div>
              <div className="type-meta text-[11px] truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {peakText}
              </div>
            </div>
          </div>
        </div>

        {/* 3. Wind */}
        <div className="flex items-center justify-start sm:justify-center min-w-0 w-full px-2 sm:px-3 lg:px-4 py-1 sm:py-0">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: 'var(--surface-primary)',
                color: 'var(--accent-primary)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <Wind className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div
                className="type-label text-[11px] uppercase tracking-wider truncate"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Wind
              </div>
              <div
                className="font-tabular text-base sm:text-lg font-medium leading-tight truncate"
                style={{ color: 'var(--text-primary)' }}
              >
                {weather.wind_speed} <span className="text-xs font-normal">km/h</span>
              </div>
              <div className="type-meta text-[11px] truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {windDesc}
              </div>
            </div>
          </div>
        </div>

        {/* 4. Humidity */}
        <div className="flex items-center justify-start sm:justify-center min-w-0 w-full px-2 sm:px-3 lg:px-4 py-1 sm:py-0">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                backgroundColor: 'rgba(99, 102, 241, 0.10)',
                color: '#818cf8',
                border: '1px solid rgba(99, 102, 241, 0.20)',
              }}
            >
              <Droplets className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div
                className="type-label text-[11px] uppercase tracking-wider truncate"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Humidity
              </div>
              <div
                className="font-tabular text-base sm:text-lg font-medium leading-tight"
                style={{ color: 'var(--text-primary)' }}
              >
                {weather.humidity}%
              </div>
              <div className="type-meta text-[11px] truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                {humidityDesc}
              </div>
            </div>
          </div>
        </div>

        {/* 5. Air Quality (Rendered only when real data exists) */}
        {aqi && (
          <div className="flex items-center justify-start sm:justify-center min-w-0 w-full px-2 sm:px-3 lg:px-4 py-1 sm:py-0 col-span-2 sm:col-span-1 pt-2.5 sm:pt-0 border-t sm:border-t-0 border-[var(--border-subtle)]">
            <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{
                  backgroundColor: `${aqi.color}18`,
                  color: aqi.color,
                  border: `1px solid ${aqi.color}35`,
                }}
              >
                <Activity className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <div
                  className="type-label text-[11px] uppercase tracking-wider truncate"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  Air Quality
                </div>
                <div
                  className="font-tabular text-base sm:text-lg font-medium leading-tight truncate"
                  style={{ color: aqi.color }}
                >
                  {aqi.value ? `AQI ${aqi.value}` : aqi.category}
                </div>
                <div className="type-meta text-[11px] truncate mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {aqi.category}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

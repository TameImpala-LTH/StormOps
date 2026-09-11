import React, { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  CloudRain,
  Wind,
  Droplets,
  Thermometer,
  Info,
  Umbrella,
  MapPin,
  Star,
  Footprints,
  Car,
  Shirt,
  CheckCircle,
  XCircle,
  AlertCircle,
  AlertTriangle,
  HelpCircle,
} from 'lucide-react';
import { QueryResponse, HourlyForecast } from '../types/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { PRESET_LOCATIONS } from '../utils/locations';
import { WeatherMap } from './WeatherMap';
import { EnvironmentalEventIndicator } from './EnvironmentalEventIndicator';
import { EnvironmentalEventPanel } from './EnvironmentalEventPanel';
import { useAuth } from '../context/AuthContext';
import { FormattedMarkdown } from './FormattedMarkdown';


interface WeatherAnswerSurfaceProps {
  response: QueryResponse;
  onSelectPresetLocation?: (cityName: string) => void;
  onOpenAuthModal?: (mode: 'login' | 'register') => void;
}

// Map decision type to an icon
function getDecisionIcon(type: string): React.ReactNode {
  const icons: Record<string, React.ReactNode> = {
    umbrella: <Umbrella className="w-5 h-5" />,
    outdoor_activity: <Footprints className="w-5 h-5" />,
    travel: <Car className="w-5 h-5" />,
    clothing: <Shirt className="w-5 h-5" />,
  };
  return icons[type] ?? <Info className="w-5 h-5" />;
}

// Format backend period_label into clean human readable display
function formatPeriodLabel(rawLabel: string): string {
  const normalized = rawLabel.trim().toLowerCase();
  const map: Record<string, string> = {
    'today': 'Today',
    'tomorrow': 'Tomorrow',
    'today morning': 'Today · Morning',
    'tomorrow morning': 'Tomorrow · Morning',
    'today afternoon': 'Today · Afternoon',
    'tomorrow afternoon': 'Tomorrow · Afternoon',
    'today evening': 'Today · Evening',
    'tomorrow evening': 'Tomorrow · Evening',
    'tonight': 'Tonight',
    'right now': 'Right Now',
    'current': 'Current Weather',
  };
  if (map[normalized]) return map[normalized];
  return rawLabel.split(' ').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' · ');
}

// Map recommendation to style
function getRecommendationStyle(rec: string): { icon: React.ReactNode; bgColor: string; borderColor: string; textColor: string; badgeBg: string; badgeBorder: string } {
  switch (rec) {
    case 'recommended':
      return {
        icon: <CheckCircle className="w-4 h-4" />,
        bgColor: 'rgba(5,150,105,0.08)',
        borderColor: 'rgba(5,150,105,0.25)',
        textColor: '#10b981',
        badgeBg: 'rgba(5,150,105,0.12)',
        badgeBorder: 'rgba(5,150,105,0.30)',
      };
    case 'not_recommended':
      return {
        icon: <XCircle className="w-4 h-4" />,
        bgColor: 'rgba(220,38,38,0.08)',
        borderColor: 'rgba(220,38,38,0.25)',
        textColor: '#f87171',
        badgeBg: 'rgba(220,38,38,0.12)',
        badgeBorder: 'rgba(220,38,38,0.30)',
      };
    default:
      return {
        icon: <AlertCircle className="w-4 h-4" />,
        bgColor: 'rgba(217,119,6,0.08)',
        borderColor: 'rgba(217,119,6,0.25)',
        textColor: '#fbbf24',
        badgeBg: 'rgba(217,119,6,0.12)',
        badgeBorder: 'rgba(217,119,6,0.30)',
      };
  }
}

// Helper to format ISO or HH:MM string into 12-hour AM/PM label
function formatHour12(isoOrTimeString: string): { label12: string; hour: number; full12: string } {
  const timePart = isoOrTimeString.includes('T')
    ? isoOrTimeString.split('T')[1].slice(0, 5)
    : isoOrTimeString.slice(0, 5);
  const parts = timePart.split(':');
  const h = parseInt(parts[0], 10);
  const m = parts[1] ?? '00';

  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;

  return {
    label12: `${h12} ${ampm}`,
    hour: h,
    full12: `${h12}:${m} ${ampm}`,
  };
}

// Continuous Interactive Forecast Chart (Pure SVG + React State)
const InteractiveForecastChart: React.FC<{ items: HourlyForecast[]; periodTitle: string }> = ({ items, periodTitle }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!items || items.length === 0) return null;

  const svgWidth = 640;
  const svgHeight = 135;
  const paddingX = 36;
  const paddingTop = 36;
  const paddingBottom = 30;

  const temps = items.map((i) => Math.round(i.temperature));
  const minTemp = Math.min(...temps);
  const maxTemp = Math.max(...temps);
  const tempRange = Math.max(1, maxTemp - minTemp);

  const getX = (index: number) => {
    if (items.length <= 1) return svgWidth / 2;
    return paddingX + (index / (items.length - 1)) * (svgWidth - 2 * paddingX);
  };

  const getY = (temp: number) => {
    const chartHeight = svgHeight - paddingTop - paddingBottom;
    return paddingTop + chartHeight - ((temp - minTemp) / tempRange) * chartHeight;
  };

  const points = items.map((item, idx) => {
    const timeFormatted = formatHour12(item.time);
    return {
      x: getX(idx),
      y: getY(Math.round(item.temperature)),
      temp: Math.round(item.temperature),
      rawTime: item.time,
      timeLabel12: timeFormatted.label12,
      timeFull12: timeFormatted.full12,
      hourNumber: timeFormatted.hour,
      rainProb: item.precipitation_probability ?? 0,
      condition: item.condition,
      wind: item.wind_speed,
      weatherCode: item.weather_code,
    };
  });

  const activePoint = hoveredIdx !== null ? points[hoveredIdx] : null;

  // Build SVG path string for temperature line
  const linePath = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  return (
    <div className="space-y-3 pt-4" style={{ borderTop: '1px solid var(--border-muted)' }}>
      <div className="flex items-center justify-between text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
        <span className="flex items-center gap-1.5 font-medium">
          24-HOUR FORECAST VISUALIZATION
        </span>
        <span className="uppercase tracking-wider">{periodTitle}</span>
      </div>

      {/* Interactive Tooltip Bar */}
      <div
        className="min-h-[36px] px-4 py-2 rounded-xl flex items-center justify-between text-xs transition-all"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          border: '1px solid var(--border-muted)',
        }}
      >
        {activePoint ? (
          <div className="w-full flex items-center justify-between">
            <span className="font-mono font-semibold" style={{ color: 'var(--accent)' }}>
              {activePoint.timeFull12}
            </span>
            <span className="flex items-center gap-1 font-semibold" style={{ color: 'var(--text-primary)' }}>
              {activePoint.temp}°C
            </span>
            <span className="capitalize text-zinc-400 font-normal">
              {activePoint.condition}
            </span>
            <span className="font-mono text-sky-400 flex items-center gap-1">
              <CloudRain className="w-3.5 h-3.5 inline" /> {activePoint.rainProb}% rain
            </span>
            <span className="font-mono text-zinc-400 flex items-center gap-1 hidden sm:inline">
              <Wind className="w-3.5 h-3.5 inline" /> {activePoint.wind} km/h
            </span>
          </div>
        ) : (
          <span className="text-[11px] font-mono w-full text-center" style={{ color: 'var(--text-tertiary)' }}>
            Hover or tap any forecast point to inspect hourly details
          </span>
        )}
      </div>

      {/* SVG Chart Container */}
      <div className="w-full overflow-x-auto pb-1">
        <div className="min-w-[500px] sm:min-w-full">
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto overflow-visible">
            {/* Background Rain Probability Bars */}
            {points.map((p, idx) => {
              const barHeight = (p.rainProb / 100) * 35;
              const isHovered = hoveredIdx === idx;
              return (
                <rect
                  key={`bar-${idx}`}
                  x={p.x - 5}
                  y={svgHeight - paddingBottom - barHeight}
                  width={10}
                  height={barHeight}
                  rx={2}
                  fill={p.rainProb >= 50 ? '#38bdf8' : 'rgba(52,211,153,0.50)'}
                  opacity={isHovered ? 0.9 : 0.3}
                />
              );
            })}

            {/* Continuous Temperature Line */}
            <path
              d={linePath}
              fill="none"
              stroke="var(--accent)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Point Markers & Touch Targets */}
            {points.map((p, idx) => {
              const isHovered = hoveredIdx === idx;
              // Evenly spaced primary axis labels every 3 hours (12 AM, 3 AM, 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, 9 PM)
              const showAxisLabel = p.hourNumber % 3 === 0;

              return (
                <g key={`pt-${idx}`} className="cursor-pointer">
                  {/* Invisible enlarged hit area for touch/click */}
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={14}
                    fill="transparent"
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                    onClick={() => setHoveredIdx(idx)}
                  />

                  {/* Temperature dot */}
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={isHovered ? 6 : 3.5}
                    fill={isHovered ? 'var(--accent)' : 'var(--surface)'}
                    stroke="var(--accent)"
                    strokeWidth={2}
                    className="transition-all duration-150"
                  />

                  {/* Temperature text above point */}
                  {(isHovered || showAxisLabel) && (
                    <text
                      x={p.x}
                      y={p.y - 8}
                      textAnchor="middle"
                      className="text-[9px] font-mono font-semibold"
                      fill={isHovered ? 'var(--accent)' : 'var(--text-primary)'}
                    >
                      {p.temp}°
                    </text>
                  )}

                  {/* Hour text on X-axis */}
                  {showAxisLabel && (
                    <text
                      x={p.x}
                      y={svgHeight - 8}
                      textAnchor="middle"
                      className="text-[10px] font-mono font-medium"
                      fill={isHovered ? 'var(--accent)' : 'var(--text-secondary)'}
                    >
                      {p.timeLabel12}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
};


export const WeatherAnswerSurface: React.FC<WeatherAnswerSurfaceProps> = ({
  response,
  onSelectPresetLocation,
  onOpenAuthModal,
}) => {
  const shouldReduceMotion = useReducedMotion();

  // If response requires location clarification, render clean clarification view
  if (response.needs_clarification) {
    return (
      <div
        className="w-full rounded-3xl p-8 shadow-xl space-y-6 text-center"
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        <div className="flex justify-center text-amber-400">
          <HelpCircle className="w-10 h-10" />
        </div>
        <div className="space-y-1">
          <h3 className="text-xl font-light tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Location Context Needed
          </h3>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            {response.summary}
          </p>
        </div>

        {/* Quick Location Pills */}
        {onSelectPresetLocation && (
          <div className="pt-2">
            <span className="text-xs font-mono block mb-3" style={{ color: 'var(--text-muted)' }}>
              Select a location to check weather:
            </span>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {PRESET_LOCATIONS.map((loc) => (
                <button
                  key={loc.name}
                  type="button"
                  onClick={() => onSelectPresetLocation(loc.name)}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium border transition-colors cursor-pointer"
                  style={{
                    backgroundColor: 'var(--surface-elevated)',
                    borderColor: 'var(--border-muted)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <MapPin className="w-3 h-3 inline mr-1 text-emerald-400" />
                  {loc.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  const [isEnvPanelOpen, setIsEnvPanelOpen] = useState(false);
  const { isAuthenticated, savedLocations, saveLocation, removeSavedLocation } = useAuth();

  const {
    location,
    period_weather,
    period_forecast,
    forecast,
    decision,
    alerts,
    environmental_events,
    comparison,
    summary,
    current,
  } = response;

  const isLocationSaved = Boolean(
    location &&
    savedLocations.some(
      (loc) =>
        loc.name.toLowerCase() === location.name.toLowerCase() ||
        (Math.abs(loc.latitude - location.latitude) < 0.05 &&
         Math.abs(loc.longitude - location.longitude) < 0.05)
    )
  );

  const matchedSavedLocation = location
    ? savedLocations.find(
        (loc) =>
          loc.name.toLowerCase() === location.name.toLowerCase() ||
          (Math.abs(loc.latitude - location.latitude) < 0.05 &&
           Math.abs(loc.longitude - location.longitude) < 0.05)
      )
    : null;

  const handleToggleSaveLocation = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!location) return;
    if (!isAuthenticated) {
      if (onOpenAuthModal) {
        onOpenAuthModal('login');
      }
      return;
    }
    try {
      if (matchedSavedLocation) {
        await removeSavedLocation(matchedSavedLocation.id);
      } else {
        await saveLocation(location.name, location.latitude, location.longitude, location.country);
      }
    } catch {
      // Handled in context
    }
  };


  const weather = period_weather ?? {
    temperature: current?.temperature ?? 0,
    feels_like: current?.feels_like ?? 0,
    condition: current?.condition ?? 'Unknown',
    weather_code: current?.weather_code ?? 0,
    humidity: current?.humidity ?? 0,
    wind_speed: current?.wind_speed ?? 0,
    precipitation: current?.precipitation ?? 0,
    precipitation_probability: current?.precipitation_probability ?? 0,
    period_label: 'current',
  };

  const locationName = location
    ? `${location.name}${location.admin1 ? ', ' + location.admin1 : ''}${location.country ? ', ' + location.country : ''}`
    : 'Weather Forecast';

  const periodTitle = formatPeriodLabel(weather.period_label || 'current');

  // Render Severe Weather Alerts / Risk Advisories
  const renderAlertBanners = () => {
    if (!alerts || alerts.length === 0) return null;

    return (
      <div className="space-y-3">
        {alerts.map((alert) => {
          let style = {
            bgColor: 'rgba(56,189,248,0.08)',
            borderColor: 'rgba(56,189,248,0.25)',
            textColor: '#38bdf8',
            badgeBg: 'rgba(56,189,248,0.14)',
            icon: <Info className="w-4 h-4" />,
          };

          if (alert.severity === 'warning') {
            style = {
              bgColor: 'rgba(225,29,72,0.08)',
              borderColor: 'rgba(225,29,72,0.30)',
              textColor: '#f43f5e',
              badgeBg: 'rgba(225,29,72,0.15)',
              icon: <AlertTriangle className="w-4 h-4 text-rose-500" />,
            };
          } else if (alert.severity === 'watch') {
            style = {
              bgColor: 'rgba(217,119,6,0.08)',
              borderColor: 'rgba(217,119,6,0.30)',
              textColor: '#fbbf24',
              badgeBg: 'rgba(217,119,6,0.15)',
              icon: <AlertCircle className="w-4 h-4 text-amber-400" />,
            };
          }

          return (
            <div
              key={alert.id}
              className="p-4 rounded-2xl border space-y-2"
              style={{
                backgroundColor: style.bgColor,
                borderColor: style.borderColor,
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 rounded-lg" style={{ backgroundColor: style.badgeBg, color: style.textColor }}>
                    {style.icon}
                  </div>
                  <h4 className="text-sm font-semibold tracking-tight" style={{ color: style.textColor }}>
                    {alert.title}
                  </h4>
                </div>
                <span
                  className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border"
                  style={{
                    backgroundColor: style.badgeBg,
                    borderColor: style.borderColor,
                    color: style.textColor,
                  }}
                >
                  {alert.severity}
                </span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                {alert.summary}
              </p>

              {/* Triggering Factors */}
              {alert.factors && alert.factors.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {alert.factors.map((f, fIdx) => (
                    <span
                      key={fIdx}
                      className="text-[10px] font-mono px-2 py-0.5 rounded"
                      style={{
                        backgroundColor: 'var(--surface-elevated)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-muted)',
                      }}
                    >
                      {f.metric.replace(/_/g, ' ')}: {f.value}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // Render Location Comparison Surface (Section #2.5)
  const renderComparisonSurface = () => {
    if (!comparison) return null;
    const compDec = comparison.decision;
    const isWinnerA = compDec.recommended_key === 'a';
    const isWinnerB = compDec.recommended_key === 'b';
    const isSimilar = compDec.recommended_key === 'equal';

    return (
      <div className="space-y-6 pt-2">
        {/* Comparison Recommendation Hero Box */}
        <div
          className="p-5 rounded-3xl border space-y-4 shadow-sm"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: 'var(--border)',
          }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b" style={{ borderColor: 'var(--border-muted)' }}>
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-semibold block">
                WeatherGPT Location Comparison ({comparison.comparison_goal.replace(/_/g, ' ')})
              </span>
              <h3 className="text-xl sm:text-2xl font-light tracking-tight flex items-center gap-2 mt-0.5" style={{ color: 'var(--text-primary)' }}>
                {comparison.location_a.name} <span className="text-xs font-mono text-zinc-500">VS</span> {comparison.location_b.name}
              </h3>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <span
                className="px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider border"
                style={{
                  backgroundColor: isSimilar ? 'rgba(217,119,6,0.12)' : 'rgba(16,185,129,0.12)',
                  borderColor: isSimilar ? 'rgba(217,119,6,0.30)' : 'rgba(16,185,129,0.30)',
                  color: isSimilar ? '#fbbf24' : '#34d399',
                }}
              >
                {compDec.recommended_location}
              </span>
              <span
                className="text-[10px] font-mono uppercase px-2 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--surface)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-muted)',
                }}
              >
                {compDec.confidence} confidence
              </span>
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              {compDec.summary}
            </p>
            <p className="text-xs text-zinc-400 leading-relaxed font-mono">
              Reason: {compDec.winner_reason}
            </p>
          </div>
        </div>

        {/* Side-by-Side Location Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Location A Card */}
          <div
            className={`p-5 rounded-2xl border space-y-4 relative transition-all ${isWinnerA ? 'ring-2 ring-emerald-500/50' : ''}`}
            style={{
              backgroundColor: 'var(--surface-elevated)',
              borderColor: isWinnerA ? 'rgba(16,185,129,0.4)' : 'var(--border-muted)',
            }}
          >
            {isWinnerA && (
              <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                Recommended Winner
              </div>
            )}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                <span>LOCATION A</span>
              </div>
              <h4 className="text-xl font-medium" style={{ color: 'var(--text-primary)' }}>
                {comparison.location_a.name}, {comparison.location_a.country}
              </h4>
            </div>

            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-extralight" style={{ color: 'var(--text-primary)' }}>
                {Math.round(comparison.period_weather_a.temperature)}°C
              </span>
              <div className="text-xs">
                <span className="capitalize block font-medium" style={{ color: 'var(--text-primary)' }}>
                  {comparison.period_weather_a.condition}
                </span>
                <span className="font-mono text-zinc-400 block">
                  Feels like {Math.round(comparison.period_weather_a.feels_like)}°C
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t" style={{ borderColor: 'var(--border-muted)' }}>
              <div>
                <span className="text-zinc-400 block text-[10px]">RAIN CHANCE</span>
                <span className="font-semibold text-sky-400">{comparison.period_weather_a.precipitation_probability}%</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">PRECIPITATION</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{comparison.period_weather_a.precipitation} mm</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">WIND SPEED</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{comparison.period_weather_a.wind_speed} km/h</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">HUMIDITY</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{comparison.period_weather_a.humidity}%</span>
              </div>
            </div>

            {comparison.alerts_a && comparison.alerts_a.length > 0 && (
              <div className="pt-2">
                {comparison.alerts_a.map((a) => (
                  <div key={a.id} className="p-2 rounded-xl text-xs bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>{a.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Location B Card */}
          <div
            className={`p-5 rounded-2xl border space-y-4 relative transition-all ${isWinnerB ? 'ring-2 ring-emerald-500/50' : ''}`}
            style={{
              backgroundColor: 'var(--surface-elevated)',
              borderColor: isWinnerB ? 'rgba(16,185,129,0.4)' : 'var(--border-muted)',
            }}
          >
            {isWinnerB && (
              <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                Recommended Winner
              </div>
            )}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                <MapPin className="w-3.5 h-3.5 text-sky-400" />
                <span>LOCATION B</span>
              </div>
              <h4 className="text-xl font-medium" style={{ color: 'var(--text-primary)' }}>
                {comparison.location_b.name}, {comparison.location_b.country}
              </h4>
            </div>

            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-extralight" style={{ color: 'var(--text-primary)' }}>
                {Math.round(comparison.period_weather_b.temperature)}°C
              </span>
              <div className="text-xs">
                <span className="capitalize block font-medium" style={{ color: 'var(--text-primary)' }}>
                  {comparison.period_weather_b.condition}
                </span>
                <span className="font-mono text-zinc-400 block">
                  Feels like {Math.round(comparison.period_weather_b.feels_like)}°C
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t" style={{ borderColor: 'var(--border-muted)' }}>
              <div>
                <span className="text-zinc-400 block text-[10px]">RAIN CHANCE</span>
                <span className="font-semibold text-sky-400">{comparison.period_weather_b.precipitation_probability}%</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">PRECIPITATION</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{comparison.period_weather_b.precipitation} mm</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">WIND SPEED</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{comparison.period_weather_b.wind_speed} km/h</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px]">HUMIDITY</span>
                <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{comparison.period_weather_b.humidity}%</span>
              </div>
            </div>

            {comparison.alerts_b && comparison.alerts_b.length > 0 && (
              <div className="pt-2">
                {comparison.alerts_b.map((a) => (
                  <div key={a.id} className="p-2 rounded-xl text-xs bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>{a.title}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Metric Comparison Table */}
        {compDec.factors && compDec.factors.length > 0 && (
          <div className="p-4 rounded-2xl border space-y-3" style={{ backgroundColor: 'var(--surface-elevated)', borderColor: 'var(--border-muted)' }}>
            <div className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              Metric Comparison Factors
            </div>
            <div className="space-y-2">
              {compDec.factors.map((f, idx) => (
                <div key={idx} className="p-2.5 rounded-xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2" style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border-muted)' }}>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="capitalize font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {f.metric.replace(/_/g, ' ')}
                    </span>
                    <span className="text-zinc-400">
                      ({f.value_a} vs {f.value_b})
                    </span>
                  </div>
                  <span className="text-xs text-zinc-300 font-medium">
                    {f.impact_note}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // Decision Banner
  const renderDecisionBanner = () => {
    if (!decision) return null;
    const style = getRecommendationStyle(decision.recommendation);
    const BadgeIcon = style.icon;

    return (
      <div
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-2xl p-4"
        style={{
          backgroundColor: style.bgColor,
          border: `1px solid ${style.borderColor}`,
        }}
      >
        <div className="flex items-start space-x-3">
          <div
            className="p-2 rounded-xl mt-0.5 flex-shrink-0"
            style={{ color: style.textColor, backgroundColor: style.badgeBg }}
          >
            {getDecisionIcon(decision.type)}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span
                className="text-xs uppercase font-mono tracking-wider font-semibold"
                style={{ color: style.textColor }}
              >
                {decision.type.replace(/_/g, ' ')} Decision
              </span>
              <span
                className="text-[10px] uppercase font-mono px-2 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--surface)',
                  color: 'var(--text-secondary)',
                }}
              >
                {decision.confidence} confidence
              </span>
            </div>
            <p className="text-sm font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>
              {decision.summary}
            </p>
          </div>
        </div>
        <div
          className="inline-flex items-center space-x-1.5 self-start sm:self-auto px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border"
          style={{ color: style.textColor, borderColor: style.badgeBorder, backgroundColor: style.badgeBg }}
        >
          <span className="flex-shrink-0">{BadgeIcon}</span>
          <span>{decision.recommendation.replace(/_/g, ' ')}</span>
        </div>
      </div>
    );
  };

  // Compact Rain Status Badge for non-decision queries
  const renderRainStatusBadge = () => {
    if (decision || comparison) return null;
    const prob = weather.precipitation_probability;
    const duration = weather.rain_duration_hours ?? 0;
    let label = 'LOW CHANCE OF RAIN';
    let colorStyle = { color: '#10b981', backgroundColor: 'rgba(5,150,105,0.08)', borderColor: 'rgba(5,150,105,0.25)' };

    if (prob >= 70) {
      if (duration > 0 && duration <= 2) {
        label = 'ISOLATED SHOWER POSSIBLE';
        colorStyle = { color: '#fbbf24', backgroundColor: 'rgba(217,119,6,0.08)', borderColor: 'rgba(217,119,6,0.25)' };
      } else {
        label = 'RAIN LIKELY';
        colorStyle = { color: '#f87171', backgroundColor: 'rgba(220,38,38,0.08)', borderColor: 'rgba(220,38,38,0.25)' };
      }
    } else if (prob >= 40) {
      if (duration > 0 && duration <= 2) {
        label = 'BRIEF SHOWER CHANCE';
      } else {
        label = 'MODERATE RAIN CHANCE';
      }
      colorStyle = { color: '#fbbf24', backgroundColor: 'rgba(217,119,6,0.08)', borderColor: 'rgba(217,119,6,0.25)' };
    }

    return (
      <div
        className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-semibold tracking-wider font-mono"
        style={colorStyle}
      >
        <CloudRain className="w-4 h-4" />
        <span>{label} — Peak {prob}%</span>
      </div>
    );
  };

  // Forecast items for visualization
  const forecastItems = period_forecast && period_forecast.length > 0 ? period_forecast : (forecast?.slice(0, 24) ?? []);

  // Framer Motion Animation Variants for Progressive Reveal
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.07,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 12 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.35 },
    },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="w-full rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6"
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        color: 'var(--text-primary)',
      }}
    >
      {/* 1. Location & Period Header */}
      <motion.div
        variants={itemVariants}
        className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 gap-2"
        style={{ borderBottom: '1px solid var(--border-muted)' }}
      >
        <div>
          <h2
            className="text-2xl sm:text-3xl font-light tracking-tight flex items-center gap-2 flex-wrap"
            style={{ color: 'var(--text-primary)' }}
          >
            <MapPin className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
            <span>{comparison ? `${comparison.location_a.name} vs ${comparison.location_b.name}` : locationName}</span>
            {location && !comparison && (
              <button
                type="button"
                onClick={handleToggleSaveLocation}
                title={
                  !isAuthenticated
                    ? 'Sign in to save this location'
                    : isLocationSaved
                    ? 'Remove from saved locations'
                    : 'Save location to favorites'
                }
                className="p-1 rounded-lg transition-transform hover:scale-110 cursor-pointer ml-0.5"
                style={{
                  color: isLocationSaved ? '#f59e0b' : 'var(--text-muted)',
                }}
              >
                <Star
                  className={`w-4 h-4 sm:w-5 sm:h-5 ${
                    isLocationSaved
                      ? 'fill-amber-400 text-amber-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                />
              </button>
            )}
            {environmental_events && environmental_events.length > 0 && (
              <EnvironmentalEventIndicator
                events={environmental_events}
                isOpen={isEnvPanelOpen}
                onToggle={() => setIsEnvPanelOpen((prev) => !prev)}
              />
            )}
          </h2>
          <span
            className="text-xs font-mono tracking-wider mt-0.5 block"
            style={{ color: 'var(--text-secondary)' }}
          >
            {comparison ? `${periodTitle} Location Comparison` : `${periodTitle} Weather Answer`}
          </span>
        </div>
        <div className="self-start sm:self-auto">
          {renderRainStatusBadge()}
        </div>
      </motion.div>

      {/* Environmental Event Outlook Panel (Toggled by Bell Indicator) */}
      {environmental_events && environmental_events.length > 0 && (
        <EnvironmentalEventPanel
          events={environmental_events}
          isOpen={isEnvPanelOpen}
          onClose={() => setIsEnvPanelOpen(false)}
        />
      )}


      {/* 2. WeatherGPT Answer (Placed IMMEDIATELY after Location & Period Header) */}
      <motion.div
        variants={itemVariants}
        className="p-4.5 rounded-2xl space-y-2 border shadow-sm"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border)',
        }}
      >
        <div
          className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider font-semibold"
          style={{ color: 'var(--accent)' }}
        >
          <Info className="w-4 h-4" />
          <span>WeatherGPT Interpretation</span>
        </div>
        <div
          className="text-base font-normal leading-relaxed"
          style={{ color: 'var(--text-primary)' }}
        >
          <FormattedMarkdown content={summary} />
        </div>
      </motion.div>

      {/* 3. Severe Weather Alerts & Advisories (when applicable) */}
      {alerts && alerts.length > 0 && (
        <motion.div variants={itemVariants}>
          {renderAlertBanners()}
        </motion.div>
      )}

      {/* 4. Hero Weather / Comparison Surface */}
      {comparison ? (
        <motion.div variants={itemVariants}>
          {renderComparisonSurface()}
        </motion.div>
      ) : (
        <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div className="flex items-center space-x-6">
            <div
              className="p-4 rounded-2xl flex-shrink-0 weather-icon-breathe"
              style={{
                backgroundColor: 'var(--surface-elevated)',
                border: '1px solid var(--border)',
                color: 'var(--accent)',
              }}
            >
              {getWeatherIcon(weather.weather_code)}
            </div>
            <div>
              <div className="flex items-baseline space-x-2">
                <span
                  className="text-5xl font-extralight"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {Math.round(weather.temperature)}°
                </span>
                <span
                  className="text-sm font-normal"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  C
                </span>
              </div>
              <p
                className="text-lg font-normal capitalize mt-0.5"
                style={{ color: 'var(--text-primary)' }}
              >
                {weather.condition}
              </p>
              <p
                className="text-xs font-mono mt-1"
                style={{ color: 'var(--text-secondary)' }}
              >
                Feels like {Math.round(weather.feels_like)}°C
              </p>
            </div>
          </div>

          {/* Embedded Decision Banner */}
          {renderDecisionBanner()}
        </motion.div>
      )}

      {/* 5. Key Metrics Grid (Single Location only) */}
      {!comparison && (
        <motion.div variants={itemVariants} className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          {/* Peak Rain Chance */}
          <div
            className="p-3.5 rounded-2xl flex items-center space-x-3"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-muted)',
            }}
          >
            <div
              className="p-2 rounded-xl flex-shrink-0 text-sky-400"
              style={{ backgroundColor: 'var(--metric-icon-bg)' }}
            >
              <CloudRain className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                Peak Rain Chance
              </div>
              <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {weather.precipitation_probability}%
              </div>
            </div>
          </div>

          {/* Precipitation */}
          <div
            className="p-3.5 rounded-2xl flex items-center space-x-3"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-muted)',
            }}
          >
            <div
              className="p-2 rounded-xl flex-shrink-0 text-indigo-400"
              style={{ backgroundColor: 'var(--metric-icon-bg)' }}
            >
              <Droplets className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                Precipitation
              </div>
              <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {weather.precipitation} mm
              </div>
            </div>
          </div>

          {/* Wind Speed */}
          <div
            className="p-3.5 rounded-2xl flex items-center space-x-3"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-muted)',
            }}
          >
            <div
              className="p-2 rounded-xl flex-shrink-0"
              style={{ backgroundColor: 'var(--metric-icon-bg)', color: 'var(--accent)' }}
            >
              <Wind className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                Wind Speed
              </div>
              <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {weather.wind_speed} km/h
              </div>
            </div>
          </div>

          {/* Humidity */}
          <div
            className="p-3.5 rounded-2xl flex items-center space-x-3"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-muted)',
            }}
          >
            <div
              className="p-2 rounded-xl flex-shrink-0 text-teal-400"
              style={{ backgroundColor: 'var(--metric-icon-bg)' }}
            >
              <Thermometer className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                Humidity
              </div>
              <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {weather.humidity}%
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* 6. Target Period Forecast Visualization */}
      {!comparison && (
        <motion.div variants={itemVariants}>
          <InteractiveForecastChart items={forecastItems} periodTitle={periodTitle} />
        </motion.div>
      )}

      {/* 7. Interactive Weather Map */}
      {location && (
        <motion.div variants={itemVariants}>
          <WeatherMap
            location={comparison ? comparison.location_a : location}
            weather={comparison ? comparison.period_weather_a : weather}
            locationB={comparison?.location_b}
            weatherB={comparison?.period_weather_b}
            periodLabel={periodTitle}
            onCheckWeatherAtCoords={(lat, lng) => {
              if (onSelectPresetLocation) {
                onSelectPresetLocation(`${lat}, ${lng}`);
              }
            }}
          />
        </motion.div>
      )}
    </motion.div>
  );
};


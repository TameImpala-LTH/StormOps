import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Info,
  Umbrella,
  MapPin,
  Footprints,
  Car,
  Shirt,
  CheckCircle,
  XCircle,
  AlertCircle,
  AlertTriangle,
} from 'lucide-react';
import { QueryResponse, HourlyForecast } from '../types/weather';
import { OfficialAdvisory } from '../types/advisory';
import { fetchOfficialAdvisories } from '../services/weather';
import { PRESET_LOCATIONS } from '../utils/locations';
import { OfficialAdvisoryBanner } from './advisory/OfficialAdvisoryBanner';
import { OfficialAdvisorySection } from './advisory/OfficialAdvisorySection';
import { WeatherLocationIdentity } from './briefing/WeatherLocationIdentity';
import { WeatherGPTHero } from './briefing/WeatherGPTHero';
import { WeatherTelemetry } from './briefing/WeatherTelemetry';
import { useAuth } from '../context/AuthContext';

const WeatherMap = React.lazy(() =>
  import('./WeatherMap').then((m) => ({ default: m.WeatherMap }))
);
const InteractiveForecastChart = React.lazy(() =>
  import('./InteractiveForecastChart').then((m) => ({ default: m.InteractiveForecastChart }))
);
const ComparisonSurface = React.lazy(() =>
  import('./ComparisonSurface').then((m) => ({ default: m.ComparisonSurface }))
);
const EnvironmentalEventPanel = React.lazy(() =>
  import('./EnvironmentalEventPanel').then((m) => ({ default: m.EnvironmentalEventPanel }))
);

interface WeatherAnswerSurfaceProps {
  response: QueryResponse;
  onSelectPresetLocation?: (cityName: string) => void;
  onOpenAuthModal?: (mode: 'login' | 'register') => void;
}

// Map decision type to an icon
export function getDecisionIcon(type: string): React.ReactNode {
  const icons: Record<string, React.ReactNode> = {
    umbrella: <Umbrella className="w-5 h-5" />,
    outdoor_activity: <Footprints className="w-5 h-5" />,
    travel: <Car className="w-5 h-5" />,
    clothing: <Shirt className="w-5 h-5" />,
  };
  return icons[type] ?? <Info className="w-5 h-5" />;
}

// Format backend period_label into clean human readable display
export function formatPeriodLabel(rawLabel: string): string {
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
export function getRecommendationStyle(rec: string): {
  icon: React.ReactNode;
  bgColor: string;
  borderColor: string;
  textColor: string;
  badgeBg: string;
  badgeBorder: string;
} {
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

// Extract a concise, prominent key insight (first clean sentence) from AI summary
export function extractKeyInsight(summaryText: string): string {
  if (!summaryText) return '';
  const clean = summaryText.trim().replace(/^#+\s+/, '').replace(/^\*+\s+/, '');
  const match = clean.match(/^([^.!?\n]+[.!?])/);
  if (match && match[1] && match[1].trim().length >= 8) {
    return match[1].trim();
  }
  const firstLine = clean.split('\n')[0].trim();
  if (firstLine.length <= 180) return firstLine;
  return firstLine.slice(0, 177) + '...';
}

// Generate an authoritative, deterministic 1-sentence Key Insight answering "What is the one thing I should know?"
export function generateDeterministicKeyInsight(
  weather: {
    temperature: number;
    condition: string;
    weather_code: number;
    precipitation_probability?: number | null;
    rain_duration_hours?: number;
    peak_hour?: string | null;
  } | null,
  periodLabel: string,
  decision?: { summary: string; recommendation?: string } | null,
  rawSummary?: string
): string {
  if (decision?.summary) {
    return decision.summary;
  }
  if (!weather) {
    return rawSummary ? extractKeyInsight(rawSummary) : 'Weather forecast data is currently unavailable for this period.';
  }

  const p = weather.precipitation_probability ?? 0;
  const temp = Math.round(weather.temperature);
  const cond = weather.condition.toLowerCase();

  if (p >= 70) {
    if (weather.rain_duration_hours && weather.rain_duration_hours <= 2) {
      return `Isolated showers are likely during ${periodLabel.toLowerCase()} with a peak ${p}% precipitation chance.`;
    }
    return `Sustained rain is expected during ${periodLabel.toLowerCase()} (${temp}°C) with a ${p}% peak probability.`;
  }
  if (cond.includes('thunder') || weather.weather_code >= 95) {
    return `Thunderstorm conditions expected during ${periodLabel.toLowerCase()} with gusty winds and possible heavy spells.`;
  }
  if (p >= 40) {
    return `Passing or brief showers are possible during ${periodLabel.toLowerCase()} with a ${p}% rain chance.`;
  }
  if (temp >= 38) {
    return `Intense heat anticipated during ${periodLabel.toLowerCase()}, peaking around ${temp}°C.`;
  }
  if (rawSummary) {
    const extracted = extractKeyInsight(rawSummary);
    if (extracted && extracted.length >= 12) return extracted;
  }
  return `Predominantly ${cond} conditions with temperatures around ${temp}°C during ${periodLabel.toLowerCase()}.`;
}

// Ensure the Detailed Interpretation does not repeat the exact headline Key Insight
export function getDeduplicatedSummary(summaryText: string, keyInsight: string): string {
  if (!summaryText || !keyInsight) return summaryText;
  const cleanSummary = summaryText.trim();
  const cleanInsight = keyInsight.trim();
  if (cleanSummary.startsWith(cleanInsight)) {
    const rest = cleanSummary.slice(cleanInsight.length).trim();
    return rest || cleanSummary;
  }
  return cleanSummary;
}

// Weather condition accent styling (distinct from official advisory severity colors)
export function getWeatherConditionAccent(
  weatherCode: number,
  temp: number,
  theme: string,
  darkVariant: string,
  baseAccent: string
): {
  accentColor: string;
  supportingColor: string;
  badgeBg: string;
  badgeBorder: string;
  glowStyle: string;
} {
  // 1. Thunderstorm (codes 95-99) — electric violet / purple
  if (weatherCode >= 95 && weatherCode <= 99) {
    return {
      accentColor: '#a855f7',
      supportingColor: '#c084fc',
      badgeBg: 'rgba(168, 85, 247, 0.12)',
      badgeBorder: 'rgba(168, 85, 247, 0.28)',
      glowStyle: '0 4px 20px -2px rgba(168, 85, 247, 0.18)',
    };
  }

  // 2. Rain / Showers (codes 51-82, 85-86) — cyan / cool blue
  if ((weatherCode >= 51 && weatherCode <= 82) || (weatherCode >= 85 && weatherCode <= 86)) {
    const isVandal = theme === 'dark' && darkVariant === 'vandal';
    return {
      accentColor: isVandal ? '#38bdf8' : '#38bdf8',
      supportingColor: isVandal ? '#fb923c' : '#7dd3fc',
      badgeBg: 'rgba(56, 189, 248, 0.12)',
      badgeBorder: 'rgba(56, 189, 248, 0.28)',
      glowStyle: isVandal
        ? '0 4px 20px -2px rgba(255, 42, 85, 0.14)'
        : '0 4px 20px -2px rgba(56, 189, 248, 0.14)',
    };
  }

  // 3. Extreme Heat (temp >= 35°C) — amber / warm orange
  if (temp >= 35) {
    return {
      accentColor: '#f97316',
      supportingColor: '#fbbf24',
      badgeBg: 'rgba(249, 115, 22, 0.12)',
      badgeBorder: 'rgba(249, 115, 22, 0.28)',
      glowStyle: '0 4px 20px -2px rgba(249, 115, 22, 0.16)',
    };
  }

  // 4. Cold / Freezing (temp <= 5°C) — cool icy blue
  if (temp <= 5) {
    return {
      accentColor: '#60a5fa',
      supportingColor: '#93c5fd',
      badgeBg: 'rgba(96, 165, 250, 0.12)',
      badgeBorder: 'rgba(96, 165, 250, 0.28)',
      glowStyle: '0 4px 20px -2px rgba(96, 165, 250, 0.14)',
    };
  }

  // 5. Default / Clear / Mild — theme-driven accent
  const isVandal = theme === 'dark' && darkVariant === 'vandal';
  const isNight = theme === 'night';
  return {
    accentColor: baseAccent,
    supportingColor: isVandal ? '#fb923c' : isNight ? '#a78bfa' : baseAccent,
    badgeBg: 'var(--accent-muted)',
    badgeBorder: 'var(--accent-border)',
    glowStyle: isVandal
      ? '0 4px 20px -2px rgba(255, 42, 85, 0.14)'
      : isNight
      ? '0 4px 20px -2px rgba(168, 85, 247, 0.14)'
      : '0 4px 18px -2px rgba(56, 189, 248, 0.12)',
  };
}

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
          backgroundColor: 'var(--surface-primary)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-primary)',
        }}
      >
        <div className="flex justify-center text-amber-400">
          <AlertCircle className="w-10 h-10" />
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
            <span className="text-xs font-mono block mb-3" style={{ color: 'var(--text-tertiary)' }}>
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
                    backgroundColor: 'var(--surface-secondary)',
                    borderColor: 'var(--border-subtle)',
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
    official_advisories,
  } = response;

  const [advisories, setAdvisories] = useState<OfficialAdvisory[]>(
    official_advisories || []
  );

  // Fetch official advisories for location context when not provided directly in response
  useEffect(() => {
    if (official_advisories !== undefined && official_advisories !== null) {
      setAdvisories(official_advisories);
      return;
    }
    if (!location) {
      setAdvisories([]);
      return;
    }

    let isMounted = true;
    fetchOfficialAdvisories({
      latitude: location.latitude,
      longitude: location.longitude,
      district: location.name,
      state: location.admin1 ?? undefined,
    }).then((fetched) => {
      if (isMounted) {
        setAdvisories(fetched);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [location?.latitude, location?.longitude, location?.name, location?.admin1, official_advisories]);

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

  const isForecastRequested = Boolean(
    response.period?.is_forecast ||
    (response.query?.date_context && response.query.date_context !== 'today')
  );

  const isPeriodUnavailable = isForecastRequested && !period_weather;

  const rawPeriodLabel = period_weather?.period_label || response.period?.label || response.query?.date_context || 'current';
  const periodTitle = formatPeriodLabel(rawPeriodLabel);

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

  // UI-06: Interactive inspection hour state driven by forecast scrubber
  const [inspectedHour, setInspectedHour] = useState<HourlyForecast | null>(null);

  const handleInspectHour = useCallback((hour: HourlyForecast | null) => {
    setInspectedHour(hour);
  }, []);

  const handleResetInspection = useCallback(() => {
    setInspectedHour(null);
  }, []);

  const activeTelemetry = useMemo(() => {
    if (!inspectedHour) return weather;
    return {
      temperature: inspectedHour.temperature,
      feels_like: inspectedHour.feels_like ?? inspectedHour.temperature,
      condition: inspectedHour.condition,
      weather_code: inspectedHour.weather_code,
      humidity: weather.humidity,
      wind_speed: inspectedHour.wind_speed,
      precipitation: inspectedHour.precipitation,
      precipitation_probability: inspectedHour.precipitation_probability,
      peak_hour: weather.peak_hour,
      rain_duration_hours: weather.rain_duration_hours,
    };
  }, [inspectedHour, weather]);

  const inspectedTimeStr = useMemo(() => {
    if (!inspectedHour) return null;
    const t = inspectedHour.time;
    const timePart = t.includes('T') ? t.split('T')[1].slice(0, 5) : t.slice(0, 5);
    const [hStr, mStr] = timePart.split(':');
    const h = parseInt(hStr, 10);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 === 0 ? 12 : h % 12;
    return `${h12}:${mStr ?? '00'} ${ampm}`;
  }, [inspectedHour]);

  const keyInsight = response.key_insight || generateDeterministicKeyInsight(
    isPeriodUnavailable ? null : weather,
    periodTitle,
    decision,
    summary
  );
  const deduplicatedSummary = getDeduplicatedSummary(summary, keyInsight);

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
                        backgroundColor: 'var(--surface-secondary)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-subtle)',
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

  // Forecast items for visualization
  const forecastItems = period_forecast && period_forecast.length > 0 ? period_forecast : (forecast?.slice(0, 24) ?? []);

  // Framer Motion Animation Variants for Progressive Reveal
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : 0.05,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 8 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.25 },
    },
  };

  return (
    <motion.article
      aria-label="Weather intelligence briefing surface"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="w-full rounded-3xl p-5 sm:p-7 shadow-xl space-y-5"
      style={{
        backgroundColor: 'var(--surface-primary)',
        border: '1px solid var(--border-default)',
        color: 'var(--text-primary)',
      }}
    >
      {/* 1. LOCATION IDENTITY (Restrained identity: Locality · Admin1 · Country) */}
      <motion.div variants={itemVariants}>
        <WeatherLocationIdentity
          location={location}
          comparison={comparison}
          periodTitle={periodTitle}
          isLocationSaved={isLocationSaved}
          isAuthenticated={isAuthenticated}
          onToggleSaveLocation={handleToggleSaveLocation}
          environmentalEvents={environmental_events}
          advisories={advisories}
          isEnvPanelOpen={isEnvPanelOpen}
          onToggleEnvPanel={() => setIsEnvPanelOpen((prev) => !prev)}
        />
      </motion.div>

      {/* Environmental Intelligence Panel Drawer (Toggled by Indicator) */}
      {((environmental_events && environmental_events.length > 0) || advisories.length > 0) && isEnvPanelOpen && (
        <React.Suspense fallback={null}>
          <EnvironmentalEventPanel
            events={environmental_events || []}
            advisories={advisories}
            isOpen={isEnvPanelOpen}
            onClose={() => setIsEnvPanelOpen(false)}
            locationName={location?.name ?? undefined}
          />
        </React.Suspense>
      )}

      {/* 2. OFFICIAL WARNING (Active Orange or Red only - Precedes WeatherGPT synthesis) */}
      <motion.div variants={itemVariants}>
        <OfficialAdvisoryBanner advisories={advisories} />
      </motion.div>

      {/* Severe Weather Alerts (When present in response) */}
      {alerts && alerts.length > 0 && (
        <motion.div variants={itemVariants}>
          {renderAlertBanners()}
        </motion.div>
      )}

      {/* 3. WEATHERGPT HERO (WHAT MATTERS: Prominent unboxed intelligence synthesis) */}
      <motion.div variants={itemVariants}>
        <WeatherGPTHero
          keyInsight={keyInsight}
          detailedSummary={deduplicatedSummary}
          condition={weather.condition}
          weatherCode={weather.weather_code}
          weather={weather}
          decision={decision}
          isUnavailable={isPeriodUnavailable}
          periodTitle={periodTitle}
        />
      </motion.div>

      {/* 4. CORE WEATHER TELEMETRY (WHY: Single borderless telemetry strip) */}
      {comparison ? (
        <motion.div variants={itemVariants}>
          <React.Suspense
            fallback={
              <div
                className="p-6 rounded-3xl animate-pulse space-y-4"
                style={{ backgroundColor: 'var(--surface-secondary)', border: '1px solid var(--border-subtle)' }}
              >
                <div className="h-5 w-48 bg-slate-700/30 rounded" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="h-36 bg-slate-700/20 rounded-2xl" />
                  <div className="h-36 bg-slate-700/20 rounded-2xl" />
                </div>
              </div>
            }
          >
            <ComparisonSurface comparison={comparison} />
          </React.Suspense>
        </motion.div>
      ) : !isPeriodUnavailable ? (
        <motion.div variants={itemVariants}>
          <WeatherTelemetry
            weather={activeTelemetry}
            advisories={advisories}
            inspectedTime={inspectedTimeStr}
            onResetToCurrent={handleResetInspection}
          />
        </motion.div>
      ) : null}

      {/* 5. 24-HOUR FORECAST (EVIDENCE: Preserved intact) */}
      {!comparison && (
        <motion.div variants={itemVariants}>
          <React.Suspense
            fallback={
              <div
                className="p-6 rounded-3xl animate-pulse space-y-4"
                style={{ backgroundColor: 'var(--surface-secondary)', border: '1px solid var(--border-subtle)' }}
              >
                <div className="h-4 w-36 bg-slate-700/30 rounded" />
                <div className="h-44 bg-slate-700/20 rounded-2xl" />
              </div>
            }
          >
            <InteractiveForecastChart
              items={forecastItems}
              periodTitle={periodTitle}
              timezone={location?.timezone ?? null}
              onInspectHour={handleInspectHour}
            />
          </React.Suspense>
        </motion.div>
      )}

      {/* 6. OFFICIAL ADVISORIES (DETAIL: Preserved intact when present) */}
      {advisories && advisories.length > 0 && (
        <motion.div variants={itemVariants}>
          <OfficialAdvisorySection
            advisories={advisories}
            locationName={location?.name ?? undefined}
            showEmptyState={false}
          />
        </motion.div>
      )}

      {/* 7. INTERACTIVE WEATHER MAP (DETAIL: Spatial context preserved intact) */}
      {location && (
        <motion.div variants={itemVariants}>
          <React.Suspense
            fallback={
              <div
                className="h-80 rounded-3xl flex flex-col items-center justify-center animate-pulse space-y-3"
                style={{ backgroundColor: 'var(--surface-secondary)', border: '1px solid var(--border-subtle)' }}
              >
                <div
                  className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
                  style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }}
                />
                <div className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                  Loading interactive weather map...
                </div>
              </div>
            }
          >
            <WeatherMap
              location={comparison ? comparison.location_a : location}
              weather={comparison ? comparison.period_weather_a : weather}
              locationB={comparison?.location_b}
              weatherB={comparison?.period_weather_b}
              periodLabel={periodTitle}
              advisories={advisories}
              onCheckWeatherAtCoords={(lat, lng) => {
                if (onSelectPresetLocation) {
                  onSelectPresetLocation(`${lat}, ${lng}`);
                }
              }}
            />
          </React.Suspense>
        </motion.div>
      )}
    </motion.article>
  );
};

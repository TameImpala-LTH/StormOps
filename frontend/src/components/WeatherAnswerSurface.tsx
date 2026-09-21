import React, { useState, useEffect } from 'react';
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
  Sparkles,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { QueryResponse } from '../types/weather';
import { OfficialAdvisory } from '../types/advisory';
import { fetchOfficialAdvisories } from '../services/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { PRESET_LOCATIONS } from '../utils/locations';
import { EnvironmentalEventIndicator } from './EnvironmentalEventIndicator';
import { OfficialAdvisoryBanner } from './advisory/OfficialAdvisoryBanner';
import { OfficialAdvisorySection } from './advisory/OfficialAdvisorySection';

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

// Extract a concise, prominent key insight (first clean sentence) from AI summary
function extractKeyInsight(summaryText: string): string {
  if (!summaryText) return '';
  const clean = summaryText.trim().replace(/^#+\s+/, '').replace(/^\*+\s+/, '');
  // Match first complete sentence
  const match = clean.match(/^([^.!?\n]+[.!?])/);
  if (match && match[1] && match[1].trim().length >= 8) {
    return match[1].trim();
  }
  const firstLine = clean.split('\n')[0].trim();
  if (firstLine.length <= 180) return firstLine;
  return firstLine.slice(0, 177) + '...';
}

// Weather condition accent styling (distinct from official advisory severity colors)
function getWeatherConditionAccent(
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
  const { theme, darkVariant, accentColor } = useTheme();

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

  const keyInsight = extractKeyInsight(summary);
  const conditionStyle = getWeatherConditionAccent(
    weather.weather_code,
    weather.temperature,
    theme,
    darkVariant,
    accentColor
  );

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
            {((environmental_events && environmental_events.length > 0) || advisories.length > 0) && (
              <EnvironmentalEventIndicator
                events={environmental_events || []}
                advisories={advisories}
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

      {/* Environmental Intelligence Panel (Toggled by Indicator) */}
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

      {/* Official Severe Weather Advisory Banner (Active Orange or Red only) */}
      <OfficialAdvisoryBanner advisories={advisories} />


      {/* 2. WeatherGPT Answer (Placed IMMEDIATELY after Location & Period Header) */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl border transition-all"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border)',
          borderTop: `2px solid ${conditionStyle.accentColor}`,
          boxShadow: conditionStyle.glowStyle,
        }}
      >
        <div className="p-5 sm:p-6 space-y-4">
          {/* 1. WEATHERGPT INTERPRETATION header */}
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div
              className="flex items-center space-x-2 text-xs font-mono uppercase tracking-wider font-semibold"
              style={{ color: 'var(--accent)' }}
            >
              <Sparkles className="w-4 h-4 flex-shrink-0" />
              <span>WeatherGPT Interpretation</span>
            </div>
            <div
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono border"
              style={{
                backgroundColor: conditionStyle.badgeBg,
                borderColor: conditionStyle.badgeBorder,
                color: conditionStyle.accentColor,
              }}
            >
              <span className="capitalize font-medium">{weather.condition}</span>
            </div>
          </div>

          {/* 2. KEY INSIGHT — prominent, concise first-sentence insight */}
          {keyInsight && (
            <div className="pt-0.5">
              <h3
                className="text-lg sm:text-xl font-normal tracking-tight leading-snug"
                style={{ color: 'var(--text-primary)' }}
              >
                {keyInsight}
              </h3>
            </div>
          )}

          {/* 3. Structured metric blocks (visually dominating) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
            {/* Temperature & Feels Like */}
            <div
              className="p-3 rounded-xl border flex flex-col justify-between"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              <div className="flex items-center justify-between text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                <span>Temperature</span>
                <Thermometer className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="mt-2">
                <div className="text-xl font-medium tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  {Math.round(weather.temperature)}°C
                </div>
                <div className="text-[11px] font-mono mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  Feels like {Math.round(weather.feels_like)}°C
                </div>
              </div>
            </div>

            {/* Precipitation */}
            <div
              className="p-3 rounded-xl border flex flex-col justify-between"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              <div className="flex items-center justify-between text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                <span>Precipitation</span>
                <CloudRain className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div className="mt-2">
                <div className="text-xl font-medium tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  {weather.precipitation_probability}%
                </div>
                <div className="text-[11px] font-mono mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }} title={weather.precipitation > 0 ? `${weather.precipitation} mm` : (weather.peak_hour ? `Peak: ${weather.peak_hour}` : 'No rain')}>
                  {weather.precipitation > 0 ? `${weather.precipitation} mm` : (weather.peak_hour ? `Peak: ${weather.peak_hour}` : 'No rain expected')}
                </div>
              </div>
            </div>

            {/* Humidity */}
            <div
              className="p-3 rounded-xl border flex flex-col justify-between"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              <div className="flex items-center justify-between text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                <span>Humidity</span>
                <Droplets className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="mt-2">
                <div className="text-xl font-medium tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  {weather.humidity}%
                </div>
                <div className="text-[11px] font-mono mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {weather.humidity >= 70 ? 'Humid' : weather.humidity >= 40 ? 'Comfortable' : 'Dry'}
                </div>
              </div>
            </div>

            {/* Wind Speed */}
            <div
              className="p-3 rounded-xl border flex flex-col justify-between"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              <div className="flex items-center justify-between text-[11px] font-mono uppercase" style={{ color: 'var(--text-secondary)' }}>
                <span>Wind</span>
                <Wind className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
              </div>
              <div className="mt-2">
                <div className="text-xl font-medium tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  {weather.wind_speed} <span className="text-xs font-normal">km/h</span>
                </div>
                <div className="text-[11px] font-mono mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>
                  {weather.wind_speed >= 30 ? 'Strong wind' : weather.wind_speed >= 15 ? 'Moderate breeze' : 'Light breeze'}
                </div>
              </div>
            </div>
          </div>

          {/* 4. Full AI-generated summary underneath as secondary narrative */}
          <div
            className="pt-3 border-t space-y-1.5"
            style={{ borderColor: 'var(--border-muted)' }}
          >
            <div className="text-[11px] font-mono uppercase tracking-wider font-medium" style={{ color: 'var(--text-secondary)' }}>
              Detailed Interpretation
            </div>
            <div
              className="text-sm font-normal leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              <FormattedMarkdown content={summary} />
            </div>
          </div>
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
          <React.Suspense
            fallback={
              <div
                className="p-6 rounded-3xl animate-pulse space-y-4"
                style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border)' }}
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
          <React.Suspense
            fallback={
              <div
                className="p-6 rounded-3xl animate-pulse space-y-4"
                style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
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
            />
          </React.Suspense>
        </motion.div>
      )}

      {/* Official Environmental & Hazard Advisories (When present) */}
      {advisories && advisories.length > 0 && (
        <motion.div variants={itemVariants}>
          <OfficialAdvisorySection
            advisories={advisories}
            locationName={location?.name ?? undefined}
            showEmptyState={false}
          />
        </motion.div>
      )}

      {/* 7. Interactive Weather Map */}
      {location && (
        <motion.div variants={itemVariants}>
          <React.Suspense
            fallback={
              <div
                className="h-80 rounded-3xl flex flex-col items-center justify-center animate-pulse space-y-3"
                style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <div
                  className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
                  style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}
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
    </motion.div>
  );
};


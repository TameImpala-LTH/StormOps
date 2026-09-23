import React, { useState } from 'react';
import {
  Sparkles,
  Umbrella,
  Footprints,
  Car,
  Shirt,
  Info,
  CheckCircle,
  XCircle,
  AlertCircle,
  AlertTriangle,
  Thermometer,
  CloudRain,
  Wind,
  Lightbulb,
  ChevronDown,
} from 'lucide-react';
import { DecisionResponse } from '../../types/weather';
import { FormattedMarkdown } from '../FormattedMarkdown';
import { WeatherTelemetryData } from './WeatherTelemetry';

export interface WeatherGPTHeroProps {
  keyInsight: string;
  detailedSummary?: string;
  condition: string;
  weatherCode: number;
  weather?: WeatherTelemetryData;
  decision?: DecisionResponse | null;
  isUnavailable?: boolean;
  periodTitle: string;
}

// Map decision type to an icon
function getDecisionIcon(type: string): React.ReactNode {
  const icons: Record<string, React.ReactNode> = {
    umbrella: <Umbrella className="w-4 h-4" />,
    outdoor_activity: <Footprints className="w-4 h-4" />,
    travel: <Car className="w-4 h-4" />,
    clothing: <Shirt className="w-4 h-4" />,
  };
  return icons[type] ?? <Info className="w-4 h-4" />;
}

// Map recommendation to semantic styles
function getRecommendationStyle(rec: string): {
  icon: React.ReactNode;
  textColor: string;
  badgeBg: string;
  badgeBorder: string;
} {
  switch (rec) {
    case 'recommended':
      return {
        icon: <CheckCircle className="w-3.5 h-3.5" />,
        textColor: '#34d399',
        badgeBg: 'rgba(16, 185, 129, 0.12)',
        badgeBorder: 'rgba(16, 185, 129, 0.30)',
      };
    case 'not_recommended':
      return {
        icon: <XCircle className="w-3.5 h-3.5" />,
        textColor: '#f87171',
        badgeBg: 'rgba(239, 68, 68, 0.12)',
        badgeBorder: 'rgba(239, 68, 68, 0.30)',
      };
    default:
      return {
        icon: <AlertCircle className="w-3.5 h-3.5" />,
        textColor: '#fbbf24',
        badgeBg: 'rgba(217, 119, 6, 0.12)',
        badgeBorder: 'rgba(217, 119, 6, 0.30)',
      };
  }
}

interface BriefingBullet {
  category: string;
  icon: React.ReactNode;
  content: string;
}

export function generateScannableBullets(
  weather?: WeatherTelemetryData,
  decision?: DecisionResponse | null,
  condition?: string
): BriefingBullet[] {
  const temp = weather?.temperature !== undefined ? Math.round(weather.temperature) : undefined;
  const feelsLike = weather?.feels_like !== undefined ? Math.round(weather.feels_like) : undefined;
  const humidity = weather?.humidity ?? 0;
  const windSpeed = weather?.wind_speed ?? 0;
  const prob = weather?.precipitation_probability ?? 0;
  const peakHour = weather?.peak_hour;
  const precip = weather?.precipitation ?? 0;

  // 1. Conditions & Comfort
  let comfortText = '';
  if (temp !== undefined && feelsLike !== undefined) {
    if (feelsLike >= temp + 3) {
      comfortText = `Feels warmer than actual temperature (${feelsLike}°C vs ${temp}°C) due to elevated humidity (${humidity}%).`;
    } else if (feelsLike <= temp - 3) {
      comfortText = `Feels noticeably cooler (${feelsLike}°C) due to brisk wind conditions.`;
    } else if (temp >= 33) {
      comfortText = `High heat environment (${temp}°C); prolonged sun exposure may cause fatigue.`;
    } else if (temp >= 24) {
      comfortText = `Warm and ${humidity >= 65 ? 'humid' : 'pleasant'} (${temp}°C); comfortable for indoor or shaded outdoor activity.`;
    } else if (temp >= 16) {
      comfortText = `Mild and pleasant (${temp}°C) with comfortable ambient moisture levels (${humidity}%).`;
    } else if (temp >= 8) {
      comfortText = `Cool conditions (${temp}°C); a light jacket or sweater will maintain comfort.`;
    } else {
      comfortText = `Cold temperatures (${temp}°C); insulating layers recommended.`;
    }
  } else if (condition) {
    comfortText = `Ambient conditions are currently described as ${condition.toLowerCase()}.`;
  } else {
    comfortText = `Current thermal comfort remains within normal seasonal expectations.`;
  }

  // 2. Rain & Timing
  let rainText = '';
  if (prob >= 60) {
    rainText = peakHour
      ? `High likelihood of precipitation (${prob}%), peaking around ${peakHour}. Rain gear strongly recommended.`
      : `High probability of rainfall (${prob}%). Expect wet ground and possible travel delays.`;
  } else if (prob >= 30) {
    rainText = peakHour
      ? `Scattered showers possible (${prob}% chance), with highest probability near ${peakHour}.`
      : `Intermittent showers possible (${prob}% chance); keep a compact umbrella nearby.`;
  } else if (precip > 0) {
    rainText = `Light localized precipitation (${precip} mm) observed; overall low disruption.`;
  } else {
    rainText = `Dry conditions expected with no notable rain forecast for the period.`;
  }

  // 3. Wind & Atmosphere
  let windText = '';
  if (windSpeed >= 40) {
    windText = `Strong winds (${windSpeed} km/h); expect notable resistance and caution on open bridges or elevated areas.`;
  } else if (windSpeed >= 20) {
    windText = `Breezy winds (${windSpeed} km/h); keeps air circulating and provides cooling effect.`;
  } else if (windSpeed >= 8) {
    windText = `Gentle breeze (${windSpeed} km/h); calm outdoor conditions with minimal drift.`;
  } else {
    windText = `Light air or calm winds (${windSpeed} km/h); stable atmospheric air motion.`;
  }

  // 4. Practical Advice
  let adviceText = '';
  if (decision?.summary) {
    adviceText = decision.summary;
  } else if (
    decision?.recommendation === 'umbrella_recommended' ||
    (decision?.recommendation === 'recommended' && decision?.type === 'umbrella')
  ) {
    adviceText = `Carry an umbrella or rain poncho before heading out.`;
  } else if (decision?.recommendation === 'not_recommended') {
    adviceText = `Outdoor activities are not recommended under current meteorological conditions.`;
  } else if (decision?.recommendation === 'recommended') {
    adviceText = `Great opportunity for planned outdoor travel, exercise, and leisure.`;
  } else if (prob >= 50) {
    adviceText = `Pack wet-weather gear and allow extra commute buffer for wet roadways.`;
  } else if (temp !== undefined && temp >= 32) {
    adviceText = `Stay hydrated, wear UV-protective sunglasses, and favor shaded routes.`;
  } else {
    adviceText = `Favorable conditions for regular daily commutes and outdoor routines.`;
  }

  return [
    {
      category: 'Conditions & Comfort',
      icon: <Thermometer className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />,
      content: comfortText,
    },
    {
      category: 'Rain & Timing',
      icon: <CloudRain className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />,
      content: rainText,
    },
    {
      category: 'Wind & Air',
      icon: <Wind className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />,
      content: windText,
    },
    {
      category: 'Practical Advice',
      icon: <Lightbulb className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />,
      content: adviceText,
    },
  ];
}

export const WeatherGPTHero: React.FC<WeatherGPTHeroProps> = ({
  keyInsight,
  detailedSummary,
  condition,
  weather,
  decision,
  isUnavailable,
  periodTitle,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  if (isUnavailable) {
    return (
      <section
        aria-label="Weather intelligence briefing"
        className="p-5 sm:p-6 rounded-2xl border"
        style={{
          backgroundColor: 'var(--surface-primary)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex items-center gap-2 text-amber-400 font-mono text-xs uppercase font-semibold">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Forecast Unavailable for {periodTitle}</span>
        </div>
        <p className="text-xs leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
          Authoritative forecast metrics for {periodTitle} could not be calculated from the meteorological feed.
          Current observation values are strictly not substituted to prevent misinformation.
        </p>
      </section>
    );
  }

  const recStyle = decision?.recommendation ? getRecommendationStyle(decision.recommendation) : null;
  const bullets = generateScannableBullets(weather, decision, condition);

  return (
    <section
      aria-label="Weather intelligence briefing"
      className="p-5 sm:p-6 rounded-2xl border space-y-4"
      style={{
        backgroundColor: 'var(--surface-primary)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* 1. Kicker / Mode Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div
          className="flex items-center gap-1.5 type-label"
          style={{ color: 'var(--accent-primary)' }}
        >
          <Sparkles className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
          <span>WeatherGPT Briefing</span>
        </div>

        {/* Condition pill */}
        {condition && (
          <span
            className="type-label px-2.5 py-0.5 rounded-full capitalize"
            style={{
              backgroundColor: 'var(--surface-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {condition}
          </span>
        )}
      </div>

      {/* LEVEL 1: WHAT MATTERS — Primary Synthesis Headline */}
      {keyInsight && (
        <h2
          className="text-xl sm:text-2xl lg:text-3xl font-light tracking-tight leading-snug max-w-3xl"
          style={{ color: 'var(--text-primary)' }}
        >
          {keyInsight}
        </h2>
      )}

      {/* Action / Recommendation Badge (Strictly only when decision exists from backend) */}
      {decision && (
        <div className="flex items-center gap-2.5 flex-wrap pt-0.5">
          {decision.recommendation && recStyle && (
            <div
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border"
              style={{
                backgroundColor: recStyle.badgeBg,
                borderColor: recStyle.badgeBorder,
                color: recStyle.textColor,
              }}
            >
              <span className="flex-shrink-0">{getDecisionIcon(decision.type)}</span>
              <span>{decision.recommendation.replace(/_/g, ' ')}</span>
            </div>
          )}

          {/* Real confidence signal ONLY when backend supplies it */}
          {decision.confidence && (
            <span
              className="type-meta px-2 py-0.5 rounded uppercase text-[11px]"
              style={{
                backgroundColor: 'var(--surface-secondary)',
                color: 'var(--text-tertiary)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              {decision.confidence} confidence
            </span>
          )}
        </div>
      )}

      {/* LEVEL 2: BRIEFING — Compact Scannable Bullet Structure */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
        {bullets.map((bullet) => (
          <div
            key={bullet.category}
            className="p-3 rounded-xl border flex items-start gap-2.5 text-xs transition-colors"
            style={{
              backgroundColor: 'var(--surface-secondary)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <div className="mt-0.5">{bullet.icon}</div>
            <div className="min-w-0">
              <span
                className="font-semibold block text-[11px] uppercase tracking-wider mb-0.5"
                style={{ color: 'var(--text-tertiary)' }}
              >
                {bullet.category}
              </span>
              <p className="leading-relaxed text-xs" style={{ color: 'var(--text-secondary)' }}>
                {bullet.content}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* LEVEL 3: DETAILED INTERPRETATION — Collapsible Disclosure */}
      {detailedSummary && (
        <div
          className="pt-2 border-t"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            aria-expanded={isExpanded}
            aria-controls="weathergpt-detailed-interpretation"
            className="inline-flex items-center gap-1.5 text-xs font-mono font-medium hover:opacity-80 transition-opacity cursor-pointer py-1"
            style={{ color: 'var(--accent-primary)' }}
          >
            <span>
              {isExpanded ? 'Hide Detailed Interpretation' : 'Read Detailed Interpretation'}
            </span>
            <ChevronDown
              className={`w-3.5 h-3.5 transition-transform duration-200 ${
                isExpanded ? 'rotate-180' : ''
              }`}
            />
          </button>

          {isExpanded && (
            <div
              id="weathergpt-detailed-interpretation"
              className="mt-2.5 pt-2.5 border-t type-body-sm leading-relaxed max-w-3xl"
              style={{
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-secondary)',
              }}
            >
              <FormattedMarkdown content={detailedSummary} />
            </div>
          )}
        </div>
      )}
    </section>
  );
};

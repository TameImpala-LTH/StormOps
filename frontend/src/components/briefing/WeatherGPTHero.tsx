import React from 'react';
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
} from 'lucide-react';
import { DecisionResponse } from '../../types/weather';
import { FormattedMarkdown } from '../FormattedMarkdown';

interface WeatherGPTHeroProps {
  keyInsight: string;
  detailedSummary?: string;
  condition: string;
  weatherCode: number;
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

export const WeatherGPTHero: React.FC<WeatherGPTHeroProps> = ({
  keyInsight,
  detailedSummary,
  condition,
  decision,
  isUnavailable,
  periodTitle,
}) => {
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

      {/* 2. WHAT MATTERS: Primary Synthesis Headline */}
      {keyInsight && (
        <h2
          className="text-xl sm:text-2xl lg:text-3xl font-light tracking-tight leading-snug max-w-3xl"
          style={{ color: 'var(--text-primary)' }}
        >
          {keyInsight}
        </h2>
      )}

      {/* 3. Action / Recommendation Badge (Strictly only when decision exists from backend) */}
      {decision && (
        <div className="flex items-center gap-2.5 flex-wrap pt-1">
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

      {/* 4. Detailed Interpretation (Secondary Narrative) */}
      {detailedSummary && (
        <div
          className="pt-3 border-t space-y-1"
          style={{ borderColor: 'var(--border-subtle)' }}
        >
          <div
            className="type-label"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Detailed Interpretation
          </div>
          <div
            className="type-body-sm leading-relaxed max-w-3xl"
            style={{ color: 'var(--text-secondary)' }}
          >
            <FormattedMarkdown content={detailedSummary} />
          </div>
        </div>
      )}
    </section>
  );
};

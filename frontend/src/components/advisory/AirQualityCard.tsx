import React from 'react';
import { Wind, MapPin, ExternalLink } from 'lucide-react';
import { OfficialAdvisory } from '../../types/advisory';

interface AirQualityCardProps {
  advisory: OfficialAdvisory;
}

function getAqiCategoryDetails(officialLevel?: string | null): {
  category: string;
  color: string;
  bg: string;
  border: string;
  aqiValue?: string;
} {
  const level = (officialLevel || '').toUpperCase();
  let category = 'Moderate';
  let color = '#eab308';
  let bg = 'rgba(234,179,8,0.10)';
  let border = 'rgba(234,179,8,0.25)';
  let aqiValue: string | undefined = undefined;

  // Try extracting number from "AQI 320 (Very Poor)" or "AQI 412"
  const match = level.match(/AQI\s*(\d+)/i);
  if (match) {
    aqiValue = match[1];
  }

  if (level.includes('SEVERE')) {
    category = 'Severe';
    color = '#991b1b';
    bg = 'rgba(153,27,27,0.12)';
    border = 'rgba(153,27,27,0.30)';
  } else if (level.includes('VERY POOR')) {
    category = 'Very Poor';
    color = '#f43f5e';
    bg = 'rgba(244,63,94,0.12)';
    border = 'rgba(244,63,94,0.30)';
  } else if (level.includes('POOR')) {
    category = 'Poor';
    color = '#f97316';
    bg = 'rgba(249,115,22,0.10)';
    border = 'rgba(249,115,22,0.25)';
  } else if (level.includes('MODERATE')) {
    category = 'Moderate';
    color = '#eab308';
    bg = 'rgba(234,179,8,0.10)';
    border = 'rgba(234,179,8,0.25)';
  } else if (level.includes('SATISFACTORY')) {
    category = 'Satisfactory';
    color = '#10b981';
    bg = 'rgba(16,185,129,0.10)';
    border = 'rgba(16,185,129,0.25)';
  } else if (level.includes('GOOD')) {
    category = 'Good';
    color = '#059669';
    bg = 'rgba(5,150,105,0.10)';
    border = 'rgba(5,150,105,0.25)';
  }

  return { category, color, bg, border, aqiValue };
}

export const AirQualityCard: React.FC<AirQualityCardProps> = ({ advisory }) => {
  const { category, color, bg, border, aqiValue } = getAqiCategoryDetails(advisory.official_level);

  return (
    <article
      aria-label={`Air quality bulletin: ${category} AQI`}
      className="p-4 sm:p-5 rounded-2xl border space-y-3 transition-colors"
      style={{
        backgroundColor: 'var(--surface-secondary)',
        borderColor: border,
      }}
    >
      {/* 1. Header: Environmental Measurement Identity */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div
            className="p-1.5 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: bg, color }}
          >
            <Wind className="w-4 h-4" />
          </div>
          <div>
            <span
              className="text-[10px] font-mono font-bold uppercase tracking-wider block"
              style={{ color }}
            >
              Air Quality Bulletin · NAQI
            </span>
            <span
              className="text-xs font-mono"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Continuous Ambient Air Quality Monitoring (CPCB)
            </span>
          </div>
        </div>

        <span
          className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border tracking-wider uppercase"
          style={{
            backgroundColor: bg,
            borderColor: border,
            color,
          }}
        >
          {category.toUpperCase()}
        </span>
      </div>

      {/* 2. Main AQI Value Block */}
      <div className="flex items-baseline space-x-3 pt-1">
        {aqiValue ? (
          <span className="text-3xl sm:text-4xl font-light font-mono tabular-nums" style={{ color }}>
            {aqiValue}
          </span>
        ) : (
          <span className="text-2xl font-light font-mono" style={{ color }}>
            {category}
          </span>
        )}
        <div className="text-xs space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{advisory.headline}</p>
          {advisory.description && <p className="line-clamp-2">{advisory.description}</p>}
        </div>
      </div>

      {/* 3. Official Health Guidance (Strictly when supplied by source) */}
      {advisory.action_guidance && (
        <div
          className="p-3 rounded-xl text-xs space-y-1 border"
          style={{
            backgroundColor: 'var(--surface-primary)',
            borderColor: 'var(--border-subtle)',
            color: 'var(--text-primary)',
          }}
        >
          <span
            className="text-[10px] font-mono uppercase font-semibold tracking-wider block"
            style={{ color }}
          >
            Official Public Health Guidance
          </span>
          <p className="leading-relaxed text-xs">{advisory.action_guidance}</p>
        </div>
      )}

      {/* 4. Footer: Station & CPCB Attribution */}
      <div
        className="flex flex-col sm:flex-row sm:items-center justify-between pt-2 gap-2 text-[11px] font-mono border-t"
        style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-tertiary)' }}
      >
        <div className="flex items-center space-x-1.5">
          <MapPin className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
          <span>
            Station: {advisory.district || advisory.state || 'Local Station'}
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <span>Source: Central Pollution Control Board (CPCB)</span>
          {advisory.source_url && (
            <a
              href={advisory.source_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open CPCB CAAQM Portal in a new tab"
              className="inline-flex items-center space-x-1 underline hover:no-underline cursor-pointer"
              style={{ color }}
            >
              <span>CAAQM Portal</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
};

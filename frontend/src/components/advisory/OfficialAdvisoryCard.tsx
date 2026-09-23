import React, { useState } from 'react';
import { Clock, MapPin, ExternalLink, ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../../types/advisory';
import { AdvisorySeverityBadge } from './AdvisorySeverityBadge';

interface OfficialAdvisoryCardProps {
  advisory: OfficialAdvisory;
  isPromotedAbove?: boolean;
}

export function formatAuthorityName(authority: string): string {
  const map: Record<string, string> = {
    IMD: 'India Meteorological Department (IMD)',
    NDMA: 'National Disaster Management Authority (NDMA)',
    CWC: 'Central Water Commission (CWC)',
    INCOIS: 'Indian National Centre for Ocean Information Services (INCOIS)',
    CPCB: 'Central Pollution Control Board (CPCB)',
  };
  return map[authority.toUpperCase()] || authority;
}

export function formatDateTime(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return d.toLocaleString('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return isoDate;
  }
}

export const OfficialAdvisoryCard: React.FC<OfficialAdvisoryCardProps> = ({
  advisory,
  isPromotedAbove = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const temporalState = getAdvisoryTemporalState(advisory);
  const isActive = temporalState === 'ACTIVE';
  const isUpcoming = temporalState === 'UPCOMING';

  const sev = (advisory.severity || '').toLowerCase();
  const isSevere = sev === 'red' || sev === 'orange';

  // Official severity border semantics (immutable across themes)
  let cardBorder = 'var(--border-subtle)';
  if (isActive && isSevere) {
    cardBorder = sev === 'red' ? 'rgba(244,63,94,0.35)' : 'rgba(249,115,22,0.35)';
  } else if (isUpcoming) {
    cardBorder = 'rgba(234,179,8,0.25)';
  }

  const description = advisory.description || '';
  const isLongDescription = description.length > 180;
  const displayedDescription = !isExpanded && isLongDescription
    ? `${description.slice(0, 180).trim()}...`
    : description;

  // Promoted severe advisory deduplication: Render compact reference row instead of repeating full paragraphs
  if (isPromotedAbove) {
    return (
      <article
        aria-label={`Official advisory reference: ${advisory.headline}`}
        className="p-3.5 sm:p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors"
        style={{
          backgroundColor: 'var(--surface-secondary)',
          borderColor: 'rgba(244,63,94,0.25)',
        }}
      >
        <div className="flex items-center space-x-2.5 min-w-0">
          <AdvisorySeverityBadge severity={advisory.severity} officialLevel={advisory.official_level} size="sm" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-mono text-zinc-400">
                OFFICIAL · {advisory.authority.toUpperCase()}
              </span>
              <span
                className="text-[10px] font-mono px-2 py-0.2 rounded border"
                style={{
                  backgroundColor: 'rgba(244,63,94,0.08)',
                  borderColor: 'rgba(244,63,94,0.22)',
                  color: '#f43f5e',
                }}
              >
                Surfaced in alert banner ↑
              </span>
            </div>
            <h4 className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
              {advisory.headline}
            </h4>
          </div>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto text-[11px] font-mono flex-shrink-0">
          <span className="text-zinc-400">Source: {formatAuthorityName(advisory.authority)}</span>
          {advisory.source_url && (
            <a
              href={advisory.source_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open official source bulletin from ${advisory.authority} in a new tab`}
              className="inline-flex items-center space-x-1 underline hover:no-underline cursor-pointer"
              style={{ color: 'var(--accent-primary)' }}
            >
              <span>Official Portal</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </article>
    );
  }

  return (
    <article
      aria-label={`Official advisory: ${advisory.headline}`}
      className="p-4 sm:p-5 rounded-2xl border space-y-3 transition-colors"
      style={{
        backgroundColor: 'var(--surface-secondary)',
        borderColor: cardBorder,
      }}
    >
      {/* 1. Header: Authoritative Issuing Source & Severity Badge */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          {isActive ? (
            <span
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wider"
              style={{
                backgroundColor: 'rgba(16,185,129,0.12)',
                color: '#10b981',
                border: '1px solid rgba(16,185,129,0.30)',
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              ACTIVE NOW
            </span>
          ) : isUpcoming ? (
            <span
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold tracking-wider"
              style={{
                backgroundColor: 'rgba(234,179,8,0.10)',
                color: '#eab308',
                border: '1px solid rgba(234,179,8,0.25)',
              }}
            >
              <Clock className="w-3 h-3" />
              UPCOMING
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono tracking-wider"
              style={{
                backgroundColor: 'rgba(113,113,122,0.10)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              EXPIRED
            </span>
          )}

          <span
            className="text-[10px] font-mono uppercase font-semibold px-2 py-0.5 rounded-md"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              color: 'var(--text-secondary)',
            }}
          >
            {advisory.hazard_type.replace(/_/g, ' ')}
          </span>

          {isPromotedAbove && (
            <span
              className="text-[10px] font-mono px-2 py-0.5 rounded-md"
              style={{
                backgroundColor: 'rgba(244,63,94,0.08)',
                color: '#f43f5e',
                border: '1px solid rgba(244,63,94,0.20)',
              }}
            >
              Surfaced in alert banner ↑
            </span>
          )}
        </div>

        <AdvisorySeverityBadge
          severity={advisory.severity}
          officialLevel={advisory.official_level}
          size="sm"
        />
      </div>

      {/* 2. Headline & Authority Attribution */}
      <div className="space-y-1">
        <div className="flex items-center gap-1 text-[11px] font-mono text-zinc-400">
          <ShieldAlert className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
          <span>OFFICIAL · {advisory.authority.toUpperCase()}</span>
        </div>
        <h4
          className="text-base font-medium leading-snug tracking-tight"
          style={{ color: 'var(--text-primary)' }}
        >
          {advisory.headline}
        </h4>
      </div>

      {/* 3. Description with Truncation / Disclosure */}
      {description && (
        <div className="space-y-1">
          <p
            className="text-xs sm:text-sm leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}
          >
            {displayedDescription}
          </p>
          {isLongDescription && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              aria-expanded={isExpanded}
              className="inline-flex items-center gap-1 text-xs font-mono font-medium hover:underline cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--focus-ring)] rounded"
              style={{ color: 'var(--accent-primary)' }}
            >
              <span>{isExpanded ? 'Show less' : 'Read more'}</span>
              {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>
      )}

      {/* 4. Official Public Guidance (Rendered strictly when supplied by authoritative data) */}
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
            style={{ color: '#f59e0b' }}
          >
            Official Public Guidance
          </span>
          <p className="leading-relaxed text-xs">{advisory.action_guidance}</p>
        </div>
      )}

      {/* 5. Geographic Scope & Validity Window */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 text-xs border-t"
        style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-secondary)' }}
      >
        <div className="flex items-center space-x-1.5 font-mono text-[11px]">
          <MapPin className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
          <span>
            {advisory.district ? `${advisory.district}` : ''}
            {advisory.state ? (advisory.district ? `, ${advisory.state}` : advisory.state) : ''}
            {!advisory.district && !advisory.state ? 'Pan-India Scope' : ''}
            <span className="opacity-60 ml-1">({advisory.granularity})</span>
          </span>
        </div>

        <div className="flex items-center space-x-1.5 font-mono text-[11px]">
          <Clock className="w-3.5 h-3.5 flex-shrink-0 text-zinc-400" />
          <span>
            {formatDateTime(advisory.effective_at)} – {formatDateTime(advisory.expires_at)}
          </span>
        </div>
      </div>

      {/* 6. Issuing Authority Attribution & Safe External Link */}
      <div
        className="flex items-center justify-between pt-2 text-[11px] font-mono border-t"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex items-center space-x-1.5" style={{ color: 'var(--text-tertiary)' }}>
          <span>Source: {formatAuthorityName(advisory.authority)}</span>
        </div>

        {advisory.source_url && (
          <a
            href={advisory.source_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open official source bulletin from ${advisory.authority} in a new tab`}
            className="inline-flex items-center space-x-1 underline hover:no-underline cursor-pointer"
            style={{ color: 'var(--accent-primary)' }}
          >
            <span>Official Portal</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </article>
  );
};

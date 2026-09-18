import React from 'react';
import { Clock, MapPin, ExternalLink, ShieldAlert } from 'lucide-react';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../../types/advisory';
import { AdvisorySeverityBadge } from './AdvisorySeverityBadge';

interface OfficialAdvisoryCardProps {
  advisory: OfficialAdvisory;
}

function formatAuthorityName(authority: string): string {
  const map: Record<string, string> = {
    IMD: 'India Meteorological Department (IMD)',
    NDMA: 'National Disaster Management Authority (NDMA)',
    CWC: 'Central Water Commission (CWC)',
    INCOIS: 'Indian National Centre for Ocean Information Services (INCOIS)',
    CPCB: 'Central Pollution Control Board (CPCB)',
  };
  return map[authority.toUpperCase()] || authority;
}

function formatDateTime(isoDate: string): string {
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

export const OfficialAdvisoryCard: React.FC<OfficialAdvisoryCardProps> = ({ advisory }) => {
  const temporalState = getAdvisoryTemporalState(advisory);
  const isActive = temporalState === 'ACTIVE';
  const isUpcoming = temporalState === 'UPCOMING';

  const sev = (advisory.severity || '').toLowerCase();
  const isSevere = sev === 'red' || sev === 'orange';

  return (
    <article
      className="p-4 sm:p-5 rounded-2xl border space-y-3 transition-all"
      style={{
        backgroundColor: 'var(--surface-elevated)',
        borderColor: isSevere
          ? sev === 'red'
            ? 'rgba(244,63,94,0.30)'
            : 'rgba(249,115,22,0.30)'
          : 'var(--border)',
      }}
    >
      {/* Top status bar: Active/Upcoming + Severity Badge */}
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
                backgroundColor: 'rgba(56,189,248,0.10)',
                color: '#38bdf8',
                border: '1px solid rgba(56,189,248,0.25)',
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
                border: '1px solid var(--border-muted)',
              }}
            >
              EXPIRED
            </span>
          )}

          <span
            className="text-[10px] font-mono uppercase font-semibold px-2 py-0.5 rounded-md"
            style={{
              backgroundColor: 'var(--surface-input)',
              color: 'var(--text-secondary)',
            }}
          >
            {advisory.hazard_type.replace(/_/g, ' ')}
          </span>
        </div>

        <AdvisorySeverityBadge
          severity={advisory.severity}
          officialLevel={advisory.official_level}
          size="sm"
        />
      </div>

      {/* Headline & Description */}
      <div className="space-y-1.5">
        <h4
          className="text-base font-medium leading-snug"
          style={{ color: 'var(--text-primary)' }}
        >
          {advisory.headline}
        </h4>
        <p
          className="text-xs sm:text-sm leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}
        >
          {advisory.description}
        </p>
      </div>

      {/* Official Action Guidance (only when provided) */}
      {advisory.action_guidance && (
        <div
          className="p-3 rounded-xl text-xs space-y-1 border"
          style={{
            backgroundColor: 'var(--surface)',
            borderColor: 'var(--border-muted)',
            color: 'var(--text-primary)',
          }}
        >
          <span
            className="text-[10px] font-mono uppercase font-semibold tracking-wider block"
            style={{ color: 'var(--accent)' }}
          >
            Official Public Guidance
          </span>
          <p className="leading-relaxed">{advisory.action_guidance}</p>
        </div>
      )}

      {/* Geographic Scope & Temporal Window */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 text-xs border-t"
        style={{ borderColor: 'var(--border-muted)', color: 'var(--text-secondary)' }}
      >
        <div className="flex items-center space-x-1.5 font-mono text-[11px]">
          <MapPin className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
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

      {/* Issuing Authority & Source Link */}
      <div
        className="flex items-center justify-between pt-2 text-[11px] font-mono border-t"
        style={{ borderColor: 'var(--border-muted)' }}
      >
        <div className="flex items-center space-x-1.5" style={{ color: 'var(--text-muted)' }}>
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 text-sky-400" />
          <span>Source: {formatAuthorityName(advisory.authority)}</span>
        </div>

        {advisory.source_url && (
          <a
            href={advisory.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-1 underline hover:no-underline"
            style={{ color: 'var(--accent)' }}
          >
            <span>Official Portal</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </article>
  );
};

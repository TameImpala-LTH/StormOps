import React, { useState } from 'react';
import { ShieldAlert, ExternalLink, Clock, AlertTriangle } from 'lucide-react';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../../types/advisory';
import { AdvisorySeverityBadge } from './AdvisorySeverityBadge';

interface OfficialAdvisoryBannerProps {
  advisories: OfficialAdvisory[];
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

function formatExpiryTime(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZoneName: 'short',
    });
  } catch {
    return isoDate;
  }
}

export const OfficialAdvisoryBanner: React.FC<OfficialAdvisoryBannerProps> = ({ advisories }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filter for currently active Orange and Red advisories (excluding upcoming and expired)
  const severeAdvisories = advisories.filter((a) => {
    const sev = (a.severity || '').toLowerCase();
    const isActive = getAdvisoryTemporalState(a) === 'ACTIVE';
    return isActive && (sev === 'red' || sev === 'orange');
  });

  if (severeAdvisories.length === 0) return null;

  const current = severeAdvisories[selectedIndex] || severeAdvisories[0];
  const isRed = (current.severity || '').toLowerCase() === 'red';

  const bannerBorder = isRed ? 'rgba(244,63,94,0.40)' : 'rgba(249,115,22,0.40)';
  const bannerBg = isRed ? 'rgba(244,63,94,0.06)' : 'rgba(249,115,22,0.06)';
  const accentColor = isRed ? '#f43f5e' : '#f97316';

  return (
    <aside
      aria-label="Official Severe Weather Advisory Banner"
      className="w-full rounded-2xl border p-4 sm:p-5 space-y-3.5 transition-all shadow-sm"
      style={{
        backgroundColor: bannerBg,
        borderColor: bannerBorder,
      }}
    >
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div
            className="p-1.5 rounded-lg flex items-center justify-center"
            style={{
              backgroundColor: isRed ? 'rgba(244,63,94,0.15)' : 'rgba(249,115,22,0.15)',
              color: accentColor,
            }}
          >
            {isRed ? <AlertTriangle className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
          </div>
          <span
            className="text-xs font-mono font-bold uppercase tracking-wider"
            style={{ color: accentColor }}
          >
            Official Government Advisory
          </span>
        </div>

        <div className="flex items-center gap-2">
          {severeAdvisories.length > 1 && (
            <div className="flex items-center space-x-1 mr-1">
              {severeAdvisories.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSelectedIndex(idx)}
                  className={`w-2 h-2 rounded-full transition-all cursor-pointer ${
                    idx === selectedIndex ? 'w-5' : 'opacity-40 hover:opacity-80'
                  }`}
                  style={{ backgroundColor: accentColor }}
                  aria-label={`View advisory ${idx + 1} of ${severeAdvisories.length}`}
                />
              ))}
            </div>
          )}

          <AdvisorySeverityBadge
            severity={current.severity}
            officialLevel={current.official_level}
            size="sm"
          />
        </div>
      </div>

      {/* Main Headline & Hazard Type */}
      <div>
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span
            className="text-[11px] font-mono uppercase font-semibold px-2 py-0.5 rounded-md"
            style={{
              backgroundColor: isRed ? 'rgba(244,63,94,0.12)' : 'rgba(249,115,22,0.12)',
              color: accentColor,
            }}
          >
            {current.hazard_type.replace(/_/g, ' ')}
          </span>
          {current.district && (
            <span className="text-[11px] font-mono" style={{ color: 'var(--text-secondary)' }}>
              · {current.district}
              {current.state ? `, ${current.state}` : ''}
            </span>
          )}
        </div>
        <h3
          className="text-base sm:text-lg font-medium leading-snug"
          style={{ color: 'var(--text-primary)' }}
        >
          {current.headline}
        </h3>
      </div>

      {/* Description */}
      {current.description && (
        <p
          className="text-xs sm:text-sm leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}
        >
          {current.description}
        </p>
      )}

      {/* Official Public Guidance (Only when provided by source) */}
      {current.action_guidance && (
        <div
          className="p-3 rounded-xl text-xs space-y-1 border"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: bannerBorder,
            color: 'var(--text-primary)',
          }}
        >
          <span
            className="text-[10px] font-mono uppercase tracking-wider font-semibold block"
            style={{ color: accentColor }}
          >
            Official Public Guidance
          </span>
          <p className="leading-relaxed">{current.action_guidance}</p>
        </div>
      )}

      {/* Footer: Expiry time, Authority & Link */}
      <div
        className="flex flex-col sm:flex-row sm:items-center justify-between pt-2 gap-2 text-xs border-t"
        style={{ borderColor: 'var(--border-muted)' }}
      >
        <div className="flex items-center space-x-1.5" style={{ color: 'var(--text-muted)' }}>
          <Clock className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Valid until: {formatExpiryTime(current.expires_at)}</span>
        </div>

        <div className="flex items-center space-x-3">
          <span className="font-mono text-[11px]" style={{ color: 'var(--text-secondary)' }}>
            Source: {formatAuthorityName(current.authority)}
          </span>
          {current.source_url && (
            <a
              href={current.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1 underline hover:no-underline font-mono text-[11px]"
              style={{ color: accentColor }}
            >
              <span>Official Source</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </aside>
  );
};

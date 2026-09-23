import React, { useState } from 'react';
import { ShieldAlert, ShieldCheck, ChevronDown, ChevronUp, Wind, Clock, ExternalLink } from 'lucide-react';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../../types/advisory';
import { OfficialAdvisoryCard } from './OfficialAdvisoryCard';
import { AirQualityCard } from './AirQualityCard';
import { AdvisorySeverityBadge } from './AdvisorySeverityBadge';

interface OfficialAdvisorySectionProps {
  advisories: OfficialAdvisory[];
  locationName?: string;
  showEmptyState?: boolean;
  promotedAdvisoryIds?: string[];
}

export const OfficialAdvisorySection: React.FC<OfficialAdvisorySectionProps> = ({
  advisories,
  locationName: _locationName,
  showEmptyState = false,
  promotedAdvisoryIds = [],
}) => {
  const [isMultiExpanded, setIsMultiExpanded] = useState(false);

  // 1. Separate AQI bulletins from meteorological & hazard advisories
  const aqiAdvisories = advisories.filter(
    (a) => a.hazard_type === 'AIR_QUALITY' || a.authority.toUpperCase() === 'CPCB'
  );
  const weatherAdvisories = advisories.filter(
    (a) => a.hazard_type !== 'AIR_QUALITY' && a.authority.toUpperCase() !== 'CPCB'
  );

  const now = new Date();

  // 2. Active vs Upcoming weather advisories using authoritative temporal validity
  // Expired advisories are strictly excluded from active and upcoming presentation
  const activeAdvisories = weatherAdvisories.filter(
    (a) => getAdvisoryTemporalState(a, now) === 'ACTIVE'
  );

  const upcomingAdvisories = weatherAdvisories.filter(
    (a) => getAdvisoryTemporalState(a, now) === 'UPCOMING'
  );

  const totalWeatherCount = activeAdvisories.length + upcomingAdvisories.length;
  const totalCount = totalWeatherCount + aqiAdvisories.length;
  const hasAnyContent = totalCount > 0;

  // 3. ZERO-STATE BEHAVIOR
  // If zero unexpired advisories and zero AQI:
  // - If showEmptyState is false: render absolutely nothing (zero vertical space).
  // - If showEmptyState is true: render an extremely quiet, subtle 1-line state.
  if (!hasAnyContent) {
    if (!showEmptyState) {
      return null;
    }
    return (
      <section
        aria-label="Official Information"
        className="py-2 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono text-zinc-400 border border-zinc-800/60 bg-zinc-900/30">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span className="font-semibold text-zinc-300">OFFICIAL CONDITIONS</span>
          <span>·</span>
          <span>No active official advisories are currently available for this location.</span>
        </div>
      </section>
    );
  }

  // Determine section header badge
  let countBadgeText = '';
  if (activeAdvisories.length > 0) {
    countBadgeText = `${activeAdvisories.length} ACTIVE`;
  } else if (upcomingAdvisories.length > 0) {
    countBadgeText = `${upcomingAdvisories.length} UPCOMING`;
  } else {
    countBadgeText = `${aqiAdvisories.length} BULLETIN`;
  }

  const isMultiAdvisory = totalWeatherCount >= 2;

  return (
    <section
      aria-label="Official Information"
      className="space-y-4 pt-1"
    >
      {/* Section Header */}
      <div
        className="flex items-center justify-between pb-2.5 border-b"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex items-center space-x-2">
          <div
            className="p-1.5 rounded-lg flex items-center justify-center text-sky-400"
            style={{ backgroundColor: 'var(--surface-secondary)' }}
          >
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3
              className="text-xs font-mono font-bold tracking-wider uppercase"
              style={{ color: 'var(--text-primary)' }}
            >
              OFFICIAL INFORMATION
            </h3>
            <p className="text-[11px] font-mono text-zinc-400">
              Authoritative government bulletins · IMD · NDMA SACHET · INCOIS · CPCB
            </p>
          </div>
        </div>

        <span
          className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border tracking-wider"
          style={{
            backgroundColor: activeAdvisories.length > 0 ? 'rgba(244,63,94,0.12)' : 'var(--surface-secondary)',
            borderColor: activeAdvisories.length > 0 ? 'rgba(244,63,94,0.30)' : 'var(--border-subtle)',
            color: activeAdvisories.length > 0 ? '#f43f5e' : 'var(--text-secondary)',
          }}
        >
          {countBadgeText}
        </span>
      </div>

      {/* 1. Air Quality Intelligence (Strictly separated from storm/weather warnings) */}
      {aqiAdvisories.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center space-x-1.5 text-xs font-mono font-semibold" style={{ color: 'var(--text-secondary)' }}>
            <Wind className="w-3.5 h-3.5 text-amber-400" />
            <span>AIR QUALITY BULLETIN</span>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {aqiAdvisories.map((aqiAdv) => (
              <AirQualityCard key={aqiAdv.id} advisory={aqiAdv} />
            ))}
          </div>
        </div>
      )}

      {/* 2. Weather Advisories (Active & Upcoming) */}
      {totalWeatherCount > 0 && (
        <div className="space-y-3.5">
          {/* Active Advisories Group */}
          {activeAdvisories.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-1.5 text-xs font-mono font-semibold" style={{ color: '#10b981' }}>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>ACTIVE ADVISORIES NOW</span>
              </div>

              {isMultiAdvisory && !isMultiExpanded ? (
                /* Compact scannable list item */
                <div
                  className="rounded-2xl border divide-y overflow-hidden"
                  style={{
                    backgroundColor: 'var(--surface-secondary)',
                    borderColor: 'var(--border-subtle)',
                  }}
                >
                  {activeAdvisories.map((adv) => {
                    const isPromoted = promotedAdvisoryIds.includes(adv.id);
                    return (
                      <div
                        key={adv.id}
                        className="p-3 sm:p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 transition-colors hover:bg-white/[0.02]"
                        style={{ borderColor: 'var(--border-subtle)' }}
                      >
                        <div className="flex items-center space-x-2.5 min-w-0">
                          <AdvisorySeverityBadge severity={adv.severity} officialLevel={adv.official_level} size="sm" />
                          <div className="min-w-0">
                            <h4 className="text-xs sm:text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                              {adv.headline}
                            </h4>
                            <span className="text-[11px] font-mono text-zinc-400 block truncate">
                              {adv.authority.toUpperCase()} · {adv.district ? `${adv.district} · ` : ''}
                              {adv.expires_at ? `Valid until ${new Date(adv.expires_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}` : ''}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
                          {adv.source_url && (
                            <a
                              href={adv.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={`Open official source bulletin from ${adv.authority} in a new tab`}
                              className="inline-flex items-center gap-1 text-[11px] font-mono text-[var(--accent-primary)] hover:underline cursor-pointer"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <span className="hidden sm:inline">Official Source</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}

                          {isPromoted ? (
                            <span
                              className="text-[10px] font-mono px-2 py-0.5 rounded border whitespace-nowrap"
                              style={{
                                backgroundColor: 'rgba(244,63,94,0.08)',
                                borderColor: 'rgba(244,63,94,0.25)',
                                color: '#f43f5e',
                              }}
                            >
                              Surfaced in alert banner ↑
                            </span>
                          ) : (
                            <span
                              className="text-[10px] font-mono px-2 py-0.5 rounded-full border whitespace-nowrap"
                              style={{
                                backgroundColor: 'rgba(16,185,129,0.10)',
                                borderColor: 'rgba(16,185,129,0.25)',
                                color: '#10b981',
                              }}
                            >
                              ACTIVE NOW
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Full cards (Single advisory or Multi-advisory Expanded) */
                <div className="grid grid-cols-1 gap-3">
                  {activeAdvisories.map((adv) => (
                    <OfficialAdvisoryCard
                      key={adv.id}
                      advisory={adv}
                      isPromotedAbove={promotedAdvisoryIds.includes(adv.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Upcoming Advisories Group */}
          {upcomingAdvisories.length > 0 && (
            <div className="space-y-2 opacity-90">
              <div className="flex items-center space-x-1.5 text-xs font-mono font-semibold" style={{ color: 'var(--text-muted)' }}>
                <Clock className="w-3.5 h-3.5 text-zinc-400" />
                <span>UPCOMING WATCHES & ADVANCE ALERTS</span>
              </div>

              {isMultiAdvisory && !isMultiExpanded ? (
                /* Compact scannable list item */
                <div
                  className="rounded-2xl border divide-y overflow-hidden"
                  style={{
                    backgroundColor: 'var(--surface-secondary)',
                    borderColor: 'var(--border-subtle)',
                  }}
                >
                  {upcomingAdvisories.map((adv) => (
                    <div
                      key={adv.id}
                      className="p-3 sm:p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 opacity-85 transition-colors hover:bg-white/[0.02]"
                      style={{ borderColor: 'var(--border-subtle)' }}
                    >
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <AdvisorySeverityBadge severity={adv.severity} officialLevel={adv.official_level} size="sm" />
                        <div className="min-w-0">
                          <h4 className="text-xs sm:text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                            {adv.headline}
                          </h4>
                          <span className="text-[11px] font-mono text-zinc-400 block truncate">
                            {adv.authority.toUpperCase()} · {adv.district ? `${adv.district} · ` : ''}
                            {adv.effective_at ? `Starts ${new Date(adv.effective_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}` : ''}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
                        {adv.source_url && (
                          <a
                            href={adv.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Open official source bulletin from ${adv.authority} in a new tab`}
                            className="inline-flex items-center gap-1 text-[11px] font-mono text-[var(--accent-primary)] hover:underline cursor-pointer"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span className="hidden sm:inline">Official Source</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}

                        <span
                          className="text-[10px] font-mono px-2 py-0.5 rounded-full border whitespace-nowrap"
                          style={{
                            backgroundColor: 'rgba(234,179,8,0.10)',
                            borderColor: 'rgba(234,179,8,0.25)',
                            color: '#eab308',
                          }}
                        >
                          UPCOMING
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                /* Full cards (Single advisory or Multi-advisory Expanded) */
                <div className="grid grid-cols-1 gap-3">
                  {upcomingAdvisories.map((adv) => (
                    <OfficialAdvisoryCard key={adv.id} advisory={adv} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Multi-advisory Disclosure Toggle */}
          {isMultiAdvisory && (
            <div className="flex justify-center pt-1">
              <button
                type="button"
                onClick={() => setIsMultiExpanded(!isMultiExpanded)}
                aria-expanded={isMultiExpanded}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-medium border transition-colors cursor-pointer"
                style={{
                  backgroundColor: 'var(--surface-secondary)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--text-primary)',
                }}
              >
                <span>
                  {isMultiExpanded
                    ? 'Collapse official advisories'
                    : `View all official advisories (${totalWeatherCount})`}
                </span>
                {isMultiExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

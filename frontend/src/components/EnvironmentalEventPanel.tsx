import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Calendar, Activity, Info, CheckCircle2, Clock, ShieldAlert, Wind } from 'lucide-react';

import { EnvironmentalEvent, EnvironmentalPressureItem } from '../types/weather';
import { OfficialAdvisory } from '../types/advisory';
import { OfficialAdvisoryCard } from './advisory/OfficialAdvisoryCard';
import { AirQualityCard } from './advisory/AirQualityCard';
import { useTheme } from '../context/ThemeContext';

interface EnvironmentalEventPanelProps {
  events?: EnvironmentalEvent[];
  advisories?: OfficialAdvisory[];
  isOpen: boolean;
  onClose: () => void;
  locationName?: string;
}

function formatPressureLabel(type: string): string {
  const map: Record<string, string> = {
    traffic: 'Vehicular Traffic',
    noise_pollution: 'Noise Level',
    air_pollution: 'Air Quality / Smoke',
    public_activity: 'Crowd Density',
    congestion: 'Road Congestion',
  };
  return map[type] ?? type.replace(/_/g, ' ');
}

function formatEvidenceLabel(evidence: string): string {
  const map: Record<string, string> = {
    historical_pattern: 'Historical Pattern',
    observed: 'Observed Data',
    authoritative: 'Authoritative Source',
  };
  return map[evidence] ?? evidence.replace(/_/g, ' ');
}

function formatStartDate(isoDate: string): string {
  try {
    const [year, month, day] = isoDate.split('-').map(Number);
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return isoDate;
  }
}

function getStatusBadgeStyle(
  status?: string,
  daysUntil?: number,
  isVandal = false
): { label: string; color: string; bg: string; border: string } {
  if (status === 'active') {
    return {
      label: 'ACTIVE EVENT NOW',
      color: '#34d399',
      bg: 'rgba(52,211,153,0.12)',
      border: 'rgba(52,211,153,0.30)',
    };
  }
  if (status === 'post_event') {
    return {
      label: 'POST-EVENT ACTIVITY ELEVATED',
      color: '#fbbf24',
      bg: 'rgba(251,191,36,0.12)',
      border: 'rgba(251,191,36,0.30)',
    };
  }
  // UPCOMING status: Vandal uses supporting orange; all other themes use sky blue.
  const upcomingColor = isVandal ? '#fb923c' : '#38bdf8';
  const upcomingBgAlpha = isVandal ? 'rgba(251,146,60,0.12)' : 'rgba(56,189,248,0.12)';
  const upcomingBorderAlpha = isVandal ? 'rgba(251,146,60,0.30)' : 'rgba(56,189,248,0.30)';
  return {
    label: `UPCOMING IN ${daysUntil ?? 0} DAYS`,
    color: upcomingColor,
    bg: upcomingBgAlpha,
    border: upcomingBorderAlpha,
  };
}

export const EnvironmentalEventPanel: React.FC<EnvironmentalEventPanelProps> = ({
  events = [],
  advisories = [],
  isOpen,
  onClose,
  locationName: _locationName,
}) => {
  const { darkVariant } = useTheme();
  const isVandal = darkVariant === 'vandal';

  // Derive theme-adaptive accent for non-severity chrome elements.
  // Atheris = sky blue, Vandal = neon red, Night = amber, Light = emerald.
  // We use var(--accent) which already resolves to the correct per-theme value.

  // Separate AQI advisories from general weather advisories
  const aqiAdvisories = advisories.filter(
    (a) => a.hazard_type === 'AIR_QUALITY' || a.authority.toUpperCase() === 'CPCB'
  );
  const weatherAdvisories = advisories.filter(
    (a) => a.hazard_type !== 'AIR_QUALITY' && a.authority.toUpperCase() !== 'CPCB'
  );

  // Active tab selection
  const [activeTab, setActiveTab] = useState<'advisories' | 'aqi' | 'civic'>(() => {
    if (weatherAdvisories.length > 0) return 'advisories';
    if (aqiAdvisories.length > 0) return 'aqi';
    return 'civic';
  });

  if (!isOpen) return null;

  const allUpcoming = events.every((e) => e.status === 'upcoming');

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.98 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-2xl mx-auto p-5 rounded-3xl shadow-2xl border space-y-4 my-3"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: 'var(--border-muted)' }}>
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg" style={{ backgroundColor: 'var(--surface-input)', color: 'var(--accent)' }}>
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Official & Environmental Information
              </h3>
              <span className="text-[11px] font-mono text-zinc-400 block">
                Official advisories, air quality, and regional civic periods
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close Environmental Intelligence Panel"
            className="p-1.5 rounded-lg transition-colors cursor-pointer"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface)';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
            }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Segmented Navigation Tabs */}
        <div className="flex items-center space-x-1 p-1 rounded-xl border font-mono text-xs" style={{ backgroundColor: 'var(--surface-input)', borderColor: 'var(--border-muted)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('advisories')}
            className={`flex-1 py-1.5 px-2 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
              activeTab === 'advisories'
                ? 'shadow-xs'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            style={{
              backgroundColor: activeTab === 'advisories' ? 'var(--surface-elevated)' : 'transparent',
              color: activeTab === 'advisories' ? 'var(--accent)' : undefined,
              border: activeTab === 'advisories' ? '1px solid var(--border)' : '1px solid transparent',
            }}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Official Advisories</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full border opacity-80" style={{ borderColor: 'var(--border-muted)' }}>
              {weatherAdvisories.length}
            </span>
          </button>

          {aqiAdvisories.length > 0 && (
            <button
              type="button"
              onClick={() => setActiveTab('aqi')}
              className={`flex-1 py-1.5 px-2 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                activeTab === 'aqi'
                  ? 'shadow-xs'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
              style={{
                backgroundColor: activeTab === 'aqi' ? 'var(--surface-elevated)' : 'transparent',
                color: activeTab === 'aqi' ? 'var(--accent)' : undefined,
                border: activeTab === 'aqi' ? '1px solid var(--border)' : '1px solid transparent',
              }}
            >
              <Wind className="w-3.5 h-3.5" />
              <span>Air Quality</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full border opacity-80" style={{ borderColor: 'var(--border-muted)' }}>
                {aqiAdvisories.length}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setActiveTab('civic')}
            className={`flex-1 py-1.5 px-2 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
              activeTab === 'civic'
                ? 'shadow-xs'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            style={{
              backgroundColor: activeTab === 'civic' ? 'var(--surface-elevated)' : 'transparent',
              color: activeTab === 'civic' ? 'var(--accent)' : undefined,
              border: activeTab === 'civic' ? '1px solid var(--border)' : '1px solid transparent',
            }}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Civic & Events</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full border opacity-80" style={{ borderColor: 'var(--border-muted)' }}>
              {events.length}
            </span>
          </button>
        </div>

        {/* TAB 1: OFFICIAL ADVISORIES */}
        {activeTab === 'advisories' && (
          <div className="space-y-3">
            <div className="text-[11px] font-mono text-zinc-400 px-1">
              Authoritative government warnings issued by IMD, NDMA, and INCOIS.
            </div>

            {weatherAdvisories.length === 0 ? (
              <div
                className="p-6 rounded-2xl border text-center space-y-2"
                style={{
                  backgroundColor: 'var(--surface)',
                  borderColor: 'var(--border-muted)',
                }}
              >
                <div className="w-8 h-8 rounded-full flex items-center justify-center mx-auto text-zinc-400" style={{ backgroundColor: 'var(--surface-input)' }}>
                  <Info className="w-4 h-4" />
                </div>
                <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                  No active official advisories are currently available for this location.
                </p>
                <p className="text-[11px] max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
                  Official advisories appear here when available from configured sources.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {weatherAdvisories.map((adv) => (
                  <OfficialAdvisoryCard key={adv.id} advisory={adv} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: AIR QUALITY */}
        {activeTab === 'aqi' && (
          <div className="space-y-3">
            <div className="text-[11px] font-mono text-zinc-400 px-1">
              National Air Quality Index (NAQI) continuous bulletins from Central Pollution Control Board (CPCB).
            </div>
            {aqiAdvisories.map((aqiAdv) => (
              <AirQualityCard key={aqiAdv.id} advisory={aqiAdv} />
            ))}
          </div>
        )}

        {/* TAB 3: CIVIC & REGIONAL EVENTS (Existing Preserved System) */}
        {activeTab === 'civic' && (
          <div className="space-y-3">
            <div className="text-[11px] font-mono text-zinc-400 px-1">
              StormOps-curated intelligence on regional festivals, cultural gatherings, and local pressure periods.
            </div>

            {allUpcoming && (
              <div
                className="flex items-center gap-2 px-3 py-2 rounded-xl border"
                style={{
                  backgroundColor: isVandal ? 'rgba(251,146,60,0.06)' : 'rgba(56,189,248,0.06)',
                  borderColor: isVandal ? 'rgba(251,146,60,0.18)' : 'rgba(56,189,248,0.18)',
                }}
              >
                <Clock className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
                <div>
                  <span className="text-[10px] font-mono font-semibold uppercase tracking-wider block" style={{ color: 'var(--accent)' }}>
                    Upcoming Environmental Periods
                  </span>
                  <span className="text-[10px] font-mono text-zinc-400">
                    Next 60 days · Known event advisories
                  </span>
                </div>
              </div>
            )}

            {events.length === 0 ? (
              <div
                className="p-6 rounded-2xl border text-center space-y-2"
                style={{
                  backgroundColor: 'var(--surface)',
                  borderColor: 'var(--border-muted)',
                }}
              >
                <div className="w-8 h-8 rounded-full flex items-center justify-center mx-auto text-zinc-400" style={{ backgroundColor: 'var(--surface-input)' }}>
                  <Calendar className="w-4 h-4" />
                </div>
                <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                  No civic or environmental events currently catalogued for this region.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {events.map((event) => {
                  const statusStyle = getStatusBadgeStyle(event.status, event.days_until, isVandal);
                  const occurrence = event.occurrences && event.occurrences.length > 0 ? event.occurrences[0] : null;

                  return (
                    <div
                      key={event.id}
                      className="p-4 rounded-2xl border space-y-3"
                      style={{
                        backgroundColor: 'var(--surface)',
                        borderColor: 'var(--border-muted)',
                      }}
                    >
                      {/* Event Title & Badges */}
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                        <div>
                          <span className="text-[10px] font-mono uppercase tracking-wider font-semibold block" style={{ color: 'var(--accent)' }}>
                            {event.category} event · StormOps Curated
                          </span>
                          <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {event.title}
                          </h4>
                        </div>

                        <div className="flex flex-col items-start sm:items-end gap-1 self-start">
                          <span
                            className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border whitespace-nowrap"
                            style={{
                              backgroundColor: statusStyle.bg,
                              borderColor: statusStyle.border,
                              color: statusStyle.color,
                            }}
                          >
                            {statusStyle.label}
                          </span>
                          {event.status === 'upcoming' && occurrence && (
                            <span className="text-[10px] font-mono text-zinc-400">
                              Starts {formatStartDate(occurrence.start_date)}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Event Dates */}
                      {occurrence && (
                        <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400">
                          <Calendar className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
                          <span>
                            {occurrence.start_date} to {occurrence.end_date} ({occurrence.year})
                          </span>
                        </div>
                      )}

                      {/* Environmental Pressures Tags */}
                      {event.environmental_pressures && event.environmental_pressures.length > 0 && (
                        <div className="space-y-1 pt-1">
                          <span className="text-[10px] font-mono uppercase text-zinc-400 block">
                            Associated Environmental Pressures:
                          </span>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {event.environmental_pressures.map((item: EnvironmentalPressureItem, idx: number) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded text-[10px] font-mono flex items-center gap-1 border"
                                style={{
                                  backgroundColor: 'var(--surface-elevated)',
                                  borderColor: 'var(--border-muted)',
                                  color: 'var(--text-primary)',
                                }}
                              >
                                <span className="font-semibold">{formatPressureLabel(item.type)}</span>
                                <span className="text-zinc-400">({formatEvidenceLabel(item.evidence_type)})</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Advisory Summary */}
                      <p className="text-xs leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                        {event.advisory_summary}
                      </p>

                      {/* Recommendations */}
                      {event.key_recommendations && event.key_recommendations.length > 0 && (
                        <div className="space-y-1 pt-1 border-t" style={{ borderColor: 'var(--border-muted)' }}>
                          <span className="text-[10px] font-mono uppercase text-zinc-400 block">
                            STORMOPS IMPACT INSIGHT:
                          </span>
                          <ul className="space-y-1">
                            {event.key_recommendations.map((rec, rIdx) => (
                              <li key={rIdx} className="text-xs flex items-start gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                                <span>{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Source Metadata Citation */}
                      <div className="text-[10px] font-mono text-zinc-500 pt-1 flex items-center gap-1">
                        <Info className="w-3 h-3 text-zinc-400" />
                        <span>Source: {event.source_metadata}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

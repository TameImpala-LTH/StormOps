import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Calendar, Activity, Info, CheckCircle2, Clock } from 'lucide-react';

import { EnvironmentalEvent, EnvironmentalPressureItem } from '../types/weather';

interface EnvironmentalEventPanelProps {
  events: EnvironmentalEvent[];
  isOpen: boolean;
  onClose: () => void;
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

/**
 * Phase 10B: Format an ISO date string (YYYY-MM-DD) into a human-readable label.
 * e.g. "2026-10-16" → "Oct 16, 2026"
 */
function formatStartDate(isoDate: string): string {
  try {
    const [year, month, day] = isoDate.split('-').map(Number);
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return isoDate;
  }
}

function getStatusBadgeStyle(status?: string, daysUntil?: number): { label: string; color: string; bg: string; border: string } {
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
  return {
    label: `UPCOMING IN ${daysUntil ?? 0} DAYS`,
    color: '#38bdf8',
    bg: 'rgba(56,189,248,0.12)',
    border: 'rgba(56,189,248,0.30)',
  };
}

export const EnvironmentalEventPanel: React.FC<EnvironmentalEventPanelProps> = ({
  events,
  isOpen,
  onClose,
}) => {
  if (!events || events.length === 0 || !isOpen) return null;

  // Phase 10B: Show outlook framing header when ALL events are upcoming (none active/post_event).
  const allUpcoming = events.every((e) => e.status === 'upcoming');

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.98 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-lg mx-auto p-5 rounded-3xl shadow-2xl border space-y-4 my-3"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: 'var(--border-muted)' }}>
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg text-sky-400" style={{ backgroundColor: 'var(--surface-input)' }}>
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Environmental Awareness Outlook
              </h3>
              <span className="text-[11px] font-mono text-zinc-400 block">
                Evidence-based regional event advisories
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close Environmental Panel"
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

        {/* Phase 10B: Upcoming Environmental Periods framing header */}
        {allUpcoming && (
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-xl border"
            style={{
              backgroundColor: 'rgba(56,189,248,0.06)',
              borderColor: 'rgba(56,189,248,0.18)',
            }}
          >
            <Clock className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
            <div>
              <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-sky-400 block">
                Upcoming Environmental Periods
              </span>
              <span className="text-[10px] font-mono text-zinc-400">
                Next 60 days · Known event advisories
              </span>
            </div>
          </div>
        )}

        {/* Event List */}
        <div className="space-y-4">
          {events.map((event) => {
            const statusStyle = getStatusBadgeStyle(event.status, event.days_until);
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
                    <span className="text-[10px] font-mono uppercase tracking-wider text-sky-400 font-semibold block">
                      {event.category} event
                    </span>
                    <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {event.title}
                    </h4>
                  </div>

                  {/* Status badge + Phase 10B start-date secondary label */}
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
                    {/* Phase 10B: Show "Starts [date]" beneath the badge for upcoming events */}
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
                    <Calendar className="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
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
                      Practical Considerations:
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
      </motion.div>
    </AnimatePresence>
  );
};

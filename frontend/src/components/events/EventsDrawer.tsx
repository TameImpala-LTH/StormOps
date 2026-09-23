import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Calendar, MapPin, Activity, CheckCircle2, Info } from 'lucide-react';
import { EnvironmentalEvent } from '../../types/weather';

export interface EventsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  events?: EnvironmentalEvent[];
  onSelectLocation?: (locationName: string) => void;
  activeLocationName?: string | null;
}

export const EventsDrawer: React.FC<EventsDrawerProps> = ({
  isOpen,
  onClose,
  events = [],
  onSelectLocation,
  activeLocationName,
}) => {
  // Close drawer on Escape key press
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs transition-opacity"
            aria-hidden="true"
          />

          {/* Slide-over Drawer (Desktop & Mobile) */}
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-label="Events and Regional Information"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed top-0 bottom-0 right-0 z-50 w-full sm:w-[420px] md:w-[460px] flex flex-col shadow-2xl border-l"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-primary)',
            }}
          >
            {/* Header */}
            <div
              className="p-4 sm:p-5 flex items-start justify-between border-b"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                  <h2
                    className="text-xs font-mono uppercase tracking-wider font-semibold"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    Events &amp; Information
                  </h2>
                </div>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Regional cultural gatherings, festivals &amp; environmental pressure windows
                </p>
              </div>

              <button
                type="button"
                onClick={onClose}
                aria-label="Close events panel"
                className="p-1.5 rounded-lg border transition-colors hover:opacity-80 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
                style={{
                  backgroundColor: 'var(--surface-secondary)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--text-secondary)',
                }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
              {events.length === 0 ? (
                /* Quiet Empty State (No "All Clear", no giant banners) */
                <div
                  className="p-6 rounded-xl border border-dashed text-center space-y-2.5 my-6"
                  style={{
                    borderColor: 'var(--border-subtle)',
                    backgroundColor: 'var(--surface-primary)',
                  }}
                  data-testid="events-empty-state"
                >
                  <Calendar
                    className="w-6 h-6 mx-auto opacity-50"
                    style={{ color: 'var(--text-tertiary)' }}
                  />
                  <div className="space-y-1">
                    <p
                      className="text-xs font-medium"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      No regional events or scheduled disruptions currently catalogued for this area.
                    </p>
                    <p
                      className="text-[11px] leading-relaxed"
                      style={{ color: 'var(--text-tertiary)' }}
                    >
                      Event intelligence monitors major verified regional festivals, procession routes, and civic periods across Indian meteorological zones.
                    </p>
                  </div>
                </div>
              ) : (
                /* Verified Event Cards */
                events.map((ev) => {
                  const occurrence = ev.occurrences?.[0];
                  const dateStr = occurrence
                    ? `${occurrence.start_date} to ${occurrence.end_date}`
                    : 'Upcoming 2026';

                  return (
                    <article
                      key={ev.id}
                      className="p-4 rounded-xl border space-y-3 transition-colors"
                      style={{
                        backgroundColor: 'var(--surface-primary)',
                        borderColor: 'var(--border-subtle)',
                      }}
                      data-testid={`event-card-${ev.id}`}
                    >
                      {/* Category & Status Row */}
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span
                          className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider font-semibold border"
                          style={{
                            backgroundColor: 'var(--surface-secondary)',
                            borderColor: 'var(--border-subtle)',
                            color: 'var(--accent-primary)',
                          }}
                        >
                          {ev.category || 'Regional Event'}
                        </span>

                        {ev.days_until !== undefined && (
                          <span
                            className="text-[10px] font-mono tracking-wider"
                            style={{ color: 'var(--text-tertiary)' }}
                          >
                            {ev.days_until === 0
                              ? 'Active Today'
                              : ev.days_until > 0
                              ? `Starts in ${ev.days_until} days`
                              : 'Recent Event'}
                          </span>
                        )}
                      </div>

                      {/* Event Title */}
                      <h3
                        className="text-sm sm:text-base font-semibold tracking-tight"
                        style={{ color: 'var(--text-primary)' }}
                      >
                        {ev.title}
                      </h3>

                      {/* Date Span */}
                      <div
                        className="flex items-center gap-1.5 text-xs font-mono"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        <Calendar className="w-3.5 h-3.5 flex-shrink-0 opacity-70" />
                        <span>{dateStr}</span>
                      </div>

                      {/* Summary */}
                      {ev.advisory_summary && (
                        <p
                          className="text-xs leading-relaxed"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {ev.advisory_summary}
                        </p>
                      )}

                      {/* Environmental Pressures */}
                      {ev.environmental_pressures && ev.environmental_pressures.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <span
                            className="text-[10px] font-mono uppercase tracking-wider block"
                            style={{ color: 'var(--text-tertiary)' }}
                          >
                            Associated Pressures:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {ev.environmental_pressures.map((p, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono border"
                                style={{
                                  backgroundColor: 'var(--surface-secondary)',
                                  borderColor: 'var(--border-subtle)',
                                  color: 'var(--text-secondary)',
                                }}
                              >
                                <Activity className="w-2.5 h-2.5 opacity-60" />
                                <span className="capitalize">{p.type.replace(/_/g, ' ')}:</span>
                                <span className="font-semibold uppercase">{p.level}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Affected Locations — The Core Event -> Location -> WeatherGPT workflow */}
                      {ev.geographic_scope && ev.geographic_scope.length > 0 && (
                        <div className="space-y-2 pt-2 border-t" style={{ borderColor: 'var(--border-subtle)' }}>
                          <div className="flex items-center gap-1.5">
                            <MapPin
                              className="w-3.5 h-3.5 flex-shrink-0"
                              style={{ color: 'var(--accent-primary)' }}
                            />
                            <span
                              className="text-xs font-medium"
                              style={{ color: 'var(--text-primary)' }}
                            >
                              Affected Locations
                            </span>
                          </div>
                          <p
                            className="text-[11px]"
                            style={{ color: 'var(--text-tertiary)' }}
                          >
                            Select a location to inspect its WeatherGPT forecast:
                          </p>

                          <div className="flex flex-wrap gap-1.5">
                            {ev.geographic_scope.map((locName) => {
                              const isActive =
                                activeLocationName?.toLowerCase() === locName.toLowerCase();
                              return (
                                <button
                                  key={locName}
                                  type="button"
                                  onClick={() => onSelectLocation?.(locName)}
                                  aria-label={`View WeatherGPT forecast for ${locName}`}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
                                  style={{
                                    backgroundColor: isActive
                                      ? 'var(--surface-elevated)'
                                      : 'var(--surface-secondary)',
                                    borderColor: isActive
                                      ? 'var(--accent-primary)'
                                      : 'var(--border-subtle)',
                                    color: isActive
                                      ? 'var(--accent-primary)'
                                      : 'var(--text-primary)',
                                  }}
                                >
                                  <MapPin className="w-3 h-3 flex-shrink-0 opacity-70" />
                                  <span>{locName}</span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Key Recommendations */}
                      {ev.key_recommendations && ev.key_recommendations.length > 0 && (
                        <div className="space-y-1 pt-1">
                          <span
                            className="text-[10px] font-mono uppercase tracking-wider block"
                            style={{ color: 'var(--text-tertiary)' }}
                          >
                            Guidance:
                          </span>
                          <ul className="space-y-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                            {ev.key_recommendations.map((rec, rIdx) => (
                              <li key={rIdx} className="flex items-start gap-1.5">
                                <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 opacity-60 text-emerald-500" />
                                <span className="leading-snug">{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Source attribution */}
                      {ev.source_metadata && (
                        <div
                          className="pt-2 text-[10px] font-mono flex items-center gap-1 border-t"
                          style={{
                            borderColor: 'var(--border-subtle)',
                            color: 'var(--text-tertiary)',
                          }}
                        >
                          <Info className="w-3 h-3 flex-shrink-0 opacity-60" />
                          <span>Source: {ev.source_metadata}</span>
                        </div>
                      )}
                    </article>
                  );
                })
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

import React from 'react';
import { Calendar, MapPin, AlertCircle, Sparkles } from 'lucide-react';
import { EnvironmentalOutlookItem } from '../../types/auth';

interface EnvironmentalOutlookProps {
  items: EnvironmentalOutlookItem[];
  locationsEvaluated: string[];
  isLoading: boolean;
  isAuthenticated: boolean;
  onOpenAuthModal?: () => void;
  onSelectLocation?: (locationName: string) => void;
}

function formatStartDate(isoDate: string): string {
  try {
    const [year, month, day] = isoDate.split('-').map(Number);
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  } catch {
    return isoDate;
  }
}

function formatPressureLabel(type: string): string {
  const map: Record<string, string> = {
    traffic: 'Traffic',
    noise_pollution: 'Noise',
    air_pollution: 'Smoke / Air',
    public_activity: 'Crowd Density',
    congestion: 'Congestion',
  };
  return map[type] ?? type.replace(/_/g, ' ');
}

export const EnvironmentalOutlook: React.FC<EnvironmentalOutlookProps> = ({
  items,
  locationsEvaluated,
  isLoading,
  isAuthenticated,
  onOpenAuthModal,
  onSelectLocation,
}) => {
  // Empty State 1: Anonymous User
  if (!isAuthenticated) {
    return (
      <div className="py-8 px-4 text-center">
        <div className="w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-3 bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Calendar className="w-5 h-5" />
        </div>
        <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
          Sign in to build your Environmental Outlook.
        </p>
        <p className="text-[11px] mt-1.5 mb-4 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Get deterministic, evidence-based alerts for known regional festivals and environmental pressure periods across your saved cities.
        </p>
        {onOpenAuthModal && (
          <button
            type="button"
            onClick={onOpenAuthModal}
            className="w-full py-2.5 rounded-xl text-xs font-medium transition-all cursor-pointer shadow-xs"
            style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }}
          >
            Sign In
          </button>
        )}
      </div>
    );
  }

  // Loading State
  if (isLoading) {
    return (
      <div className="py-8 px-4 text-center">
        <div className="animate-spin w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Evaluating environmental periods...
        </p>
      </div>
    );
  }

  // Empty State 2: No Saved Locations
  if (locationsEvaluated.length === 0) {
    return (
      <div className="py-8 px-4 text-center">
        <MapPin className="w-8 h-8 mx-auto mb-2 opacity-30 text-zinc-400" />
        <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
          Save locations to build your Environmental Outlook.
        </p>
        <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
          Star your favorite cities or query weather to see verified upcoming local environmental periods.
        </p>
      </div>
    );
  }

  // Empty State 3: Saved Locations Evaluated, but No Relevant Events
  if (items.length === 0) {
    return (
      <div className="py-8 px-4 text-center">
        <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-30 text-zinc-400" />
        <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
          No upcoming environmental periods for your saved locations.
        </p>
        <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
          No major verified festival or environmental pressure periods are scheduled within the next 60 days for {locationsEvaluated.join(', ')}.
        </p>
      </div>
    );
  }

  // Chronological Outlook Cards
  return (
    <div className="space-y-3 pb-2">
      <div className="flex items-center justify-between px-1">
        <span
          className="text-[10px] font-semibold tracking-wider uppercase opacity-60"
          style={{ color: 'var(--text-muted)' }}
        >
          Environmental Outlook
        </span>
        <span className="text-[10px] font-mono opacity-50" style={{ color: 'var(--text-muted)' }}>
          {items.length} {items.length === 1 ? 'Period' : 'Periods'}
        </span>
      </div>

      <div className="space-y-2.5">
        {items.map((item) => {
          const isActive = item.status === 'active';
          const isUpcoming = item.status === 'upcoming';

          return (
            <div
              key={`${item.event_id}-${item.location_name}`}
              className="p-3 rounded-xl border text-xs space-y-2 transition-all"
              style={{
                backgroundColor: 'var(--surface-elevated)',
                borderColor: isActive ? 'rgba(52, 211, 153, 0.35)' : 'var(--border-muted)',
              }}
            >
              {/* Header: Location & Status */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  <MapPin className="w-3.5 h-3.5 shrink-0 opacity-70" style={{ color: 'var(--accent)' }} />
                  <button
                    type="button"
                    onClick={() => onSelectLocation && onSelectLocation(item.location_name)}
                    className="font-semibold truncate hover:underline cursor-pointer text-left"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {item.location_name}
                  </button>
                </div>

                <span
                  className={`text-[9px] px-2 py-0.5 rounded-full uppercase font-mono font-medium shrink-0 border ${
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : isUpcoming
                      ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {isActive
                    ? 'Active Now'
                    : isUpcoming
                    ? item.days_until !== null && item.days_until !== undefined
                      ? `In ${item.days_until}d`
                      : 'Upcoming'
                    : 'Post-Event'}
                </span>
              </div>

              {/* Event Title & Dates */}
              <div>
                <div className="font-medium text-amber-300 text-[13px] tracking-tight">
                  {item.event_title}
                </div>
                <div className="text-[11px] font-mono mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  {item.start_date && (
                    <>
                      {isActive ? 'Ongoing until ' : 'Starts '}
                      {formatStartDate(item.end_date || item.start_date)}
                    </>
                  )}
                </div>
              </div>

              {/* Advisory description */}
              <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                {item.advisory_summary}
              </p>

              {/* Evidence-based note (no prediction) */}
              <div className="flex items-center gap-1 text-[10px] italic font-medium text-zinc-400">
                <AlertCircle className="w-3 h-3 text-amber-400/80 shrink-0" />
                <span>{item.evidence_note}</span>
              </div>

              {/* Pressure Pills */}
              {item.environmental_pressures.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {item.environmental_pressures.map((p, idx) => (
                    <span
                      key={idx}
                      className="text-[9px] px-1.5 py-0.5 rounded-md font-mono border"
                      style={{
                        backgroundColor: 'var(--bg)',
                        borderColor: 'var(--border-muted)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      {formatPressureLabel(p.type)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

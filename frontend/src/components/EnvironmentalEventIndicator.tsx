import React from 'react';
import { ShieldAlert, Calendar } from 'lucide-react';
import { EnvironmentalEvent } from '../types/weather';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../types/advisory';

interface EnvironmentalEventIndicatorProps {
  events?: EnvironmentalEvent[];
  advisories?: OfficialAdvisory[];
  isOpen: boolean;
  onToggle: () => void;
}

export const EnvironmentalEventIndicator: React.FC<EnvironmentalEventIndicatorProps> = ({
  events = [],
  advisories = [],
  isOpen,
  onToggle,
}) => {
  const eventCount = events.length;
  // Exclude expired advisories from indicator count
  const unexpiredAdvisories = advisories.filter((a) => getAdvisoryTemporalState(a) !== 'EXPIRED');
  const advisoryCount = unexpiredAdvisories.length;
  const totalCount = eventCount + advisoryCount;

  if (totalCount === 0) return null;

  // Check for severe official advisories (Red or Orange currently active)
  const hasSevereAdvisory = unexpiredAdvisories.some((a) => {
    const sev = (a.severity || '').toLowerCase();
    return getAdvisoryTemporalState(a) === 'ACTIVE' && (sev === 'red' || sev === 'orange');
  });

  const hasActiveAdvisory = unexpiredAdvisories.some((a) => getAdvisoryTemporalState(a) === 'ACTIVE');

  const tooltipLabel = [
    advisoryCount > 0 ? `${advisoryCount} Official ${advisoryCount === 1 ? 'Advisory' : 'Advisories'}` : '',
    eventCount > 0 ? `${eventCount} Civic ${eventCount === 1 ? 'Event' : 'Events'}` : '',
  ]
    .filter(Boolean)
    .join(' · ');

  // Severe warning styling: official red (#f43f5e) immutable across themes
  if (hasSevereAdvisory) {
    return (
      <button
        type="button"
        onClick={onToggle}
        title={tooltipLabel}
        aria-label={`Official advisory alert: ${tooltipLabel}`}
        aria-expanded={isOpen}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold transition-all cursor-pointer border"
        style={{
          backgroundColor: isOpen ? 'rgba(244,63,94,0.20)' : 'rgba(244,63,94,0.12)',
          borderColor: 'rgba(244,63,94,0.38)',
          color: '#f43f5e',
        }}
      >
        <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 animate-pulse text-rose-500" />
        <span className="tracking-wider">OFFICIAL</span>
        <span
          className="px-1.5 py-0.2 rounded-full text-[10px] font-bold"
          style={{ backgroundColor: 'rgba(244,63,94,0.22)' }}
        >
          {totalCount}
        </span>
      </button>
    );
  }

  // Active (non-severe) or Upcoming advisory styling: clean, restrained semantic pill
  if (hasActiveAdvisory || advisoryCount > 0) {
    return (
      <button
        type="button"
        onClick={onToggle}
        title={tooltipLabel}
        aria-label={`Official information available: ${tooltipLabel}`}
        aria-expanded={isOpen}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium transition-all cursor-pointer border"
        style={{
          backgroundColor: isOpen ? 'var(--surface-elevated)' : 'var(--surface-secondary)',
          borderColor: isOpen ? 'var(--accent-primary)' : 'var(--border-subtle)',
          color: isOpen ? 'var(--accent-primary)' : 'var(--text-secondary)',
        }}
      >
        <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 opacity-80" />
        <span className="tracking-wider">OFFICIAL</span>
        <span
          className="px-1.5 py-0.2 rounded-full text-[10px] font-bold"
          style={{ backgroundColor: 'var(--surface-elevated)' }}
        >
          {totalCount}
        </span>
      </button>
    );
  }

  // Pure civic/contextual events: quiet contextual badge
  return (
    <button
      type="button"
      onClick={onToggle}
      title={tooltipLabel}
      aria-label={`Contextual civic events: ${tooltipLabel}`}
      aria-expanded={isOpen}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono transition-all cursor-pointer border"
      style={{
        backgroundColor: isOpen ? 'var(--surface-elevated)' : 'var(--surface-secondary)',
        borderColor: isOpen ? 'var(--accent-primary)' : 'var(--border-subtle)',
        color: 'var(--text-secondary)',
      }}
    >
      <Calendar className="w-3.5 h-3.5 flex-shrink-0 opacity-70" />
      <span className="tracking-wider">CIVIC</span>
      <span
        className="px-1.5 py-0.2 rounded-full text-[10px] font-bold"
        style={{ backgroundColor: 'var(--surface-elevated)' }}
      >
        {totalCount}
      </span>
    </button>
  );
};

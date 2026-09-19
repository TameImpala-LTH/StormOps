import React from 'react';
import { Bell, BellRing, ShieldAlert } from 'lucide-react';
import { EnvironmentalEvent } from '../types/weather';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../types/advisory';
import { useTheme } from '../context/ThemeContext';

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
  const { darkVariant } = useTheme();
  const isVandal = darkVariant === 'vandal';

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
  const hasActiveEvent = events.some((e) => e.status === 'active');
  const hasAnyActive = hasActiveAdvisory || hasActiveEvent;

  // Determine icon & styling
  let IconComponent = BellRing;
  let pulseClass = !hasAnyActive && !isOpen ? 'animate-pulse' : '';
  // Severe advisory uses semantic red (#f43f5e) regardless of theme — invariant preserved.
  // Non-severe badge: Vandal = neon red (#ff2a55), Atheris/others = electric blue (#38bdf8).
  let badgeColor = hasSevereAdvisory ? '#f43f5e' : isVandal ? '#ff2a55' : '#38bdf8';
  let badgeTextColor = '#ffffff';

  if (hasSevereAdvisory) {
    IconComponent = ShieldAlert;
    pulseClass = 'animate-pulse';
  } else if (hasAnyActive) {
    IconComponent = Bell;
  }

  const tooltipLabel = [
    advisoryCount > 0 ? `${advisoryCount} Official ${advisoryCount === 1 ? 'Advisory' : 'Advisories'}` : '',
    eventCount > 0 ? `${eventCount} Civic ${eventCount === 1 ? 'Event' : 'Events'}` : '',
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <button
      type="button"
      onClick={onToggle}
      title={tooltipLabel}
      aria-label={tooltipLabel}
      className="relative p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center border"
      style={{
        backgroundColor: isOpen
          ? 'var(--surface-elevated)'
          : hasSevereAdvisory
          ? 'rgba(244,63,94,0.10)'
          : 'var(--surface-input)',
        borderColor: isOpen
          ? 'var(--accent)'
          : hasSevereAdvisory
          ? 'rgba(244,63,94,0.40)'
          : 'var(--border-muted)',
        color: isOpen
          ? 'var(--accent)'
          : hasSevereAdvisory
          ? '#f43f5e'
          : 'var(--text-secondary)',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-elevated)';
        (e.currentTarget as HTMLButtonElement).style.color = hasSevereAdvisory ? '#f43f5e' : 'var(--accent)';
      }}
      onMouseLeave={(e) => {
        if (!isOpen) {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = hasSevereAdvisory
            ? 'rgba(244,63,94,0.10)'
            : 'var(--surface-input)';
          (e.currentTarget as HTMLButtonElement).style.color = hasSevereAdvisory ? '#f43f5e' : 'var(--text-secondary)';
        }
      }}
    >
      <IconComponent className={`w-4 h-4 ${pulseClass}`} />
      <span
        className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[10px] font-mono font-bold flex items-center justify-center shadow-xs"
        style={{
          backgroundColor: badgeColor,
          color: badgeTextColor,
        }}
      >
        {totalCount}
      </span>
    </button>
  );
};

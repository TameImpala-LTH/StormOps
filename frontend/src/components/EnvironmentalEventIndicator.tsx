import React from 'react';
import { Bell, BellRing } from 'lucide-react';
import { EnvironmentalEvent } from '../types/weather';

interface EnvironmentalEventIndicatorProps {
  events: EnvironmentalEvent[];
  isOpen: boolean;
  onToggle: () => void;
}

export const EnvironmentalEventIndicator: React.FC<EnvironmentalEventIndicatorProps> = ({
  events,
  isOpen,
  onToggle,
}) => {
  if (!events || events.length === 0) return null;

  const count = events.length;

  // Phase 10B: Use BellRing with a subtle pulse when all events are upcoming.
  // Use static Bell when any event is currently active.
  const hasActiveEvent = events.some((e) => e.status === 'active');
  const IconComponent = hasActiveEvent ? Bell : BellRing;
  const pulseClass = !hasActiveEvent && !isOpen ? 'animate-pulse' : '';

  return (
    <button
      type="button"
      onClick={onToggle}
      title={`${count} Environmental Event Advisory${count > 1 ? 's' : ''}`}
      aria-label={`${count} Environmental Event Advisory${count > 1 ? 's' : ''}`}
      className="relative p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center border"
      style={{
        backgroundColor: isOpen ? 'var(--surface-elevated)' : 'var(--surface-input)',
        borderColor: isOpen ? 'var(--accent)' : 'var(--border-muted)',
        color: isOpen ? 'var(--accent)' : 'var(--text-secondary)',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-elevated)';
        (e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)';
      }}
      onMouseLeave={(e) => {
        if (!isOpen) {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-input)';
          (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
        }
      }}
    >
      <IconComponent className={`w-4 h-4 ${pulseClass}`} />
      <span
        className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[10px] font-mono font-bold flex items-center justify-center"
        style={{
          backgroundColor: '#38bdf8',
          color: '#090d16',
        }}
      >
        {count}
      </span>
    </button>
  );
};

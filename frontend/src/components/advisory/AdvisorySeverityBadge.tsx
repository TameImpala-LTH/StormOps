import React from 'react';

interface AdvisorySeverityBadgeProps {
  severity: string;
  officialLevel?: string | null;
  size?: 'sm' | 'md';
}

export const AdvisorySeverityBadge: React.FC<AdvisorySeverityBadgeProps> = ({
  severity,
  officialLevel,
  size = 'md',
}) => {
  const sev = (severity || 'unknown').toLowerCase().trim();

  let colors = {
    bg: 'rgba(113,113,122,0.12)',
    border: 'rgba(113,113,122,0.35)',
    text: '#a1a1aa',
    dot: '#71717a',
    defaultLabel: 'ADVISORY',
  };

  switch (sev) {
    case 'red':
      colors = {
        bg: 'rgba(244,63,94,0.12)',
        border: 'rgba(244,63,94,0.35)',
        text: '#f43f5e',
        dot: '#f43f5e',
        defaultLabel: 'RED · WARNING',
      };
      break;
    case 'orange':
      colors = {
        bg: 'rgba(249,115,22,0.12)',
        border: 'rgba(249,115,22,0.35)',
        text: '#f97316',
        dot: '#f97316',
        defaultLabel: 'ORANGE · ALERT',
      };
      break;
    case 'yellow':
      colors = {
        bg: 'rgba(234,179,8,0.12)',
        border: 'rgba(234,179,8,0.35)',
        text: '#eab308',
        dot: '#eab308',
        defaultLabel: 'YELLOW · WATCH',
      };
      break;
    case 'green':
      colors = {
        bg: 'rgba(16,185,129,0.12)',
        border: 'rgba(16,185,129,0.35)',
        text: '#10b981',
        dot: '#10b981',
        defaultLabel: 'GREEN · NO WARNING',
      };
      break;
  }

  const label = officialLevel?.trim() ? officialLevel.trim().toUpperCase() : colors.defaultLabel;

  const isSmall = size === 'sm';

  return (
    <span
      role="status"
      aria-label={`Official severity: ${label}`}
      className={`inline-flex items-center gap-1.5 font-mono font-semibold tracking-wider rounded-full border transition-colors ${
        isSmall ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      }`}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
      }}
    >
      <span
        className={`rounded-full flex-shrink-0 ${isSmall ? 'w-1.5 h-1.5' : 'w-2 h-2'}`}
        style={{ backgroundColor: colors.dot }}
        aria-hidden="true"
      />
      <span>{label}</span>
    </span>
  );
};

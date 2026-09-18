import React from 'react';
import { ShieldAlert, Info, Wind } from 'lucide-react';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../../types/advisory';
import { OfficialAdvisoryCard } from './OfficialAdvisoryCard';
import { AirQualityCard } from './AirQualityCard';

interface OfficialAdvisorySectionProps {
  advisories: OfficialAdvisory[];
  locationName?: string;
  showEmptyState?: boolean;
}

export const OfficialAdvisorySection: React.FC<OfficialAdvisorySectionProps> = ({
  advisories,
  locationName: _locationName,
  showEmptyState = false,
}) => {
  // Separate AQI bulletins from meteorological & hazard advisories
  const aqiAdvisories = advisories.filter(
    (a) => a.hazard_type === 'AIR_QUALITY' || a.authority.toUpperCase() === 'CPCB'
  );
  const weatherAdvisories = advisories.filter(
    (a) => a.hazard_type !== 'AIR_QUALITY' && a.authority.toUpperCase() !== 'CPCB'
  );

  const now = new Date();

  // Active vs Upcoming weather advisories using authoritative temporal validity
  // Expired advisories are excluded from active and upcoming presentation
  const activeAdvisories = weatherAdvisories.filter(
    (a) => getAdvisoryTemporalState(a, now) === 'ACTIVE'
  );

  const upcomingAdvisories = weatherAdvisories.filter(
    (a) => getAdvisoryTemporalState(a, now) === 'UPCOMING'
  );

  const hasAnyAdvisories = advisories.length > 0;

  // If zero advisories and showEmptyState is false, render nothing
  if (!hasAnyAdvisories && !showEmptyState) {
    return null;
  }

  return (
    <section
      aria-label="Official Environmental and Hazard Advisories"
      className="space-y-4 pt-2"
    >
      {/* Section Header */}
      <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-muted)' }}>
        <div className="flex items-center space-x-2">
          <div
            className="p-1.5 rounded-lg flex items-center justify-center text-sky-400"
            style={{ backgroundColor: 'var(--surface-input)' }}
          >
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold tracking-tight uppercase font-mono" style={{ color: 'var(--text-primary)' }}>
              Official Advisories & Warnings
            </h3>
            <p className="text-[11px] font-mono" style={{ color: 'var(--text-muted)' }}>
              Authoritative government intelligence (IMD, NDMA, INCOIS, CPCB)
            </p>
          </div>
        </div>

        {hasAnyAdvisories && (
          <span
            className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-full border"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              borderColor: 'var(--border-muted)',
              color: 'var(--accent)',
            }}
          >
            {advisories.length} {advisories.length === 1 ? 'Advisory' : 'Advisories'}
          </span>
        )}
      </div>

      {/* Empty State */}
      {!hasAnyAdvisories && (
        <div
          className="p-5 rounded-2xl border text-center space-y-2"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: 'var(--border)',
          }}
        >
          <div className="w-8 h-8 rounded-full flex items-center justify-center mx-auto text-zinc-400" style={{ backgroundColor: 'var(--surface-input)' }}>
            <Info className="w-4 h-4" />
          </div>
          <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
            No active official advisories are currently available for this location.
          </p>
          <p className="text-[11px] max-w-md mx-auto" style={{ color: 'var(--text-muted)' }}>
            Official advisories appear here when available from configured sources.
          </p>
        </div>
      )}

      {/* 1. Air Quality Intelligence (Strictly separated from storm/weather warnings) */}
      {aqiAdvisories.length > 0 && (
        <div className="space-y-2.5">
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

      {/* 2. Active Now Advisories */}
      {activeAdvisories.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center space-x-1.5 text-xs font-mono font-semibold" style={{ color: '#10b981' }}>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>ACTIVE ADVISORIES NOW</span>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {activeAdvisories.map((adv) => (
              <OfficialAdvisoryCard key={adv.id} advisory={adv} />
            ))}
          </div>
        </div>
      )}

      {/* 3. Upcoming Advisories (Visually secondary) */}
      {upcomingAdvisories.length > 0 && (
        <div className="space-y-2.5 opacity-90">
          <div className="flex items-center space-x-1.5 text-xs font-mono font-semibold" style={{ color: 'var(--text-muted)' }}>
            <ShieldAlert className="w-3.5 h-3.5 text-zinc-400" />
            <span>UPCOMING WATCHES & ADVANCE ALERTS</span>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {upcomingAdvisories.map((adv) => (
              <OfficialAdvisoryCard key={adv.id} advisory={adv} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
};

import React, { useState, useEffect } from 'react';
import { Clock, MapPin, Loader2 } from 'lucide-react';
import { GeocodedLocationSchema } from '../types/weather';

interface LiveWeatherHeaderProps {
  location?: GeocodedLocationSchema | null;
  temperature?: number | null;
  isLocating?: boolean;
  onRequestLocation?: () => void;
}

export const LiveWeatherHeader: React.FC<LiveWeatherHeaderProps> = ({
  location,
  temperature,
  isLocating = false,
  onRequestLocation,
}) => {
  const [currentTime, setCurrentTime] = useState<Date>(new Date());

  useEffect(() => {
    // 1-second ticking clock
    const timer = setInterval(() => {
      if (!document.hidden) {
        setCurrentTime(new Date());
      }
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const timezone = location?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

  // Format Time
  let timeString = '';
  try {
    timeString = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    }).format(currentTime);
  } catch {
    timeString = currentTime.toLocaleTimeString();
  }

  // Format Date: e.g. "Tue, Sep 8, 2026"
  let dateString = '';
  try {
    dateString = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(currentTime);
  } catch {
    dateString = currentTime.toLocaleDateString();
  }

  const hasLocation = Boolean(location?.name);
  const tempDisplay = typeof temperature === 'number' ? `${Math.round(temperature)}°C` : null;

  let tooltipTitle = 'StormOps Active (Location unavailable)';
  if (isLocating && !hasLocation) {
    tooltipTitle = 'Detecting current device location...';
  } else if (hasLocation) {
    tooltipTitle = `Live Location: ${location?.name} (${timezone})`;
  }

  return (
    <div
      className="hidden sm:flex items-center space-x-2.5 px-3 py-1.5 rounded-xl border text-xs font-mono transition-all"
      style={{
        backgroundColor: 'var(--surface-input)',
        borderColor: 'var(--border-muted)',
        color: 'var(--text-primary)',
      }}
      title={tooltipTitle}
    >
      {/* Location & Temp */}
      <div className="flex items-center space-x-1.5 font-semibold tracking-tight">
        {isLocating && !hasLocation ? (
          <>
            <Loader2 className="w-3.5 h-3.5 flex-shrink-0 animate-spin" style={{ color: 'var(--accent)' }} />
            <span
              className="text-[11px] font-medium animate-pulse"
              style={{ color: 'var(--text-secondary)' }}
            >
              Locating...
            </span>
          </>
        ) : hasLocation ? (
          <>
            <MapPin className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent)' }} />
            <span
              className="text-[11px] font-medium truncate max-w-[100px] sm:max-w-[140px]"
              style={{ color: 'var(--text-primary)' }}
            >
              {location?.name}
            </span>
            {tempDisplay && (
              <span
                className="px-1.5 py-0.5 rounded-md font-mono text-[11px] font-bold"
                style={{
                  backgroundColor: 'var(--accent-muted)',
                  color: 'var(--accent-text)',
                }}
              >
                {tempDisplay}
              </span>
            )}
          </>
        ) : (
          <button
            type="button"
            onClick={onRequestLocation}
            className="flex items-center space-x-1.5 cursor-pointer hover:opacity-80 transition-opacity"
            title="Click to detect device location"
          >
            <MapPin className="w-3.5 h-3.5 flex-shrink-0 opacity-60" style={{ color: 'var(--text-muted)' }} />
            <span
              className="text-[11px] font-medium truncate max-w-[100px] sm:max-w-[140px]"
              style={{ color: 'var(--text-secondary)' }}
            >
              StormOps Active
            </span>
          </button>
        )}
      </div>

      <span className="opacity-30" style={{ color: 'var(--text-tertiary)' }}>|</span>

      {/* Date & Time */}
      <div className="flex items-center space-x-1.5 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
        <Clock className="w-3 h-3 opacity-70 hidden sm:inline" />
        <span className="hidden md:inline">{dateString} ·</span>
        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
          {timeString}
        </span>
      </div>
    </div>
  );
};

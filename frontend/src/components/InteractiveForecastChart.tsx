import React, { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { CloudRain, Wind, Droplets, Clock } from 'lucide-react';
import { HourlyForecast } from '../types/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { useTheme } from '../context/ThemeContext';

export interface InteractiveForecastChartProps {
  items: HourlyForecast[];
  periodTitle: string;
  /** Timezone string e.g. "Asia/Kolkata" — used to identify the current local hour */
  timezone?: string | null;
  /** Optional callback to notify parent surface when user scrubs an hour */
  onInspectHour?: (hour: HourlyForecast | null) => void;
}

// ---------------------------------------------------------------------------
// Time utilities
// ---------------------------------------------------------------------------

export function parseHour(t: string): number {
  const timePart = t.includes('T') ? t.split('T')[1].slice(0, 5) : t.slice(0, 5);
  return parseInt(timePart.split(':')[0] ?? '0', 10);
}

export function parseMinute(t: string): number {
  const timePart = t.includes('T') ? t.split('T')[1].slice(0, 5) : t.slice(0, 5);
  return parseInt(timePart.split(':')[1] ?? '0', 10);
}

export function fmtShort(t: string): string {
  const h = parseHour(t);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12} ${ampm}`;
}

export function fmtFull(t: string): string {
  const h = parseHour(t);
  const m = parseMinute(t);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, '0')} ${ampm}`;
}

function isMidnightCrossing(a: HourlyForecast, b: HourlyForecast): boolean {
  return parseHour(b.time) < parseHour(a.time);
}

function getCurrentHourInTz(timezone?: string | null): number {
  try {
    if (timezone) {
      const s = new Intl.DateTimeFormat('en-GB', {
        timeZone: timezone,
        hour: '2-digit',
        hour12: false,
      }).format(new Date());
      return parseInt(s, 10);
    }
  } catch {
    /* ignore */
  }
  return new Date().getHours();
}

// ---------------------------------------------------------------------------
// Smooth cubic Catmull-Rom spline path builder (Strictly visual smoothing)
// ---------------------------------------------------------------------------

function smoothPath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length < 2) return '';
  if (pts.length === 2) return `M ${pts[0].x} ${pts[0].y} L ${pts[1].x} ${pts[1].y}`;
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }
  return d;
}

function areaPath(pts: Array<{ x: number; y: number }>, bottomY: number): string {
  if (pts.length < 2) return '';
  const line = smoothPath(pts);
  return `${line} L ${pts[pts.length - 1].x} ${bottomY} L ${pts[0].x} ${bottomY} Z`;
}

// ---------------------------------------------------------------------------
// Nearest forecast index resolver across continuous interaction surface
// ---------------------------------------------------------------------------

export function findNearestForecastIndex(
  svgX: number,
  points: Array<{ x: number; idx: number }>
): number {
  if (points.length === 0) return 0;
  let best = points[0].idx;
  let minDiff = Infinity;
  for (let i = 0; i < points.length; i++) {
    const diff = Math.abs(points[i].x - svgX);
    if (diff < minDiff) {
      minDiff = diff;
      best = points[i].idx;
    }
  }
  return best;
}

// ---------------------------------------------------------------------------
// Tooltip card (Inspection overlay)
// ---------------------------------------------------------------------------

const TooltipCard: React.FC<{ item: HourlyForecast; isCurrent: boolean }> = ({
  item,
  isCurrent,
}) => {
  const rain = item.precipitation_probability ?? 0;
  const feelsLike = item.feels_like != null ? Math.round(item.feels_like) : null;

  return (
    <div
      role="tooltip"
      className="rounded-xl p-3 space-y-2 text-xs backdrop-blur-md transition-all"
      style={{
        backgroundColor: 'var(--surface-overlay, rgba(18, 18, 22, 0.94))',
        border: '1px solid var(--border-default)',
        boxShadow: 'var(--shadow-md, 0 8px 24px rgba(0,0,0,0.35))',
        minWidth: '155px',
        maxWidth: '190px',
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono font-semibold" style={{ color: 'var(--accent-primary)' }}>
          {fmtFull(item.time)}
        </span>
        {isCurrent && (
          <span
            className="type-label text-[9px] px-1.5 py-0.5 rounded-sm"
            style={{
              backgroundColor: 'var(--accent-subtle)',
              color: 'var(--accent-primary)',
              border: '1px solid var(--accent-border)',
            }}
          >
            NOW
          </span>
        )}
      </div>

      <div className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
        {getWeatherIcon(item.weather_code, 'w-3.5 h-3.5')}
        <span className="capitalize truncate font-medium">{item.condition}</span>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-base font-light font-tabular" style={{ color: 'var(--text-primary)' }}>
          {Math.round(item.temperature)}°C
        </span>
        {feelsLike !== null && (
          <span className="type-meta text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
            feels {feelsLike}°
          </span>
        )}
      </div>

      <div
        className="pt-1.5 border-t"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div className="grid grid-cols-2 gap-x-3 gap-y-1" style={{ color: 'var(--text-secondary)' }}>
          <div className="flex items-center gap-1">
            <CloudRain className="w-3 h-3 flex-shrink-0 text-sky-400" />
            <span className="font-tabular">{rain}%</span>
          </div>
          <div className="flex items-center gap-1">
            <Droplets className="w-3 h-3 flex-shrink-0 text-indigo-400" />
            <span className="font-tabular">{item.precipitation} mm</span>
          </div>
          <div className="flex items-center gap-1 col-span-2">
            <Wind className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
            <span className="font-tabular">{item.wind_speed} km/h</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Interactive Forecast Chart
// ---------------------------------------------------------------------------

export const InteractiveForecastChart: React.FC<InteractiveForecastChartProps> = ({
  items,
  periodTitle,
  timezone,
  onInspectHour,
}) => {
  const { theme, accentColor } = useTheme();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const touchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [tooltipLeft, setTooltipLeft] = useState(true);

  // Layout geometry
  const W = 640;
  const pL = 28;     // pad left
  const pR = 20;     // pad right
  const pTop = 44;   // room above curve: condition icons + temp labels
  const cH = 96;     // temperature curve height
  const prH = 26;    // precipitation bar height
  const pBot = 32;   // time axis
  const totalH = pTop + cH + prH + pBot;
  const curveBottom = pTop + cH;
  const precipBottom = pTop + cH + prH;

  // Accent color from theme
  const accent = accentColor;
  const gradId = `fcg-${theme}-${accent.replace('#', '')}`;

  // Current hour detection
  const currentHour = getCurrentHourInTz(timezone);

  // Computed temperature range
  const temps = items.map((i) => Math.round(i.temperature));
  const minT = temps.length > 0 ? Math.min(...temps) - 1 : 0;
  const maxT = temps.length > 0 ? Math.max(...temps) + 1 : 30;
  const tRange = Math.max(1, maxT - minT);

  const getX = useCallback(
    (idx: number) => {
      if (items.length <= 1) return W / 2;
      return pL + (idx / (items.length - 1)) * (W - pL - pR);
    },
    [items.length]
  );

  const getY = useCallback(
    (temp: number) => pTop + cH - ((temp - minT) / tRange) * cH,
    [minT, tRange]
  );

  const points = useMemo(
    () =>
      items.map((item, idx) => {
        const h = parseHour(item.time);
        return {
          x: getX(idx),
          y: getY(Math.round(item.temperature)),
          temp: Math.round(item.temperature),
          feelsY: item.feels_like != null ? getY(Math.round(item.feels_like)) : null,
          rain: item.precipitation_probability ?? 0,
          code: item.weather_code,
          h,
          idx,
          raw: item,
        };
      }),
    [items, getX, getY]
  );

  // Identify index closest to current local hour
  const currentIdx = useMemo(() => {
    let best = 0;
    let bestDiff = Infinity;
    points.forEach((p, i) => {
      const diff = Math.abs(p.h - currentHour);
      if (diff < bestDiff) {
        bestDiff = diff;
        best = i;
      }
    });
    return best;
  }, [points, currentHour]);

  // Points with isCurrent
  const pts = useMemo(
    () => points.map((p, i) => ({ ...p, isCurrent: i === currentIdx })),
    [points, currentIdx]
  );

  const linePts = pts.map((p) => ({ x: p.x, y: p.y }));
  const linePath = useMemo(() => smoothPath(linePts), [linePts]);
  const fillPath = useMemo(() => areaPath(linePts, curveBottom), [linePts, curveBottom]);

  // Feels-like path (subtle secondary dashed line)
  const flPts = useMemo(() => {
    const fl = pts.filter((p) => p.feelsY !== null);
    return fl.length >= Math.floor(pts.length * 0.5) ? fl.map((p) => ({ x: p.x, y: p.feelsY! })) : [];
  }, [pts]);
  const flPath = useMemo(() => (flPts.length >= 2 ? smoothPath(flPts) : ''), [flPts]);

  // Midnight crossings (00:00 boundary markers)
  const midnights = useMemo(() => {
    const r: number[] = [];
    for (let i = 1; i < items.length; i++) {
      if (isMidnightCrossing(items[i - 1], items[i])) r.push(i);
    }
    return r;
  }, [items]);

  // Orientation Axis Points: Every 3 hours + start + end
  const axisPts = useMemo(
    () => pts.filter((p, i) => i === 0 || i === pts.length - 1 || p.h % 3 === 0),
    [pts]
  );

  const labelEvery = pts.length > 20 ? 4 : pts.length > 12 ? 3 : 2;
  const hitWidth = pts.length > 0 ? (W - pL - pR) / pts.length : 20;

  // Interaction handlers
  const getSvgX = useCallback((e: React.MouseEvent | React.TouchEvent): number | null => {
    const svg = svgRef.current;
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    if (rect.width === 0) return null;
    const clientX =
      'touches' in e
        ? e.touches[0]?.clientX ?? (e as React.TouchEvent).changedTouches[0]?.clientX ?? 0
        : (e as React.MouseEvent).clientX;
    return ((clientX - rect.left) / rect.width) * W;
  }, []);

  const selectHour = useCallback(
    (idx: number, svgX?: number) => {
      setSelectedIdx(idx);
      const posX = svgX !== undefined ? svgX : getX(idx);
      setTooltipLeft(posX > W * 0.55);
      if (onInspectHour) {
        onInspectHour(items[idx] ?? null);
      }
    },
    [items, getX, onInspectHour]
  );

  const onInteract = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      if (touchTimerRef.current) {
        clearTimeout(touchTimerRef.current);
        touchTimerRef.current = null;
      }
      const x = getSvgX(e);
      if (x === null) return;
      const idx = findNearestForecastIndex(x, pts);
      selectHour(idx, x);
    },
    [getSvgX, pts, selectHour]
  );

  const onLeave = useCallback(() => {
    setSelectedIdx(null);
    if (onInspectHour) {
      onInspectHour(null);
    }
  }, [onInspectHour]);

  const onTouchEnd = useCallback(() => {
    if (touchTimerRef.current) clearTimeout(touchTimerRef.current);
    // After 2.5 seconds of touch inactivity, smoothly return to current/now state
    touchTimerRef.current = setTimeout(() => {
      setSelectedIdx(null);
      if (onInspectHour) {
        onInspectHour(null);
      }
    }, 2500);
  }, [onInspectHour]);

  // Keyboard navigation for full sequential scrubbing
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        const next = selectedIdx === null ? (currentIdx !== null ? currentIdx : 0) : Math.min(items.length - 1, selectedIdx + 1);
        selectHour(next);
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        const next = selectedIdx === null ? (currentIdx !== null ? currentIdx : 0) : Math.max(0, selectedIdx - 1);
        selectHour(next);
      } else if (e.key === 'Home') {
        e.preventDefault();
        selectHour(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        selectHour(items.length - 1);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onLeave();
      }
    },
    [items.length, selectedIdx, currentIdx, selectHour, onLeave]
  );

  useEffect(() => {
    return () => {
      if (touchTimerRef.current) clearTimeout(touchTimerRef.current);
    };
  }, []);

  const active = selectedIdx !== null && selectedIdx >= 0 && selectedIdx < pts.length ? pts[selectedIdx] : null;

  return (
    <section
      ref={containerRef}
      role="region"
      aria-label="24-hour weather forecast timeline"
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="w-full rounded-2xl p-5 sm:p-6 border space-y-4 transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--focus-ring)]"
      style={{
        backgroundColor: 'var(--surface-primary)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* 1. Header: Forecast Context & Legend */}
      <div
        className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 gap-2 border-b"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div>
          <div className="flex items-center gap-2">
            <span
              className="type-label flex items-center gap-1.5"
              style={{ color: 'var(--accent-primary)' }}
            >
              <Clock className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
              24-Hour Forecast Timeline
            </span>
            <span className="type-meta text-xs" style={{ color: 'var(--text-tertiary)' }}>
              · Evidence
            </span>
          </div>
          <p className="type-meta text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            Hourly temperature progression and precipitation timing for {periodTitle}
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: accent }} />
            <span className="type-meta text-[11px]">Temperature</span>
          </div>
          {flPath && (
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t border-dashed" style={{ borderColor: accent, opacity: 0.5 }} />
              <span className="type-meta text-[11px]">Feels like</span>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2 rounded-xs" style={{ backgroundColor: '#38bdf8', opacity: 0.7 }} />
            <span className="type-meta text-[11px]">Rain %</span>
          </div>
        </div>
      </div>

      {/* 2. Interactive SVG Chart Area with Continuous Interaction */}
      <div className="relative">
        <div
          className="w-full overflow-x-auto"
          style={{ WebkitOverflowScrolling: 'touch' } as React.CSSProperties}
        >
          <div className="min-w-[420px] sm:min-w-full">
            <svg
              ref={svgRef}
              viewBox={`0 0 ${W} ${totalH}`}
              className="w-full h-auto overflow-visible select-none"
              aria-label="24-hour weather timeline chart"
              onMouseMove={onInteract}
              onMouseLeave={onLeave}
              onTouchStart={onInteract}
              onTouchMove={(e) => {
                e.preventDefault();
                onInteract(e);
              }}
              onTouchEnd={onTouchEnd}
              style={{ touchAction: 'none' }}
            >
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={accent} stopOpacity="0.18" />
                  <stop offset="100%" stopColor={accent} stopOpacity="0.00" />
                </linearGradient>
              </defs>

              {/* Precipitation bar background track */}
              <rect
                x={pL}
                y={curveBottom}
                width={W - pL - pR}
                height={prH}
                fill="var(--surface-secondary)"
                opacity={0.6}
                rx={3}
              />

              {/* Midnight markers (00:00 boundary) */}
              {midnights.map((i) => (
                <g key={`mid-${i}`}>
                  <line
                    x1={getX(i)}
                    y1={pTop - 10}
                    x2={getX(i)}
                    y2={precipBottom}
                    stroke="var(--border-subtle)"
                    strokeWidth={1}
                    strokeDasharray="3 4"
                  />
                  <text
                    x={getX(i) + 4}
                    y={pTop - 12}
                    fontSize={8}
                    fill="var(--text-tertiary)"
                    fontFamily="monospace"
                  >
                    00:00
                  </text>
                </g>
              ))}

              {/* Precipitation bars (Semantic meteorological blue across full interval) */}
              {pts.map((p) => {
                const barH = prH * (p.rain / 100);
                const isSel = selectedIdx === p.idx;
                const barW = Math.max(5, hitWidth * 0.72);
                const col =
                  p.rain >= 70
                    ? '#38bdf8'
                    : p.rain >= 40
                    ? '#0284c7'
                    : 'rgba(56, 189, 248, 0.28)';

                return (
                  <rect
                    key={`pr-${p.idx}`}
                    x={p.x - barW / 2}
                    y={precipBottom - barH}
                    width={barW}
                    height={barH}
                    rx={2}
                    fill={col}
                    opacity={isSel ? 1 : 0.65}
                    stroke={isSel ? '#38bdf8' : 'none'}
                    strokeWidth={isSel ? 1 : 0}
                    className="transition-opacity duration-150"
                  />
                );
              })}

              {/* Area gradient under temperature curve */}
              <path d={fillPath} fill={`url(#${gradId})`} />

              {/* Secondary Feels-like dashed line */}
              {flPath && (
                <path
                  d={flPath}
                  fill="none"
                  stroke={accent}
                  strokeWidth={1.2}
                  strokeOpacity={0.35}
                  strokeDasharray="3 4"
                />
              )}

              {/* Primary Temperature curve */}
              <path
                d={linePath}
                fill="none"
                stroke={accent}
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* NOW Vertical Marker (Permanently anchored at current hour, independent of selection) */}
              {(() => {
                const cp = pts[currentIdx];
                if (!cp) return null;
                return (
                  <g key="now-marker">
                    <line
                      x1={cp.x}
                      y1={pTop - 8}
                      x2={cp.x}
                      y2={precipBottom}
                      stroke={accent}
                      strokeWidth={1.5}
                      strokeOpacity={0.45}
                    />
                    <text
                      x={cp.x}
                      y={pTop - 11}
                      textAnchor="middle"
                      fontSize={8}
                      fill={accent}
                      fontFamily="monospace"
                      fontWeight="700"
                    >
                      NOW
                    </text>
                  </g>
                );
              })()}

              {/* Selected-hour scrubber line and guide */}
              {active && (
                <g key="inspection-guide">
                  <line
                    x1={active.x}
                    y1={pTop - 10}
                    x2={active.x}
                    y2={precipBottom}
                    stroke={accent}
                    strokeWidth={1.2}
                    strokeDasharray="3 3"
                  />
                  {/* Halo and highlight dot on curve */}
                  <circle
                    cx={active.x}
                    cy={active.y}
                    r={7}
                    fill={accent}
                    fillOpacity={0.25}
                  />
                  <circle
                    cx={active.x}
                    cy={active.y}
                    r={4.5}
                    fill={accent}
                    stroke="var(--surface-primary)"
                    strokeWidth={2}
                  />
                  {/* Active temperature numeral */}
                  <text
                    x={active.x}
                    y={active.y - 10}
                    textAnchor="middle"
                    fontSize={10.5}
                    fontWeight="700"
                    fill={accent}
                    fontFamily="monospace"
                  >
                    {active.temp}°
                  </text>
                  {/* Active condition icon */}
                  <foreignObject
                    x={active.x - 7}
                    y={pTop - 36}
                    width={14}
                    height={14}
                    style={{ overflow: 'visible', pointerEvents: 'none' }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: 1,
                      }}
                    >
                      {getWeatherIcon(active.code, 'w-3.5 h-3.5')}
                    </div>
                  </foreignObject>
                </g>
              )}

              {/* Idle points, icons, and temperature numerals */}
              {pts.map((p) => {
                const isSel = selectedIdx === p.idx;
                if (isSel) return null; // Rendered in inspection-guide above

                const isCurr = p.isCurrent;
                const showLabel = isCurr || p.idx % labelEvery === 0;
                const showIcon = p.idx % 3 === 0;

                return (
                  <g key={`pt-${p.idx}`}>
                    {/* WMO condition icon */}
                    {showIcon && (
                      <foreignObject
                        x={p.x - 7}
                        y={pTop - 36}
                        width={14}
                        height={14}
                        style={{ overflow: 'visible', pointerEvents: 'none' }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            opacity: 0.6,
                            transition: 'opacity 0.15s',
                          }}
                        >
                          {getWeatherIcon(p.code, 'w-3.5 h-3.5')}
                        </div>
                      </foreignObject>
                    )}

                    {/* Temperature value */}
                    {showLabel && (
                      <text
                        x={p.x}
                        y={p.y - 8}
                        textAnchor="middle"
                        fontSize={isCurr ? 10 : 9}
                        fontWeight={isCurr ? '700' : '400'}
                        fill={isCurr ? accent : 'var(--text-primary)'}
                        fontFamily="monospace"
                      >
                        {p.temp}°
                      </text>
                    )}

                    {/* Point dot on curve */}
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={isCurr ? 4 : 2}
                      fill={isCurr ? accent : 'var(--surface-primary)'}
                      stroke={accent}
                      strokeWidth={isCurr ? 2 : 1}
                      className="transition-all duration-100"
                    />
                  </g>
                );
              })}

              {/* Intermediate ticks for all available hours along the time axis */}
              {pts.map((p) => {
                const isMajor = p.h % 3 === 0 || p.idx === 0 || p.idx === pts.length - 1;
                return (
                  <line
                    key={`tick-${p.idx}`}
                    x1={p.x}
                    y1={isMajor ? totalH - 24 : totalH - 21}
                    x2={p.x}
                    y2={totalH - 18}
                    stroke={isMajor ? 'var(--border-default)' : 'var(--border-subtle)'}
                    strokeWidth={isMajor ? 1.2 : 0.8}
                    opacity={isMajor ? 0.8 : 0.45}
                  />
                );
              })}

              {/* Orientation Axis Labels (3-Hour intervals + start/end) */}
              {axisPts.map((p) => {
                // If this point is close to the currently inspected point, hide to prevent overlap
                const isOverlapped = active && Math.abs(active.x - p.x) < 18;
                if (isOverlapped) return null;

                return (
                  <text
                    key={`ax-${p.idx}`}
                    x={p.x}
                    y={totalH - 8}
                    textAnchor={p.idx === 0 ? 'start' : p.idx === pts.length - 1 ? 'end' : 'middle'}
                    fontSize={9}
                    fill={p.isCurrent ? accent : 'var(--text-secondary)'}
                    fontFamily="monospace"
                    fontWeight={p.isCurrent ? '600' : '400'}
                  >
                    {p.h === 0 && p.idx > 0 ? '00:00' : fmtShort(p.raw.time)}
                  </text>
                );
              })}

              {/* Active Inspected Hour Axis Badge (visibly identifies any selected intermediate or major hour) */}
              {active && (
                <g key="active-axis-badge" className="transition-all duration-75">
                  <rect
                    x={Math.max(4, Math.min(W - 48, active.x - 22))}
                    y={totalH - 17}
                    width={44}
                    height={15}
                    rx={3}
                    fill="var(--surface-primary)"
                    stroke={accent}
                    strokeWidth={1}
                  />
                  <text
                    x={Math.max(26, Math.min(W - 26, active.x))}
                    y={totalH - 6.5}
                    textAnchor="middle"
                    fontSize={8.5}
                    fontWeight="700"
                    fill={accent}
                    fontFamily="monospace"
                  >
                    {fmtShort(active.raw.time)}
                  </text>
                </g>
              )}

              {/* "rain" indicator */}
              <text
                x={pL - 4}
                y={curveBottom + prH / 2 + 3}
                textAnchor="end"
                fontSize={7.5}
                fill="var(--text-tertiary)"
                fontFamily="monospace"
              >
                rain
              </text>

              {/* Continuous full-width interactive hit surface */}
              <rect
                x={0}
                y={0}
                width={W}
                height={totalH}
                fill="transparent"
                style={{ cursor: 'crosshair', touchAction: 'none' }}
              />
            </svg>
          </div>
        </div>

        {/* Floating tooltip */}
        {active && (
          <div
            className="absolute top-1 z-10 pointer-events-none"
            style={{ [tooltipLeft ? 'right' : 'left']: '12px' }}
          >
            <TooltipCard item={active.raw} isCurrent={active.isCurrent} />
          </div>
        )}
      </div>

      {/* Scrubber guidance hint */}
      {selectedIdx === null && (
        <p
          className="text-center text-[11px] font-mono"
          style={{ color: 'var(--text-tertiary)' }}
        >
          Hover, drag, or use Arrow keys to inspect every hourly forecast point
        </p>
      )}
    </section>
  );
};

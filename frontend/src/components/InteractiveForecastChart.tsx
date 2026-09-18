import React, { useRef, useState, useCallback, useMemo } from 'react';
import { CloudRain, Wind, Droplets, Clock } from 'lucide-react';
import { HourlyForecast } from '../types/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { useTheme } from '../context/ThemeContext';

interface InteractiveForecastChartProps {
  items: HourlyForecast[];
  periodTitle: string;
  /** Timezone string e.g. "Asia/Kolkata" — used to identify the current local hour */
  timezone?: string | null;
}

// ---------------------------------------------------------------------------
// Time utilities
// ---------------------------------------------------------------------------

function parseHour(t: string): number {
  const timePart = t.includes('T') ? t.split('T')[1].slice(0, 5) : t.slice(0, 5);
  return parseInt(timePart.split(':')[0] ?? '0', 10);
}

function parseMinute(t: string): number {
  const timePart = t.includes('T') ? t.split('T')[1].slice(0, 5) : t.slice(0, 5);
  return parseInt(timePart.split(':')[1] ?? '0', 10);
}

function fmtShort(t: string): string {
  const h = parseHour(t);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12} ${ampm}`;
}

function fmtFull(t: string): string {
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
  } catch { /* ignore */ }
  return new Date().getHours();
}

// ---------------------------------------------------------------------------
// Smooth cubic Catmull-Rom spline path builder
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
// Tooltip card
// ---------------------------------------------------------------------------

const TooltipCard: React.FC<{ item: HourlyForecast; isCurrent: boolean }> = ({ item, isCurrent }) => {
  const rain = item.precipitation_probability ?? 0;
  const feelsLike = item.feels_like != null ? Math.round(item.feels_like) : null;
  return (
    <div
      className="rounded-2xl p-3 space-y-2 text-xs"
      style={{
        background: 'var(--surface-elevated)',
        border: '1px solid var(--border)',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
        minWidth: '155px',
        maxWidth: '185px',
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono font-semibold" style={{ color: 'var(--accent)' }}>
          {fmtFull(item.time)}
        </span>
        {isCurrent && (
          <span
            className="font-mono text-[9px] px-1.5 py-0.5 rounded uppercase tracking-wider"
            style={{ background: 'var(--accent-muted)', color: 'var(--accent)', border: '1px solid var(--accent-border)' }}
          >
            NOW
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
        {getWeatherIcon(item.weather_code, 'w-3.5 h-3.5')}
        <span className="capitalize truncate">{item.condition}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-base font-light" style={{ color: 'var(--text-primary)' }}>
          {Math.round(item.temperature)}°C
        </span>
        {feelsLike !== null && (
          <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
            feels {feelsLike}°
          </span>
        )}
      </div>
      <div style={{ borderTop: '1px solid var(--border-muted)', paddingTop: '6px' }}>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1" style={{ color: 'var(--text-secondary)' }}>
          <div className="flex items-center gap-1">
            <CloudRain className="w-3 h-3 flex-shrink-0" /><span>{rain}%</span>
          </div>
          <div className="flex items-center gap-1">
            <Droplets className="w-3 h-3 flex-shrink-0" /><span>{item.precipitation} mm</span>
          </div>
          <div className="flex items-center gap-1 col-span-2">
            <Wind className="w-3 h-3 flex-shrink-0" /><span>{item.wind_speed} km/h</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const InteractiveForecastChart: React.FC<InteractiveForecastChartProps> = ({
  items,
  periodTitle,
  timezone,
}) => {
  const { theme, accentColor } = useTheme();
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [tooltipLeft, setTooltipLeft] = useState(true);

  if (!items || items.length === 0) return null;

  // Layout constants
  const W = 640;
  const pL = 28;     // pad left
  const pR = 16;     // pad right
  const pTop = 46;   // room above curve: condition icons + temp labels
  const cH = 96;     // temperature curve height
  const prH = 26;    // precipitation bar height
  const pBot = 34;   // time axis
  const totalH = pTop + cH + prH + pBot;
  const curveBottom = pTop + cH;
  const precipBottom = pTop + cH + prH;

  // Accent color from theme (Atheris blue, Vandal neon red, Light emerald, Midnight amber)
  const accent = accentColor;

  const gradId = `fcg-${theme}-${accent.replace('#', '')}`;

  // Current hour detection
  const currentHour = getCurrentHourInTz(timezone);

  // Computed points
  const temps = items.map(i => Math.round(i.temperature));
  const minT = Math.min(...temps) - 1;
  const maxT = Math.max(...temps) + 1;
  const tRange = Math.max(1, maxT - minT);

  const getX = useCallback((idx: number) => {
    if (items.length <= 1) return W / 2;
    return pL + (idx / (items.length - 1)) * (W - pL - pR);
  }, [items.length]);

  const getY = useCallback((temp: number) => pTop + cH - ((temp - minT) / tRange) * cH, [minT, tRange]);

  const points = useMemo(() => items.map((item, idx) => {
    const h = parseHour(item.time);
    return {
      x: getX(idx),
      y: getY(Math.round(item.temperature)),
      temp: Math.round(item.temperature),
      feelsY: item.feels_like != null ? getY(Math.round(item.feels_like)) : null,
      rain: item.precipitation_probability ?? 0,
      code: item.weather_code,
      h,
      isCurrent: (() => {
        // Find item closest to current hour
        return false; // computed after
      })(),
      idx,
      raw: item,
    };
  }), [items, getX, getY]);

  // Now set isCurrent on the closest point
  const currentIdx = useMemo(() => {
    let best = 0, bestDiff = Infinity;
    points.forEach((p, i) => {
      const diff = Math.abs(p.h - currentHour);
      if (diff < bestDiff) { bestDiff = diff; best = i; }
    });
    return best;
  }, [points, currentHour]);

  // Mark current
  const pts = useMemo(() => points.map((p, i) => ({ ...p, isCurrent: i === currentIdx })), [points, currentIdx]);

  const linePts = pts.map(p => ({ x: p.x, y: p.y }));
  const linePath = useMemo(() => smoothPath(linePts), [linePts]);
  const fillPath = useMemo(() => areaPath(linePts, curveBottom), [linePts, curveBottom]);

  // Feels-like path (subtle secondary line, only if available on most points)
  const flPts = useMemo(() => {
    const fl = pts.filter(p => p.feelsY !== null);
    return fl.length >= Math.floor(pts.length * 0.5) ? fl.map(p => ({ x: p.x, y: p.feelsY! })) : [];
  }, [pts]);
  const flPath = useMemo(() => flPts.length >= 2 ? smoothPath(flPts) : '', [flPts]);

  // Midnight crossings
  const midnights = useMemo(() => {
    const r: number[] = [];
    for (let i = 1; i < items.length; i++) {
      if (isMidnightCrossing(items[i - 1], items[i])) r.push(i);
    }
    return r;
  }, [items]);

  // Axis: every 3 hours + first + last
  const axisPts = useMemo(() => pts.filter((p, i) => i === 0 || i === pts.length - 1 || p.h % 3 === 0), [pts]);

  // Label density
  const labelEvery = pts.length > 20 ? 4 : pts.length > 12 ? 3 : 2;
  const hitWidth = Math.max(18, (W - pL - pR) / pts.length);

  // Interaction
  const getSvgX = useCallback((e: React.MouseEvent | React.TouchEvent): number | null => {
    const svg = svgRef.current;
    if (!svg) return null;
    const rect = svg.getBoundingClientRect();
    const clientX = 'touches' in e
      ? (e.touches[0]?.clientX ?? (e as React.TouchEvent).changedTouches[0]?.clientX ?? 0)
      : (e as React.MouseEvent).clientX;
    return ((clientX - rect.left) / rect.width) * W;
  }, []);

  const findNearest = useCallback((svgX: number): number => {
    let best = 0, bd = Infinity;
    pts.forEach(p => { const d = Math.abs(p.x - svgX); if (d < bd) { bd = d; best = p.idx; } });
    return best;
  }, [pts]);

  const onInteract = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    const x = getSvgX(e);
    if (x === null) return;
    const idx = findNearest(x);
    setSelectedIdx(idx);
    setTooltipLeft(x > W * 0.55);
  }, [getSvgX, findNearest]);

  const onLeave = useCallback(() => setSelectedIdx(null), []);
  const onTouchEnd = useCallback(() => setTimeout(() => setSelectedIdx(null), 2500), []);

  const active = selectedIdx !== null ? pts[selectedIdx] : null;

  return (
    <div className="space-y-3 pt-4" style={{ borderTop: '1px solid var(--border-muted)' }}>
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
        <span className="flex items-center gap-1.5 font-medium">
          <Clock className="w-3.5 h-3.5" style={{ color: accent }} />
          24-HOUR FORECAST
        </span>
        <span className="uppercase tracking-wider">{periodTitle}</span>
      </div>

      {/* Chart area */}
      <div className="relative">
        <div className="w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' } as React.CSSProperties}>
          <div className="min-w-[400px] sm:min-w-full">
            <svg
              ref={svgRef}
              viewBox={`0 0 ${W} ${totalH}`}
              className="w-full h-auto overflow-visible select-none"
              aria-label="24-hour weather forecast"
              onMouseMove={onInteract}
              onMouseLeave={onLeave}
              onTouchStart={onInteract}
              onTouchMove={(e) => { e.preventDefault(); onInteract(e); }}
              onTouchEnd={onTouchEnd}
              style={{ touchAction: 'pan-y' }}
            >
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={accent} stopOpacity="0.20" />
                  <stop offset="100%" stopColor={accent} stopOpacity="0.00" />
                </linearGradient>
              </defs>

              {/* Precipitation zone background */}
              <rect x={pL} y={curveBottom} width={W - pL - pR} height={prH}
                fill="var(--rain-bar-bg)" opacity={0.4} rx={2} />

              {/* Midnight markers */}
              {midnights.map(i => (
                <g key={`mid-${i}`}>
                  <line x1={getX(i)} y1={pTop - 10} x2={getX(i)} y2={precipBottom}
                    stroke="var(--border-muted)" strokeWidth={1} strokeDasharray="3 5" />
                  <text x={getX(i) + 3} y={pTop - 13} fontSize={7.5}
                    fill="var(--text-tertiary)" fontFamily="monospace">
                    00:00
                  </text>
                </g>
              ))}

              {/* Precipitation bars */}
              {pts.map(p => {
                const barH = prH * (p.rain / 100);
                const isSel = selectedIdx === p.idx;
                const barW = Math.max(5, hitWidth * 0.7);
                const col = p.rain >= 70 ? accent
                  : p.rain >= 40 ? (theme === 'night' ? 'rgba(251,191,36,0.6)' : 'rgba(56,189,248,0.6)')
                  : (theme === 'night' ? 'rgba(251,191,36,0.28)' : 'rgba(56,189,248,0.28)');
                return (
                  <rect key={`pr-${p.idx}`}
                    x={p.x - barW / 2} y={precipBottom - barH}
                    width={barW} height={barH} rx={2}
                    fill={col} opacity={isSel ? 1 : 0.6}
                    className="transition-opacity duration-150"
                  />
                );
              })}

              {/* Area fill */}
              <path d={fillPath} fill={`url(#${gradId})`} />

              {/* Feels-like dashed line */}
              {flPath && (
                <path d={flPath} fill="none" stroke={accent}
                  strokeWidth={1} strokeOpacity={0.28} strokeDasharray="3 4" />
              )}

              {/* Temperature curve */}
              <path d={linePath} fill="none" stroke={accent}
                strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />

              {/* NOW vertical marker */}
              {(() => {
                const cp = pts[currentIdx];
                if (!cp) return null;
                return (
                  <g>
                    <line x1={cp.x} y1={pTop - 8} x2={cp.x} y2={precipBottom}
                      stroke={accent} strokeWidth={1.5} strokeOpacity={0.4} />
                    <text x={cp.x} y={pTop - 11} textAnchor="middle" fontSize={8}
                      fill={accent} fontFamily="monospace" fontWeight="700">
                      NOW
                    </text>
                  </g>
                );
              })()}

              {/* Selected-hour guide */}
              {active && (
                <line x1={active.x} y1={pTop - 4} x2={active.x} y2={precipBottom}
                  stroke="var(--text-secondary)" strokeWidth={1}
                  strokeOpacity={0.4} strokeDasharray="2 4" />
              )}

              {/* Points, labels, icons */}
              {pts.map(p => {
                const isSel = selectedIdx === p.idx;
                const isCurr = p.isCurrent;
                const showLabel = isSel || isCurr || p.idx % labelEvery === 0;
                const showIcon = p.idx % 3 === 0 || isSel;

                return (
                  <g key={`pt-${p.idx}`}>
                    {/* Condition icon row */}
                    {showIcon && (
                      <foreignObject x={p.x - 7} y={pTop - 38} width={14} height={14}
                        style={{ overflow: 'visible', pointerEvents: 'none' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                          opacity: isSel ? 1 : 0.55, transition: 'opacity 0.15s' }}>
                          {getWeatherIcon(p.code, 'w-3.5 h-3.5')}
                        </div>
                      </foreignObject>
                    )}

                    {/* Temp label */}
                    {showLabel && (
                      <text x={p.x} y={p.y - 9}
                        textAnchor="middle"
                        fontSize={isSel || isCurr ? 10 : 9}
                        fontWeight={isSel || isCurr ? '700' : '500'}
                        fill={isSel ? accent : isCurr ? accent : 'var(--text-primary)'}
                        fontFamily="monospace">
                        {p.temp}°
                      </text>
                    )}

                    {/* Dot */}
                    <circle cx={p.x} cy={p.y}
                      r={isSel ? 5.5 : isCurr ? 4 : 2.8}
                      fill={isSel ? accent : 'var(--surface)'}
                      stroke={accent}
                      strokeWidth={isSel ? 0 : isCurr ? 2.5 : 1.8}
                      className="transition-all duration-100"
                    />

                    {/* Hit target */}
                    <rect
                      x={p.x - hitWidth / 2} y={pTop - 8}
                      width={hitWidth} height={totalH - pTop - pBot + 8}
                      fill="transparent"
                      style={{ cursor: 'crosshair' }}
                    />
                  </g>
                );
              })}

              {/* Time axis labels */}
              {axisPts.map(p => (
                <text key={`ax-${p.idx}`}
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
              ))}

              {/* "rain" micro-label */}
              <text x={pL - 3} y={curveBottom + prH / 2 + 3}
                textAnchor="end" fontSize={7}
                fill="var(--text-tertiary)" fontFamily="monospace">
                rain
              </text>
            </svg>
          </div>
        </div>

        {/* Floating tooltip */}
        {active && (
          <div
            className="absolute top-0 z-10 pointer-events-none"
            style={{ [tooltipLeft ? 'right' : 'left']: '4px' }}
          >
            <TooltipCard item={active.raw} isCurrent={active.isCurrent} />
          </div>
        )}
      </div>

      {/* Idle hint */}
      {selectedIdx === null && (
        <p className="text-center text-[11px] font-mono"
          style={{ color: 'var(--text-tertiary)' }}>
          Move over the chart to inspect hourly details
        </p>
      )}
    </div>
  );
};

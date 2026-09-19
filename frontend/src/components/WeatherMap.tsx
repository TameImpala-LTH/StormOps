import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import L from 'leaflet';
import { useTheme } from '../context/ThemeContext';
import { GeocodedLocationSchema, TargetPeriodWeather } from '../types/weather';
import { OfficialAdvisory, getAdvisoryTemporalState } from '../types/advisory';
import { MapPin, Compass, Maximize2, Minimize2, ShieldAlert } from 'lucide-react';

export interface WeatherMapProps {
  location: GeocodedLocationSchema;
  weather: TargetPeriodWeather;
  locationB?: GeocodedLocationSchema | null;
  weatherB?: TargetPeriodWeather | null;
  periodLabel: string;
  advisories?: OfficialAdvisory[];
  onCheckWeatherAtCoords?: (lat: number, lng: number) => void;
}

// ---------------------------------------------------------------------------
// Advisory Geometry & Severity Helpers (Single Source of Truth)
// ---------------------------------------------------------------------------

export function escapeHtml(unsafe: string | null | undefined): string {
  if (!unsafe) return '';
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function formatAdvisoryTime(isoString?: string | null): string {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    return new Intl.DateTimeFormat('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(d);
  } catch {
    return '';
  }
}

/**
 * Determine geographic geometry representation for an official advisory:
 * - Rule 1: polygon_geojson available -> 'polygon'
 * - Rule 2: latitude + longitude + radius_km available -> 'circle'
 * - Rule 3: latitude + longitude available without radius -> 'point'
 * - Rule 4: state/district/subdivision only (no geometry) -> null (DO NOT fabricate polygons)
 */
export function getAdvisoryGeometryType(adv: OfficialAdvisory): 'polygon' | 'circle' | 'point' | null {
  if (adv.polygon_geojson) {
    try {
      const parsed = typeof adv.polygon_geojson === 'string' ? JSON.parse(adv.polygon_geojson) : adv.polygon_geojson;
      if (
        parsed &&
        (parsed.type === 'Polygon' ||
          parsed.type === 'MultiPolygon' ||
          parsed.type === 'Feature' ||
          parsed.type === 'FeatureCollection')
      ) {
        return 'polygon';
      }
    } catch {
      // Malformed GeoJSON — safely ignore and fall back to coordinate checks
    }
  }

  if (
    typeof adv.latitude === 'number' &&
    typeof adv.longitude === 'number' &&
    !isNaN(adv.latitude) &&
    !isNaN(adv.longitude)
  ) {
    if (typeof adv.radius_km === 'number' && adv.radius_km > 0 && !isNaN(adv.radius_km)) {
      return 'circle';
    }
    return 'point';
  }

  // Rule 4: state/district/subdivision only without geometry
  return null;
}

export interface SeverityThemeTokens {
  stroke: string;
  fill: string;
  badgeBg: string;
  badgeBorder: string;
  textColor: string;
  label: string;
}

export function getSeverityTokens(severity: string): SeverityThemeTokens {
  const s = (severity || '').toLowerCase().trim();
  switch (s) {
    case 'red':
      return {
        stroke: '#f43f5e',
        fill: 'rgba(244, 63, 94, 0.20)',
        badgeBg: 'rgba(244, 63, 94, 0.14)',
        badgeBorder: 'rgba(244, 63, 94, 0.40)',
        textColor: '#f43f5e',
        label: 'RED · WARNING',
      };
    case 'orange':
      return {
        stroke: '#f97316',
        fill: 'rgba(249, 115, 22, 0.16)',
        badgeBg: 'rgba(249, 115, 22, 0.14)',
        badgeBorder: 'rgba(249, 115, 22, 0.40)',
        textColor: '#f97316',
        label: 'ORANGE · ALERT',
      };
    case 'yellow':
      return {
        stroke: '#eab308',
        fill: 'rgba(234, 179, 8, 0.12)',
        badgeBg: 'rgba(234, 179, 8, 0.12)',
        badgeBorder: 'rgba(234, 179, 8, 0.35)',
        textColor: '#eab308',
        label: 'YELLOW · WATCH',
      };
    case 'green':
      return {
        stroke: '#10b981',
        fill: 'rgba(16, 185, 129, 0.08)',
        badgeBg: 'rgba(16, 185, 129, 0.12)',
        badgeBorder: 'rgba(16, 185, 129, 0.35)',
        textColor: '#10b981',
        label: 'GREEN · NO WARNING',
      };
    default:
      return {
        stroke: '#a1a1aa',
        fill: 'rgba(161, 161, 170, 0.08)',
        badgeBg: 'rgba(113, 113, 122, 0.14)',
        badgeBorder: 'rgba(113, 113, 122, 0.35)',
        textColor: '#a1a1aa',
        label: 'ADVISORY',
      };
  }
}

export function createAdvisoryMarkerHtml(tokens: SeverityThemeTokens, isUpcoming: boolean): string {
  const strokeStyle = isUpcoming ? 'dashed' : 'solid';
  const opacity = isUpcoming ? '0.75' : '1';
  return `
    <div style="
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--surface-elevated);
      border: 1.5px ${strokeStyle} ${tokens.stroke};
      box-shadow: 0 2px 10px rgba(0,0,0,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      transform: translate(-50%, -50%);
      opacity: ${opacity};
      cursor: pointer;
    ">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${tokens.stroke}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    </div>
  `;
}

export function createAdvisoryTooltipHtml(
  adv: OfficialAdvisory,
  tokens: SeverityThemeTokens,
  isUpcoming: boolean
): string {
  const badgeText = isUpcoming ? `${tokens.label} (UPCOMING)` : tokens.label;
  const timeInfo = isUpcoming
    ? `Effective: ${formatAdvisoryTime(adv.effective_at)}`
    : `Expires: ${formatAdvisoryTime(adv.expires_at)}`;

  return `
    <div style="font-family: inherit; min-width: 190px; max-width: 260px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 5px;">
        <span style="
          font-size: 9px;
          font-weight: 700;
          font-family: monospace;
          letter-spacing: 0.04em;
          padding: 1.5px 6px;
          border-radius: 4px;
          background: ${tokens.badgeBg};
          border: 1px solid ${tokens.badgeBorder};
          color: ${tokens.textColor};
        ">${badgeText}</span>
        <span style="font-size: 10px; font-family: monospace; color: var(--text-tertiary); font-weight: 600;">
          ${escapeHtml(adv.authority)}
        </span>
      </div>
      <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); line-height: 1.35; margin-bottom: 4px;">
        ${escapeHtml(adv.headline || adv.hazard_type)}
      </div>
      <div style="font-size: 10px; color: var(--text-secondary); font-family: monospace;">
        ${timeInfo}
      </div>
    </div>
  `;
}

export function createAdvisoryPopupHtml(
  adv: OfficialAdvisory,
  tokens: SeverityThemeTokens,
  isUpcoming: boolean
): string {
  const badgeText = isUpcoming ? `${tokens.label} (UPCOMING)` : tokens.label;
  const timeRange = `${formatAdvisoryTime(adv.effective_at)} &ndash; ${formatAdvisoryTime(adv.expires_at)}`;

  return `
    <div style="padding: 6px; font-family: inherit; min-width: 220px; max-width: 290px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;">
        <span style="
          font-size: 9px;
          font-weight: 700;
          font-family: monospace;
          letter-spacing: 0.05em;
          padding: 2px 7px;
          border-radius: 4px;
          background: ${tokens.badgeBg};
          border: 1px solid ${tokens.badgeBorder};
          color: ${tokens.textColor};
        ">${badgeText}</span>
        <span style="
          font-size: 10px;
          font-family: monospace;
          color: var(--text-tertiary);
          font-weight: 600;
          text-transform: uppercase;
        ">${escapeHtml(adv.authority)}</span>
      </div>

      <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; line-height: 1.35;">
        ${escapeHtml(adv.headline || adv.hazard_type)}
      </div>

      <div style="font-size: 10px; font-family: monospace; color: var(--text-secondary); margin-bottom: 8px;">
        ${timeRange}
      </div>

      ${adv.description ? `
        <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45; margin-bottom: 8px; max-height: 110px; overflow-y: auto; padding-right: 4px;">
          ${escapeHtml(adv.description)}
        </div>
      ` : ''}

      ${adv.action_guidance ? `
        <div style="
          font-size: 10px;
          padding: 6px 8px;
          border-radius: 6px;
          background: var(--surface);
          border: 1px solid var(--border-muted);
          color: var(--text-secondary);
          margin-bottom: 8px;
        ">
          <strong style="color: var(--text-primary);">Guidance:</strong> ${escapeHtml(adv.action_guidance)}
        </div>
      ` : ''}

      ${adv.source_url ? `
        <div style="border-top: 1px solid var(--border-muted); padding-top: 6px; text-align: right;">
          <a href="${escapeHtml(adv.source_url)}" target="_blank" rel="noopener noreferrer" style="
            font-size: 10px;
            font-family: monospace;
            color: var(--accent);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 3px;
          ">
            Official Source &nearr;
          </a>
        </div>
      ` : ''}
    </div>
  `;
}


// Configurable Basemap Tile Layer URL & Attribution (single source of truth)
export const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// CSS filter applied to the tile layer pane for dark/midnight themes
const DARK_TILE_FILTER =
  'brightness(0.55) invert(1) hue-rotate(180deg) saturate(0.65) contrast(0.88)';

// Haversine great-circle distance (km) — pure local calculation, no API
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(a));
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  if (km < 10) return `${km.toFixed(1)} km`;
  return `${Math.round(km)} km`;
}

function formatLocalTime(timezone: string): string {
  try {
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(new Date());
  } catch {
    return '';
  }
}

function applyTileFilter(map: L.Map, isDark: boolean) {
  const pane = map.getPane('tilePane');
  if (pane) {
    (pane as HTMLElement).style.filter = isDark ? DARK_TILE_FILTER : 'none';
  }
}

// Marker icon HTML — improved pill with colored indicator dot
const createMarkerHtml = (
  locName: string,
  pw: TargetPeriodWeather,
  accentColor: string = 'var(--accent)',
  rainColor: string = '#38bdf8',
  isFocal: boolean = false
): string => {
  const temp = Math.round(pw.temperature);
  const rain = pw.precipitation_probability;

  // Condition halo color — derived from temperature to represent weather intensity visually.
  // Hot (>34°C) = amber aura, Cold (<10°C) = icy blue, Rain (>40%) = rain ripple, else = accent
  const haloColor =
    temp >= 34 ? '#f97316'  // hot — orange/amber
    : temp >= 25 ? accentColor  // warm — accent (red in Vandal, blue in Atheris)
    : temp >= 10 ? '#34d399'  // mild — soft emerald
    : '#60a5fa';  // cold — icy blue
  const showRainRipple = rain > 40;
  const rippleVandalClass = rainColor === '#fb923c' ? ' stormops-rain-ripple-vandal' : '';

  const pill = `
    <div style="
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 5px 10px 5px 7px;
      border-radius: 9999px;
      background-color: var(--surface);
      border: 1px solid var(--border);
      color: var(--text-primary);
      box-shadow: 0 4px 16px rgba(0,0,0,0.35);
      font-family: inherit;
      font-size: 12px;
      white-space: nowrap;
      pointer-events: none;
      user-select: none;
    ">
      <span style="
        width: 7px;
        height: 7px;
        border-radius: 9999px;
        background-color: ${accentColor};
        flex-shrink: 0;
        box-shadow: 0 0 5px ${accentColor};
      "></span>
      <span style="font-weight: 700; color: ${accentColor}; letter-spacing: -0.02em;">${temp}&deg;C</span>
      <span style="font-weight: 500; color: var(--text-primary);">${locName}</span>
      <span style="
        font-family: monospace;
        font-size: 9px;
        padding: 1px 5px;
        border-radius: 4px;
        background-color: ${rainColor}1a;
        color: ${rainColor};
        border: 1px solid ${rainColor}38;
      ">${rain}%</span>
    </div>
  `;

  if (!isFocal) return pill;

  // Focal marker: wrap in beacon + halo container
  return `
    <div
      class="stormops-focal-marker"
      style="--marker-accent: ${accentColor};"
    >
      <div class="stormops-condition-halo" style="--halo-color: ${haloColor};"></div>
      ${showRainRipple ? `<div class="stormops-rain-ripple${rippleVandalClass}"></div>` : ''}
      ${pill}
    </div>
  `;
};

// Detailed popup HTML
const createPopupHtml = (
  loc: GeocodedLocationSchema,
  pw: TargetPeriodWeather,
  periodLabel: string
): string => {
  const admin = loc.admin1 ? `, ${loc.admin1}` : '';
  const country = loc.country ? `, ${loc.country}` : '';
  const fullLoc = `${loc.name}${admin}${country}`;
  return `
    <div style="padding: 6px; font-family: inherit; min-width: 180px;">
      <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
        ${fullLoc}
      </div>
      <div style="font-size: 10px; font-family: monospace; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px;">
        ${periodLabel}
      </div>
      <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px;">
        <span style="font-size: 24px; font-weight: 300; color: var(--text-primary);">${Math.round(pw.temperature)}&deg;C</span>
        <span style="font-size: 11px; color: var(--text-secondary); text-transform: capitalize;">${pw.condition}</span>
      </div>
      <div style="font-size: 11px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px; border-top: 1px solid var(--border-muted); padding-top: 6px;">
        <div><span style="color: var(--text-tertiary);">Feels like:</span> ${Math.round(pw.feels_like)}&deg;C</div>
        <div><span style="color: var(--text-tertiary);">Rain:</span> ${pw.precipitation_probability}%</div>
        <div><span style="color: var(--text-tertiary);">Precip:</span> ${pw.precipitation} mm</div>
        <div><span style="color: var(--text-tertiary);">Wind:</span> ${pw.wind_speed} km/h</div>
      </div>
    </div>
  `;
};

// Hover preview card HTML — uses already-available data, zero new API requests
const createHoverPreviewHtml = (
  loc: GeocodedLocationSchema,
  pw: TargetPeriodWeather,
  accentColor: string
): string => {
  const localTime = loc.timezone ? formatLocalTime(loc.timezone) : '';
  const admin = loc.admin1 ? `, ${loc.admin1}` : '';
  const fullLoc = `${loc.name}${admin}`;
  const timeRow = localTime
    ? `<div style="font-size: 10px; font-family: monospace; color: var(--text-tertiary); margin-bottom: 7px;">${localTime} local</div>`
    : '';
  return `
    <div>
      <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 1px;">${fullLoc}</div>
      ${timeRow}
      <div style="display: flex; align-items: baseline; gap: 5px; margin-bottom: 6px;">
        <span style="font-size: 22px; font-weight: 300; color: ${accentColor};">${Math.round(pw.temperature)}&deg;C</span>
        <span style="font-size: 10px; color: var(--text-secondary); text-transform: capitalize;">${pw.condition}</span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 3px; font-size: 10px; color: var(--text-secondary);">
        <div><span style="color: var(--text-tertiary);">Rain</span> ${pw.precipitation_probability}%</div>
        <div><span style="color: var(--text-tertiary);">Wind</span> ${pw.wind_speed} km/h</div>
      </div>
    </div>
  `;
};

// Per-element hover handler registry — prevents duplicate listener accumulation.
// Key: the marker's DOM element. Value: the bound handlers for that element.
type HoverHandlers = {
  onEnter: () => void;
  onLeave: () => void;
  onTouch: (e: Event) => void;
};
const markerHandlers = new WeakMap<HTMLElement, HoverHandlers>();

export function bindAdvisoryLayerInteractivity(
  layer: L.Layer,
  adv: OfficialAdvisory,
  tokens: SeverityThemeTokens,
  isUpcoming: boolean,
  defaultPathOptions: L.PathOptions
) {
  layer.bindTooltip(createAdvisoryTooltipHtml(adv, tokens, isUpcoming), {
    sticky: true,
    direction: 'top',
    offset: [0, -10],
    className: 'stormops-advisory-tooltip',
    opacity: 0.98,
  });

  layer.bindPopup(createAdvisoryPopupHtml(adv, tokens, isUpcoming), {
    maxWidth: 300,
    className: 'stormops-advisory-popup',
  });

  layer.on('click', (e) => {
    L.DomEvent.stopPropagation(e);
  });

  if ('setStyle' in layer && typeof (layer as any).setStyle === 'function') {
    layer.on('mouseover', () => {
      (layer as any).setStyle({
        fillOpacity: isUpcoming ? 0.16 : 0.32,
        weight: ((defaultPathOptions.weight as number) || 2) + 1,
      });
    });
    layer.on('mouseout', () => {
      (layer as any).setStyle(defaultPathOptions);
    });
  }
}

export const WeatherMap: React.FC<WeatherMapProps> = ({
  location,
  weather,
  locationB,
  weatherB,
  periodLabel,
  advisories,
  onCheckWeatherAtCoords,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapWrapperRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const markerBRef = useRef<L.Marker | null>(null);
  const clickMarkerRef = useRef<L.Marker | null>(null);
  const polylineRef = useRef<L.Polyline | null>(null);
  const distanceMarkerRef = useRef<L.Marker | null>(null);
  const advisoryLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const hoverPreviewRef = useRef<HTMLDivElement | null>(null);
  const { theme, darkVariant, accentColor } = useTheme();

  const [mapReady, setMapReady] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAdvisories, setShowAdvisories] = useState(true);

  // Filter advisories that have valid geometry AND are not expired
  const advisoriesWithGeom = useMemo(() => {
    return (advisories || []).filter(
      (adv) => getAdvisoryTemporalState(adv) !== 'EXPIRED' && getAdvisoryGeometryType(adv) !== null
    );
  }, [advisories]);

  const lat = location.latitude;
  const lng = location.longitude;
  const placeName = location.name;
  const isDarkTheme = theme === 'dark' || theme === 'night';

  // Theme-specific accent colors matching design tokens (including Atheris vs Vandal)
  const accentColorA = accentColor;
  const accentColorB =
    theme === 'night' ? '#38bdf8' : theme === 'light' ? '#0284c7' : darkVariant === 'vandal' ? '#fb923c' : '#a78bfa';

  // Rain badge pill color in marker HTML — Vandal = supporting orange, all others = sky blue.
  const rainColorA = darkVariant === 'vandal' ? '#fb923c' : '#38bdf8';
  const rainColorB = darkVariant === 'vandal' ? '#fb923c' : '#38bdf8';


  // ---------------------------------------------------------------------------
  // Hover preview — rendered as a fixed-position overlay via document.body
  // so it is never clipped by the map container's overflow:hidden.
  // ---------------------------------------------------------------------------

  const hideHoverPreview = useCallback(() => {
    if (hoverPreviewRef.current) {
      hoverPreviewRef.current.remove();
      hoverPreviewRef.current = null;
    }
  }, []);

  const showHoverPreview = useCallback(
    (markerEl: HTMLElement, loc: GeocodedLocationSchema, pw: TargetPeriodWeather, accent: string) => {
      hideHoverPreview();

      const markerRect = markerEl.getBoundingClientRect();

      const card = document.createElement('div');
      card.innerHTML = createHoverPreviewHtml(loc, pw, accent);
      // Style the card itself; position fixed so it escapes all overflow clipping
      Object.assign(card.style, {
        position: 'fixed',
        zIndex: '99999',
        background: 'var(--surface-elevated)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '10px 13px',
        minWidth: '168px',
        boxShadow: '0 8px 28px rgba(0,0,0,0.45)',
        fontFamily: 'inherit',
        fontSize: '13px',
        pointerEvents: 'none',
        // Position: above the marker pill, aligned to its left edge
        top: `${markerRect.top - 8}px`,
        left: `${markerRect.left}px`,
        transform: 'translateY(-100%)',
      });

      document.body.appendChild(card);
      hoverPreviewRef.current = card;
    },
    [hideHoverPreview]
  );

  // ---------------------------------------------------------------------------
  // attachHoverEvents — idempotent: removes any previously registered handlers
  // for this DOM element before adding new ones, preventing accumulation.
  // Uses a WeakMap so old elements are GC'd automatically.
  // ---------------------------------------------------------------------------

  const attachHoverEvents = useCallback(
    (marker: L.Marker, loc: GeocodedLocationSchema, pw: TargetPeriodWeather, accent: string) => {
      const el = marker.getElement();
      if (!el) return;

      // Remove any previously registered handlers on this element
      const existing = markerHandlers.get(el);
      if (existing) {
        el.removeEventListener('mouseenter', existing.onEnter);
        el.removeEventListener('mouseleave', existing.onLeave);
        el.removeEventListener('touchstart', existing.onTouch);
      }

      // Create new named handlers (closures capturing current loc/pw/accent)
      const onEnter = () => showHoverPreview(el, loc, pw, accent);
      const onLeave = () => hideHoverPreview();
      const onTouch = (e: Event) => {
        e.stopPropagation();
        if (hoverPreviewRef.current) {
          hideHoverPreview();
        } else {
          showHoverPreview(el, loc, pw, accent);
          setTimeout(hideHoverPreview, 3000);
        }
      };

      el.addEventListener('mouseenter', onEnter);
      el.addEventListener('mouseleave', onLeave);
      el.addEventListener('touchstart', onTouch, { passive: true });

      // Register so next call can remove them
      markerHandlers.set(el, { onEnter, onLeave, onTouch });
    },
    [showHoverPreview, hideHoverPreview]
  );

  // Helper: detach listeners and clear registry for a given element
  const detachHoverEvents = useCallback((el: HTMLElement) => {
    const existing = markerHandlers.get(el);
    if (existing) {
      el.removeEventListener('mouseenter', existing.onEnter);
      el.removeEventListener('mouseleave', existing.onLeave);
      el.removeEventListener('touchstart', existing.onTouch);
      markerHandlers.delete(el);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Comparison overlay helpers
  // ---------------------------------------------------------------------------

  const updateComparisonOverlay = useCallback(
    (map: L.Map, latA: number, lngA: number, latB: number, lngB: number) => {
      if (polylineRef.current) { map.removeLayer(polylineRef.current); polylineRef.current = null; }
      if (distanceMarkerRef.current) { map.removeLayer(distanceMarkerRef.current); distanceMarkerRef.current = null; }

      const distKm = haversineKm(latA, lngA, latB, lngB);
      const distLabel = formatDistance(distKm);

      // Dashed line — geographic separation between the two locations, not a route
      const line = L.polyline(
        [[latA, lngA], [latB, lngB]],
        { color: 'rgba(255,255,255,0.28)', weight: 1.5, dashArray: '5 7', interactive: false }
      ).addTo(map);
      polylineRef.current = line;

      const midLat = (latA + latB) / 2;
      const midLng = (lngA + lngB) / 2;
      const distIcon = L.divIcon({
        className: '',
        html: `<div style="
          padding: 2px 8px;
          border-radius: 9999px;
          background-color: var(--surface);
          border: 1px solid var(--border-muted);
          color: var(--text-tertiary);
          font-family: monospace;
          font-size: 10px;
          white-space: nowrap;
          transform: translate(-50%, -50%);
          pointer-events: none;
          box-shadow: 0 2px 8px rgba(0,0,0,0.28);
        ">${distLabel}</div>`,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });
      const distMarker = L.marker([midLat, midLng], {
        icon: distIcon,
        interactive: false,
        keyboard: false,
      } as L.MarkerOptions).addTo(map);
      distanceMarkerRef.current = distMarker;
    },
    []
  );

  const removeComparisonOverlay = useCallback((map: L.Map) => {
    if (polylineRef.current) { map.removeLayer(polylineRef.current); polylineRef.current = null; }
    if (distanceMarkerRef.current) { map.removeLayer(distanceMarkerRef.current); distanceMarkerRef.current = null; }
  }, []);

  // ---------------------------------------------------------------------------
  // Initialize Leaflet Map (runs once)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [lat, lng],
        zoom: 10,
        zoomControl: true,
        attributionControl: true,
      });

      const tileLayer = L.tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION, maxZoom: 19 }).addTo(map);
      tileLayerRef.current = tileLayer;

      applyTileFilter(map, isDarkTheme);

      // Marker A
      const customIconA = L.divIcon({
        className: 'stormops-weather-marker',
        html: createMarkerHtml(placeName, weather, accentColorA, rainColorA, true),
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });
      const markerA = L.marker([lat, lng], { icon: customIconA }).addTo(map);
      markerA.bindPopup(createPopupHtml(location, weather, periodLabel));
      markerRef.current = markerA;

      // Marker B (comparison)
      if (locationB && weatherB) {
        const customIconB = L.divIcon({
          className: 'stormops-weather-marker-b',
          html: createMarkerHtml(locationB.name, weatherB, accentColorB, rainColorB),
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        });
        const markerB = L.marker([locationB.latitude, locationB.longitude], { icon: customIconB }).addTo(map);
        markerB.bindPopup(createPopupHtml(locationB, weatherB, periodLabel));
        markerBRef.current = markerB;
        map.fitBounds([[lat, lng], [locationB.latitude, locationB.longitude]], { padding: [50, 50] });
        updateComparisonOverlay(map, lat, lng, locationB.latitude, locationB.longitude);
      }

      // Map click — coordinate query
      map.on('click', (e: L.LeafletMouseEvent) => {
        const clickLat = Math.round(e.latlng.lat * 10000) / 10000;
        const clickLng = Math.round(e.latlng.lng * 10000) / 10000;

        if (clickMarkerRef.current) map.removeLayer(clickMarkerRef.current);

        const tempIcon = L.divIcon({
          className: 'stormops-click-pin',
          html: `<div style="width:12px;height:12px;border-radius:50%;background-color:#34d399;border:2px solid #ffffff;box-shadow:0 0 10px rgba(52,211,153,0.8);transform:translate(-50%,-50%);"></div>`,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        });
        const clickMarker = L.marker([clickLat, clickLng], { icon: tempIcon }).addTo(map);
        const popupDiv = document.createElement('div');
        popupDiv.style.padding = '4px';
        popupDiv.style.textAlign = 'center';
        popupDiv.innerHTML = `
          <div style="font-size:11px;font-family:monospace;color:var(--text-secondary);margin-bottom:6px;">${clickLat}, ${clickLng}</div>
          <button id="btn-check-weather-click" style="padding:4px 10px;font-size:11px;font-weight:500;border-radius:8px;background-color:var(--btn-primary-bg);color:var(--btn-primary-text);border:none;cursor:pointer;">Check weather here</button>
        `;
        clickMarker.bindPopup(popupDiv).openPopup();
        clickMarkerRef.current = clickMarker;

        setTimeout(() => {
          const btn = document.getElementById('btn-check-weather-click');
          if (btn && onCheckWeatherAtCoords) {
            btn.onclick = () => { onCheckWeatherAtCoords(clickLat, clickLng); map.closePopup(); };
          }
        }, 50);
      });

      // Dismiss hover preview on map pan/zoom (but not on marker events)
      map.on('movestart', () => hideHoverPreview());

      // Dedicated layer group for official advisories
      const advGroup = L.layerGroup();
      advisoryLayerGroupRef.current = advGroup;
      advGroup.addTo(map);

      mapInstanceRef.current = map;
      setMapReady(true);
    }

    return () => {
      hideHoverPreview();
      if (advisoryLayerGroupRef.current) {
        advisoryLayerGroupRef.current.clearLayers();
        advisoryLayerGroupRef.current = null;
      }
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // ResizeObserver — invalidateSize on container resize
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => { mapInstanceRef.current?.invalidateSize(); });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // ---------------------------------------------------------------------------
  // Synchronize markers and map view when props change.
  // After any setIcon() call, Leaflet replaces the DOM element, so we must
  // re-attach hover listeners. We do so with a short rAF delay so Leaflet
  // has finished inserting the new element before we call getElement().
  // attachHoverEvents() is idempotent — safe to call multiple times.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapReady) return;

    hideHoverPreview();

    if (locationB && weatherB) {
      if (markerRef.current) {
        const oldEl = markerRef.current.getElement();
        if (oldEl) detachHoverEvents(oldEl);
        markerRef.current.setLatLng([lat, lng]);
        markerRef.current.setIcon(L.divIcon({
          className: 'stormops-weather-marker',
          html: createMarkerHtml(placeName, weather, accentColorA, rainColorA, true),
          iconSize: [0, 0], iconAnchor: [0, 0],
        }));
        markerRef.current.getPopup()?.setContent(createPopupHtml(location, weather, periodLabel));
      }

      if (!markerBRef.current) {
        const markerB = L.marker([locationB.latitude, locationB.longitude], {
          icon: L.divIcon({
            className: 'stormops-weather-marker-b',
            html: createMarkerHtml(locationB.name, weatherB, accentColorB, rainColorB),
            iconSize: [0, 0], iconAnchor: [0, 0],
          }),
        }).addTo(map);
        markerB.bindPopup(createPopupHtml(locationB, weatherB, periodLabel));
        markerBRef.current = markerB;
      } else {
        const oldElB = markerBRef.current.getElement();
        if (oldElB) detachHoverEvents(oldElB);
        markerBRef.current.setLatLng([locationB.latitude, locationB.longitude]);
        markerBRef.current.setIcon(L.divIcon({
          className: 'stormops-weather-marker-b',
          html: createMarkerHtml(locationB.name, weatherB, accentColorB, rainColorB),
          iconSize: [0, 0], iconAnchor: [0, 0],
        }));
        markerBRef.current.getPopup()?.setContent(createPopupHtml(locationB, weatherB, periodLabel));
      }

      map.fitBounds([[lat, lng], [locationB.latitude, locationB.longitude]], { padding: [50, 50] });
      updateComparisonOverlay(map, lat, lng, locationB.latitude, locationB.longitude);

      // Re-attach after Leaflet has replaced the DOM element
      requestAnimationFrame(() => {
        if (markerRef.current) attachHoverEvents(markerRef.current, location, weather, accentColorA);
        if (markerBRef.current) attachHoverEvents(markerBRef.current, locationB, weatherB, accentColorB);
      });
    } else {
      if (markerBRef.current) {
        const oldElB = markerBRef.current.getElement();
        if (oldElB) detachHoverEvents(oldElB);
        map.removeLayer(markerBRef.current);
        markerBRef.current = null;
      }
      removeComparisonOverlay(map);
      map.flyTo([lat, lng], 10, { duration: 1.2, easeLinearity: 0.25 });

      if (markerRef.current) {
        const oldEl = markerRef.current.getElement();
        if (oldEl) detachHoverEvents(oldEl);
        markerRef.current.setLatLng([lat, lng]);
        markerRef.current.setIcon(L.divIcon({
          className: 'stormops-weather-marker',
          html: createMarkerHtml(placeName, weather, accentColorA, rainColorA, true),
          iconSize: [0, 0], iconAnchor: [0, 0],
        }));
        markerRef.current.getPopup()?.setContent(createPopupHtml(location, weather, periodLabel));
      }

      requestAnimationFrame(() => {
        if (markerRef.current) attachHoverEvents(markerRef.current, location, weather, accentColorA);
      });
    }

    if (clickMarkerRef.current) { map.removeLayer(clickMarkerRef.current); clickMarkerRef.current = null; }
  }, [lat, lng, locationB?.latitude, locationB?.longitude, weather.temperature, weatherB?.temperature, periodLabel, theme, darkVariant, mapReady]);

  // ---------------------------------------------------------------------------
  // Synchronize Official Advisories into advisoryLayerGroup (Rules 1-4)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const advGroup = advisoryLayerGroupRef.current;
    if (!advGroup || !mapReady) return;

    advGroup.clearLayers();

    if (!advisories || advisories.length === 0) return;

    for (const adv of advisories) {
      const temporalState = getAdvisoryTemporalState(adv);
      // Do not create visual overlays for expired advisories
      if (temporalState === 'EXPIRED') continue;

      const geomType = getAdvisoryGeometryType(adv);
      if (!geomType) continue; // Rule 4: state/district/subdivision only without geometry

      const isUpcoming = temporalState === 'UPCOMING';
      const tokens = getSeverityTokens(adv.severity);
      const pathOptions: L.PathOptions = {
        color: tokens.stroke,
        weight: isUpcoming ? 1.5 : 2,
        opacity: isUpcoming ? 0.65 : 0.95,
        fillColor: tokens.stroke,
        fillOpacity: isUpcoming ? 0.08 : 0.18,
        dashArray: isUpcoming ? '4 5' : undefined,
      };

      if (geomType === 'polygon') {
        try {
          const parsed =
            typeof adv.polygon_geojson === 'string'
              ? JSON.parse(adv.polygon_geojson)
              : adv.polygon_geojson;
          const geoLayer = L.geoJSON(parsed, {
            style: () => pathOptions,
            onEachFeature: (_feature, layer) => {
              bindAdvisoryLayerInteractivity(layer, adv, tokens, isUpcoming, pathOptions);
            },
          });
          if (geoLayer.getLayers().length === 0) {
            bindAdvisoryLayerInteractivity(geoLayer, adv, tokens, isUpcoming, pathOptions);
          }
          advGroup.addLayer(geoLayer);
        } catch (err) {
          console.warn('Failed to parse and render advisory polygon GeoJSON:', adv.id, err);
        }
      } else if (geomType === 'circle') {
        const circle = L.circle([adv.latitude!, adv.longitude!], {
          radius: adv.radius_km! * 1000,
          ...pathOptions,
        });
        bindAdvisoryLayerInteractivity(circle, adv, tokens, isUpcoming, pathOptions);
        advGroup.addLayer(circle);
      } else if (geomType === 'point') {
        const markerIcon = L.divIcon({
          className: 'stormops-advisory-marker',
          html: createAdvisoryMarkerHtml(tokens, isUpcoming),
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const marker = L.marker([adv.latitude!, adv.longitude!], {
          icon: markerIcon,
          zIndexOffset: 500,
        });
        bindAdvisoryLayerInteractivity(marker, adv, tokens, isUpcoming, pathOptions);
        advGroup.addLayer(marker);
      }
    }
  }, [advisories, mapReady]);

  // ---------------------------------------------------------------------------
  // Toggle Advisory Layer Group visibility
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const map = mapInstanceRef.current;
    const advGroup = advisoryLayerGroupRef.current;
    if (!map || !advGroup) return;

    if (showAdvisories) {
      if (!map.hasLayer(advGroup)) {
        advGroup.addTo(map);
      }
    } else {
      if (map.hasLayer(advGroup)) {
        map.removeLayer(advGroup);
      }
    }
  }, [showAdvisories, mapReady]);

  // ---------------------------------------------------------------------------
  // Theme change — update tile filter + invalidateSize
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!tileLayerRef.current || !mapInstanceRef.current) return;
    tileLayerRef.current.setUrl(TILE_URL);
    applyTileFilter(mapInstanceRef.current, isDarkTheme);
    mapInstanceRef.current.invalidateSize();
  }, [theme, isDarkTheme]);

  // ---------------------------------------------------------------------------
  // Fullscreen toggle — invalidate size after CSS transition completes
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const timer = setTimeout(() => { mapInstanceRef.current?.invalidateSize(); }, 120);
    return () => clearTimeout(timer);
  }, [isExpanded]);

  const handleRecenter = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.flyTo([lat, lng], 10);
  };

  const handleExpandToggle = () => {
    hideHoverPreview();
    setIsExpanded((prev) => !prev);
  };

  return (
    <div
      className={isExpanded
        ? 'fixed inset-0 z-[9000] flex flex-col bg-[var(--bg)] p-3 sm:p-4'
        : 'space-y-3 pt-4'}
      style={isExpanded ? undefined : { borderTop: '1px solid var(--border-muted)' }}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
        <span className="flex items-center gap-1.5 font-medium">
          <MapPin className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
          INTERACTIVE WEATHER MAP
          {locationB && (
            <span
              className="ml-2 font-mono text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: 'var(--surface-elevated)', border: '1px solid var(--border-muted)', color: 'var(--text-tertiary)' }}
            >
              COMPARISON
            </span>
          )}
        </span>

        <div className="flex items-center gap-2">
          {advisoriesWithGeom.length > 0 && (
            <button
              type="button"
              onClick={() => setShowAdvisories((prev) => !prev)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono border cursor-pointer transition-colors"
              style={{
                backgroundColor: showAdvisories ? 'rgba(244, 63, 94, 0.10)' : 'var(--surface-elevated)',
                borderColor: showAdvisories ? 'rgba(244, 63, 94, 0.30)' : 'var(--border-muted)',
                color: showAdvisories ? '#f43f5e' : 'var(--text-secondary)',
              }}
              title={showAdvisories ? 'Hide official advisories on map' : 'Show official advisories on map'}
              aria-label="Toggle official advisories on map"
            >
              <ShieldAlert className="w-3 h-3" />
              <span>{showAdvisories ? 'Advisories On' : 'Advisories Off'}</span>
              <span
                className="font-mono text-[9px] px-1.5 py-0.2 rounded-full"
                style={{
                  background: showAdvisories ? 'rgba(244, 63, 94, 0.20)' : 'var(--surface)',
                  border: '1px solid var(--border-muted)',
                  color: showAdvisories ? '#f43f5e' : 'var(--text-tertiary)',
                }}
              >
                {advisoriesWithGeom.length}
              </span>
            </button>
          )}
          <button
            type="button"
            onClick={handleRecenter}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-mono border cursor-pointer transition-colors"
            style={{ backgroundColor: 'var(--surface-elevated)', borderColor: 'var(--border-muted)', color: 'var(--text-secondary)' }}
            title="Recenter map on selected location"
          >
            <Compass className="w-3 h-3" /> Recenter
          </button>
          <button
            type="button"
            onClick={handleExpandToggle}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-mono border cursor-pointer transition-colors"
            style={{ backgroundColor: 'var(--surface-elevated)', borderColor: 'var(--border-muted)', color: 'var(--text-secondary)' }}
            title={isExpanded ? 'Exit fullscreen map' : 'Expand map'}
          >
            {isExpanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Map Element Container */}
      <div
        ref={mapWrapperRef}
        className={`w-full rounded-2xl overflow-hidden relative shadow-inner ${isExpanded ? 'flex-1' : 'h-[300px] sm:h-[340px]'}`}
        style={{ border: '1px solid var(--border)' }}
      >
        <div ref={mapContainerRef} className="w-full h-full z-0" />
      </div>
    </div>
  );
};

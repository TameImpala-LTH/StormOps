# UI-07 — Spatial Intelligence / Map Implementation Report

**Status:** Completed  
**Release Target:** StormOps Spatial Context Layer  
**Git Commit Target:** `feat: elevate map to spatial intelligence surface`  
**Dependencies:** UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-06.1, UI-06.2  

---

## 1. Architectural Role in the 4-Level Intelligence Hierarchy

StormOps organizes conversational weather intelligence through four structured layers:

1. **WHAT MATTERS** (`WeatherGPT` Hero Briefing): Rapid executive synthesis, situation headline, scannable briefing text, and expandable deep interpretation.
2. **WHY** (`Telemetry Surface`): Instant physical validation displaying temperature, rain risk, wind speed, and relative humidity in a balanced 4-column telemetry grid.
3. **WHEN** (`24-Hour Forecast Intelligence`): Continuous temporal evolution showing hourly progression, peak events, thermal curves, and precipitation bars.
4. **WHERE** (`Spatial Intelligence / Map`): Grounded geographic orientation providing spatial context, local administrative breadcrumbs, focal visual anchor, and official environmental advisory geometry.

The map is **not** an ornamental interactive dashboard widget; it answers the user's implicit question: *"Where specifically does this weather situation apply, and what official advisory zones encompass or border my location?"*

---

## 2. Location Identity Strategy

- **Zero Re-geocoding:** The map strictly consumes the pre-resolved `GeocodedLocationSchema` object (`location.name`, `admin1`, `country`, `latitude`, `longitude`) already established during search resolution. No reverse geocoding or secondary lookup requests are dispatched.
- **Hierarchy Breadcrumbs:** The map section header explicitly displays resolved administrative breadcrumbs:
  `[Name] · [Admin1 / State] · [Country] — Geographic orientation & official advisory coverage`
- **Identity Integrity:** Coordinates and location names are guaranteed to match the briefing and telemetry without coordinate jitter or mismatched place names.

---

## 3. Camera Behavior & Recenter Interaction

- **Granularity-Driven Initial Zoom (`getOptimalZoom`):**
  - Locality / Neighborhood (`loc.locality` present): **Zoom Level 12** (~5 km extent).
  - City / District (`loc.city` or `loc.district` present): **Zoom Level 11** (~15 km extent).
  - State / Country / Broad Region: **Zoom Level 10** (~40 km extent).
- **Centering & Bounds:**
  - In single location mode, camera centers immediately on `[latitude, longitude]`.
  - In comparison mode (Location A vs Location B), camera automatically fits bounds (`map.fitBounds([pointA, pointB], { padding: [40, 40], maxZoom: 13 })`).
- **Recenter Control:** An accessible header button (`aria-label="Recenter map on current location"`) smoothly pans and zooms back to the primary location without page reload.

---

## 4. Visual Anchor Marker (Focal Marker)

The selected location is marked with a distinctive, high-clarity focal marker:
- **Dual-Ring Pulsing Beacon:** Concentric animated rings highlight the exact geocoded coordinate.
- **Condition Aura (Halo):** A luminous thermal aura radiates outward based on temperature intensity.
- **Telemetry Pill:** Elevated chip presenting:
  - Theme accent indicator dot.
  - Bold temperature numeral (`${temp}°C`).
  - Escaped place name label (`locName`).
  - Precipitation probability pill (`${rain}%` in blue or orange accent if rain risk > 0%).
- **Accessibility & Motion:** All marker pulse and ripple animations are disabled when `@media (prefers-reduced-motion: reduce)` is active.

---

## 5. Condition Aura Scale

The condition aura visually translates weather intensity into spatial thermal signatures:
- **Hot (`>= 34°C`):** Radiant amber halo (`#f97316`).
- **Warm (`>= 24°C`):** Theme accent halo (`var(--accent-primary)`).
- **Mild (`>= 10°C`):** Soft emerald halo (`#34d399`).
- **Cold (`< 10°C`):** Crisp cyan/ice blue halo (`#60a5fa`).
- **Rain Pulse (`precipitation_probability > 40%`):** Hydro-dynamic radial ripple indicating elevated rainfall probability.

Crucially, these auras are restricted to the marker anchor and do **not** paint fake pseudo-radar gradients across the surrounding map geography.

---

## 6. Atmospheric Overlay & Basemap Styling

- **Single Basemap Provider:** Standard OpenStreetMap tile URL (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) with standard attribution.
- **Dedicated Atmospheric Pane:** Custom Leaflet pane `atmosphericPane` (zIndex 250, positioned between `tilePane` at 200 and vector overlays at 400).
- **Theme-Specific Tile CSS Filters:**
  - *Light Mode:* Natural, unfiltered OSM basemap.
  - *Atheris (Default Dark):* `brightness(0.48) invert(1) hue-rotate(180deg) saturate(0.55) contrast(0.88)` with cool blue-grey atmospheric tint.
  - *Vandal (Dark Alt):* `brightness(0.42) invert(1) hue-rotate(145deg) saturate(0.60) contrast(0.90) sepia(0.18)` with deep burgundy/maroon atmospheric tint.
  - *Midnight / Night:* `brightness(0.38) invert(1) hue-rotate(210deg) saturate(0.50) contrast(0.85) sepia(0.12)` with cosmic purple tint.
- **Label Legibility:** The atmospheric overlay uses `mix-blend-mode: color` and `pointer-events: none`, preserving street line and geographical label contrast without darkening vectors.

---

## 7. Official Advisories: Rules 1–4 Geometry & Immutable Severity Colors

Advisory geometry is parsed and rendered according to strict spatial integrity rules:
- **Rule 1 (GeoJSON Polygon):** If `polygon_geojson` exists, parsed and rendered as an exact Leaflet `geoJSON` polygon layer.
- **Rule 2 (Coordinate + Radius Circle):** If `latitude`, `longitude`, and `radius_km` (> 0) exist, rendered as an exact Leaflet `circle` with metric radius `radius_km * 1000`.
- **Rule 3 (Coordinate Point):** If `latitude` and `longitude` exist without radius, rendered as an advisory warning marker.
- **Rule 4 (Regional/District/Subdivision Text-Only):** If no spatial geometry is available, **zero synthetic polygons are fabricated**. Non-spatial advisories are reported via textual advisory cards in the header/briefing.

### Immutable Severity Tokens
To ensure emergency clarity across all color themes:
- **Red (Warning):** Stroke `#f43f5e`, Fill `rgba(244, 63, 94, 0.20)`, Badge `#f43f5e`.
- **Orange (Alert):** Stroke `#f97316`, Fill `rgba(249, 115, 22, 0.16)`, Badge `#f97316`.
- **Yellow (Watch):** Stroke `#eab308`, Fill `rgba(234, 179, 8, 0.12)`, Badge `#eab308`.
- **Green (No Warning):** Stroke `#10b981`, Fill `rgba(16, 185, 129, 0.08)`, Badge `#10b981`.

### Active vs Upcoming Temporal Differentiation
- **Active Advisory:** Solid perimeter stroke (`dashArray: undefined`), solid beacon border, full opacity.
- **Upcoming Advisory:** Dashed perimeter stroke (`dashArray: "6, 6"`), dashed warning marker border, subtle 75% opacity, and clear `(UPCOMING)` badge indicator.

---

## 8. Advisory Popups & Interactions

- **Hover Previews:** Hovering over an advisory polygon or marker presents an instantaneous summary tooltip showing severity badge, issuing authority (e.g., IMD), headline, and validity window.
- **Full Interactive Popups:** Clicking an advisory displays full structured details:
  - Hazard severity level and authority.
  - Headline and comprehensive hazard description.
  - Action guidance callout box.
  - Official source external link (`rel="noopener noreferrer"` with `escapeHtml` sanitation).

---

## 9. Comparison Mode (Dual Markers A & B)

When `locationB` and `weatherB` are supplied:
- **Dual Visual Anchors:** Marker A (Theme primary accent) and Marker B (Theme secondary accent).
- **Geodesic Connector Polyline:** Styled dashed polyline connecting Point A and Point B.
- **Distance Pill:** Centered mid-point marker computing exact Haversine great-circle distance locally (`formatDistance(haversineKm(...))`).
- **Camera Auto-Fitting:** Calls `map.fitBounds()` to comfortably encompass both geographic coordinates with 40px viewport padding.
- **Comparison Legend & Header:** Header displays `Comparison: A vs B` pill badge and dual legend markers.

---

## 10. Fullscreen Exploration Mode

- **Toggle Control:** Accessible expand/minimize button (`aria-label="Expand map fullscreen"`).
- **Container Sizing:**
  - Inline default: `h-[320px]` (mobile), `sm:h-[380px]` (tablet), `lg:h-[420px]` (desktop).
  - Fullscreen: Fixed viewport overlay (`fixed inset-0 z-50 rounded-none w-screen h-screen`).
- **Keyboard Dismissal:** Global `Escape` key event listener gracefully exits fullscreen mode.
- **ResizeObserver Integration:** Automatically fires `map.invalidateSize()` upon size transitions.

---

## 11. Mobile Experience

- **Responsive Viewport Height:** Scaled to `320px` on small devices, preventing vertical scroll hijacking.
- **Touch Gestures:** Native Leaflet multi-touch pan and pinch-to-zoom preserved.
- **Compact Controls:** Touch-friendly buttons (minimum 36x36px hit targets) with high-contrast active states.
- **Single-Column Mobile Stack:** Map cleanly stacks below the 24-hour forecast chart with consistent UI-03 padding and token spacing.

---

## 12. Accessibility (a11y)

- **Semantic Role & Labels:** Map wrapper marked with `role="region"` and `aria-label="Interactive weather and advisory map"`.
- **Keyboard Operable:** All controls (Recenter, Fullscreen, Advisory Toggle) are native `<button>` elements with distinct `:focus-visible` rings.
- **Reduced Motion Support:** `@media (prefers-reduced-motion: reduce)` added in `App.css` to disable marker pulses and ripple animations.
- **XSS Sanitation:** All dynamic strings in Leaflet HTML markers, tooltips, and popups are passed through `escapeHtml()`.

---

## 13. Compact Inline Legend

Discreetly positioned below the map canvas:
- `● Selected location` (with theme-accurate beacon dot)
- `▱ Official advisory` (with official amber warning outline)
- `● Comparison location` (active in comparison mode)

Eliminates ambiguous cartographic symbology without obstructing the map viewport.

---

## 14. Anti-Patterns Explicitly Avoided

1. **No Fake Radar / Simulated Precipitation:** Synthetic Doppler radar overlays were strictly omitted because StormOps does not ingest calibrated real-time NEXRAD/Doppler feeds.
2. **No Wind Streamlines / Particle Simulations:** Animated wind particles consume excessive CPU/GPU cycles and mislead users regarding localized gust dynamics.
3. **No Uncalibrated Satellite Layers:** Satellite imagery without cloud-top temperature calibration adds visual noise without actionable utility.
4. **No Re-geocoding Overhead:** Zero reverse geocoding API calls during map drag, hover, or zoom.

---

## 15. Network Performance

- **Zero Interaction Requests:** Panning, zooming, marker hover, popup opening, and fullscreen toggling generate **0 backend API requests**.
- **Tile Caching:** Standard browser caching for OpenStreetMap raster tiles.
- **Lazy Loaded:** In `WeatherAnswerSurface.tsx`, `WeatherMap` is dynamically imported (`React.lazy`), keeping initial bundle overhead minimal.

---

## 16. Component File Structure

- **Core Component:** `frontend/src/components/WeatherMap.tsx` (1,260 lines).
- **Test Suite:** `frontend/src/components/WeatherMap.test.tsx` (243 lines, 8 test cases).
- **Style Additions:** `frontend/src/App.css` (reduced motion media queries).
- **Exported Interfaces & Helpers:**
  - `WeatherMapProps`
  - `getAdvisoryGeometryType`
  - `getSeverityTokens`
  - `escapeHtml`, `formatAdvisoryTime`
  - `createMarkerHtml`, `createPopupHtml`
  - `getOptimalZoom`, `bindAdvisoryLayerInteractivity`
  - `TILE_URL`, `TILE_ATTRIBUTION`

---

## 17. Test Coverage

- **Frontend Vitest Suites:** 7 test files, 68 tests passing (100% green).
  - `WeatherMap.test.tsx`: 8 dedicated tests validating header, breadcrumbs, legend, advisory toggle, fullscreen Escape key, optimal zoom, marker HTML generation, popup generation, comparison mode, and XSS sanitization.
  - `advisory.test.tsx`: 30 tests validating all geometry rules (1–4), severity token mappings, and temporal states.
- **Backend Pytest Suites:** 421 tests passing (100% green).

---

## 18. Responsive Breakpoint Matrix

| Viewport | Container Height | Legend Placement | Header Controls |
| :--- | :--- | :--- | :--- |
| **Mobile (<640px)** | `320px` | Inline wrap below map | Compact icon + text buttons |
| **Tablet (640px–1024px)** | `380px` | Inline flex below map | Full button labels |
| **Desktop (>1024px)** | `420px` | Inline flex below map | Full button labels with breadcrumbs |
| **Fullscreen** | `100vh` / `100vw` | Fixed bottom overlay | Recenter + Exit fullscreen controls |

---

## 19. Cross-Browser & Cross-Theme Verification

- **Theme Switching:** Seamless transition between `light`, `atheris`, `vandal`, and `midnight` without re-mounting Leaflet map or resetting camera.
- **Atmospheric Pane Blending:** Verified that street labels remain legible through the dark inverted CSS filter across Chromium, Firefox, and WebKit rendering engines.
- **Resize Handling:** Guarded against missing `ResizeObserver` in older runtimes and JSDOM environments.

---

## 20. Backward Compatibility

All functions previously consumed by `src/components/advisory/advisory.test.tsx` (`getAdvisoryGeometryType`, `getSeverityTokens`, `escapeHtml`, `formatAdvisoryTime`, `bindAdvisoryLayerInteractivity`) remain exported with identical signatures and return contracts. All 30 advisory tests pass unconditionally.

---

## 21. UI-03 Design Token Adherence

- Surface tokens: `bg-surface-primary`, `bg-surface-secondary`, `bg-surface-tertiary`.
- Border tokens: `border-border-default`, `border-border-subtle`.
- Text tokens: `text-text-primary`, `text-text-secondary`, `text-text-tertiary`.
- Radius tokens: `rounded-xl`, `rounded-full`.
- Font tokens: Monospace coordinates and telemetry numeral readouts (`font-mono`).

---

## 22. Key User Scenarios Walkthrough

1. **Standard Search (Single Location):** User searches "Kolkata". Map initializes at zoom 11, centers on Kolkata, places focal beacon with temperature and rain probability, and applies Atheris cool dark overlay.
2. **Advisory Active (Emergency Context):** Severe rain warning issued by IMD for Kolkata. Map renders orange polygon zone over district. Hovering highlights zone; clicking reveals official advisory guidance and source link.
3. **Comparison Search (Kolkata vs Mumbai):** Both locations rendered with dual beacons (A and B). Connector line draws distance metric (`1,659 km`). Camera automatically fits both cities into view.
4. **Deep Spatial Exploration:** User clicks "Expand". Map expands into edge-to-edge fullscreen canvas. User freely pans/zooms; pressing `Escape` instantly returns to inline reading position.

---

## 23. Next Phase Readiness: UI-08 (Advisories / Safety Surface)

With the spatial representation of advisories solidly established in UI-07, the product is now prepared for UI-08:
- Deep integration between Map advisory polygons and the dedicated Environmental Advisory drawer/surface.
- Cross-surface highlighting: clicking an advisory card in the briefing smoothly pans the map camera to the affected polygon zone.
- Comprehensive safety action protocols aligned with official meteorological authorities (IMD, NOAA, ECMWF).

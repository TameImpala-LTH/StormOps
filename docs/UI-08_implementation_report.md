# Phase UI-08 Implementation Report — Official & Environmental Intelligence

## 1. Existing Advisory UI Audit
Prior to UI-08, StormOps possessed multiple disconnected surfaces surfacing alerts and advisories:
- **`WeatherAnswerSurface`**: Placed `OfficialAdvisorySection` *before* the `WeatherMap`, breaking the primary product hierarchy (What Matters → Why → When → Where → Detail/Official). It also allowed full duplicate cards below when active severe advisories were promoted above `WeatherGPTHero`.
- **`OfficialAdvisoryBanner`**: Rendered prominently above `WeatherGPTHero` for active Red/Orange alerts, but did not exclude non-meteorological bulletins such as AQI from storm warnings.
- **`OfficialAdvisorySection`**: Exhibited card-stack clutter when multiple advisories existed, rendering all full descriptions and public guidance simultaneously with no scannable collapse mechanism.
- **`OfficialAdvisoryCard`**: Rendered full descriptive text without inline truncation or read-more disclosure, creating tall text blocks.
- **`AirQualityCard`**: Risked blending with storm warnings unless strictly demarcated as continuous ambient environmental measurement.
- **`EnvironmentalEventIndicator`**: Used a notification bell with an unread message badge style dot, communicating generic alert counts rather than clear semantic availability.
- **`EnvironmentalEventPanel`**: Combined advisories, AQI, and civic events into tabs, but required clear demarcation of government authoritative warnings versus contextual regional cultural periods.

---

## 2. Final Information Hierarchy
The StormOps weather intelligence page now follows a strict, deliberate progression:

```
WHAT MATTERS
↓ WeatherGPT Hero (AI synthesis & practical interpretation)

WHY
↓ Core Weather Telemetry (Observation strip: Temp, Rain, Wind, Humidity)

WHEN
↓ 24-Hour Forecast (Hourly progression & scrubber inspection)

WHERE
↓ Location Map (Dark cartography & advisory geometry)

OFFICIAL INFORMATION
↓ Official Government Advisories & Environmental Measurements
```

**Exception (Top Promotion)**:
- Genuinely severe ACTIVE official weather advisories (Red Warning or Orange Alert) are promoted immediately above `WeatherGPTHero` via `OfficialAdvisoryBanner` to ensure urgent safety information cannot be missed.
- The lower `OFFICIAL INFORMATION` section deduplicates this warning with a concise reference strip, avoiding repetitive walls of text.

---

## 3. Zero-State Behavior
- When no active official advisories, no upcoming advisories, and no AQI data exist:
  - If `showEmptyState` is false (default for normal weather queries): renders `null` completely. Zero vertical pixels wasted.
  - If `showEmptyState` is explicitly true: renders an ultra-quiet, restrained single-line badge:
    `[ShieldCheck] OFFICIAL CONDITIONS · No active official advisories are currently available for this location.`
  - No large 32px+ empty cards, no alarming "No alerts" or "All clear" dashboard banners. The absence of warnings feels quiet and calm.

---

## 4. Active Advisory Behavior
- When a single active official advisory exists:
  - Renders as a crisp, authoritative government bulletin.
  - Top header: `OFFICIAL · [AUTHORITY]` (e.g. `OFFICIAL · IMD`) + `AdvisorySeverityBadge` (`RED · WARNING` or `ORANGE · ALERT`).
  - Headline: High-contrast title (`Extremely Heavy Rainfall Expected in Kolkata`).
  - Validity window & geographic scope: `Kolkata, West Bengal · Valid until 11:25 PM`.
  - Official public guidance: Displayed in a dedicated amber box strictly when supplied by authoritative data (`Avoid stepping outdoors unless strictly emergency...`).
  - Source attribution: Safe external link to the issuing portal (`Source: India Meteorological Department (IMD) Official Portal ↗`).

---

## 5. Multiple Advisory Behavior
- When multiple advisories exist (>= 2):
  - **Default Collapsed State**: Renders a compact, scannable list grouped by temporal status (`ACTIVE ADVISORIES NOW` and `UPCOMING WATCHES & ADVANCE ALERTS`).
  - Each item displays: Severity badge, headline, authority, location, and validity time on a single line.
  - **Disclosure Toggle**: An accessible button labeled `View all official advisories (N)` with `aria-expanded="false"` allows the user to inspect full details on demand.
  - **Expanded State**: Expands full `OfficialAdvisoryCard`s with smooth animation and individual read-more disclosure for long descriptions.

---

## 6. Promotion Behavior
- `OfficialAdvisoryBanner` automatically promotes active Red and Orange meteorological advisories above `WeatherGPTHero`.
- Non-severe advisories (Yellow Watch, Green Informational) and non-meteorological air quality bulletins remain in the lower `OFFICIAL INFORMATION` section and are never promoted to the emergency top slot.

---

## 7. Deduplication Behavior
- If an advisory is promoted above `WeatherGPTHero`, its ID is tracked via `promotedAdvisoryIds`.
- In the lower `OFFICIAL INFORMATION` section:
  - In multi-advisory collapsed view: Marked with a subtle badge `Surfaced in alert banner ↑`.
  - In single-card or expanded view: Renders as a compact reference row linking directly to the issuing portal, without repeating the long description and action guidance.
- Eliminates duplicated text blocks while preserving clear spatial and official context.

---

## 8. Upcoming & Expired Behavior
- **Upcoming Advisories**:
  - Visually secondary with yellow/amber accents (`rgba(234,179,8,0.25)`).
  - Labeled `UPCOMING WATCHES & ADVANCE ALERTS`.
  - Clear future validity cues: `Starts [Time] · [Date]`.
  - Never promoted into the emergency banner above WeatherGPT.
- **Expired Advisories**:
  - Filtered out via `getAdvisoryTemporalState(a) !== 'EXPIRED'`.
  - Strictly excluded from active and upcoming warning sections.

---

## 9. Official Source Treatment
- Every advisory prominently displays its verified issuing authority:
  - `OFFICIAL · IMD` (India Meteorological Department)
  - `OFFICIAL · NDMA SACHET` (National Disaster Management Authority)
  - `OFFICIAL · INCOIS` (Indian National Centre for Ocean Information Services)
  - `OFFICIAL · CPCB` (Central Pollution Control Board)
- External links to official portals use secure attributes: `target="_blank"` and `rel="noopener noreferrer"`.
- Raw URLs are never displayed.

---

## 10. Air Quality (AQI) Treatment
- Air quality is strictly demarcated as an environmental measurement bulletin, separate from weather warnings:
  - Heading: `AIR QUALITY BULLETIN` / `Continuous Ambient Air Quality Monitoring (CPCB)`.
  - Displays National Air Quality Index (NAQI) category and numeric score (e.g. `412 SEVERE`).
  - Colors follow official NAQI brackets: Severe (`#991b1b`), Very Poor (`#f43f5e`), Poor (`#f97316`), Moderate (`#eab308`), Satisfactory (`#10b981`), Good (`#059669`).
  - Filtered out of severe weather alert banners.
  - If AQI data is unavailable: the card is completely omitted (no empty placeholder or fabrication).

---

## 11. Civic & Event Treatment
- Contextual civic and cultural events (e.g. Durga Puja, regional festivals) are classified under `Civic & Events` in `EnvironmentalEventPanel`.
- Labeled as `StormOps Curated Contextual Periods`, never as government safety warnings.
- Quiet state when no events exist.

---

## 12. WeatherGPT Relationship
- WeatherGPT text represents AI synthesis and practical daily recommendations (e.g., commute, umbrella timing).
- Official advisories represent authoritative government warnings (e.g., IMD extreme weather bulletins).
- WeatherGPT never claims to be an official warning, and official bulletins are never modified by the AI.

---

## 13. Map Relationship
- The `WeatherMap` renders *before* `OfficialAdvisorySection`.
- The map provides spatial advisory context (official polygon coverage, circle radii, and advisory marker pins).
- The official advisory cards provide textual bulletin details (authority, headline, public guidance, validity).
- No miniature maps are embedded inside advisory cards.

---

## 14. Theme Behavior & Color Invariance
- **Official Severity Colors Are Immutable**:
  - Red: `#f43f5e`
  - Orange: `#f97316`
  - Yellow: `#eab308`
  - Green: `#10b981`
- **Vandal Product Accent vs Official Severity**:
  - Vandal product accent is neon red (`#ff2a55`), reserved for UI chrome and telemetry accents.
  - Official warning borders, text, and badges strictly use `#f43f5e`, ensuring semantic distinction between StormOps styling and government emergency warnings.
- **Atheris, Midnight, Light**:
  - Atheris cyan (`#38bdf8`), Midnight amber (`#f59e0b`), and Light emerald (`#10b981`) apply to StormOps chrome; official severity colors remain identical across all themes.

---

## 15. Accessibility
- Severity is communicated textually (`WARNING (TAKE ACTION)`, `ALERT (BE PREPARED)`, `WATCH (BE UPDATED)`), not by color alone.
- Disclosure toggles use valid `aria-expanded` attributes.
- Semantic HTML tags (`<article>`, `<aside>`, `<section>`, `<button>`) with clear `aria-label`s.
- External links include `aria-label` stating that a new tab will open.
- Full keyboard tab navigation with visible focus outlines.

---

## 16. Mobile Responsiveness
- Tested and verified on 375px, 390px, and 430px viewports.
- Header semantic indicator pill wraps gracefully alongside location identity.
- Single-line compact items stack vertically on narrow screens without horizontal clipping.
- Tap targets meet 44px touch guidelines with ample spacing.

---

## 17. Desktop Responsiveness
- Tested and verified on 1024px, 1280px, 1366px, 1440px, and 1920px viewports.
- Uses max-width constraints, avoiding full-width text walls.
- Information density is balanced with generous whitespace.

---

## 18. Performance
- No additional network requests or provider API calls.
- Pure client-side memoization for filtering unexpired, severe, and AQI bulletins.
- Zero refetching on accordion expansion, tab switching, or theme toggling.

---

## 19. Tests
- **Vitest**: 80/80 tests passing across 7 test suites.
  - `advisory.test.tsx` expanded with 9 new UI-08 invariant test cases covering zero state, single active, multi-advisory scannable list, expansion toggle, deduplication, safe links, read more disclosure, immutable severity colors, AQI separation, and semantic indicators.
- **Backend Pytest**: 421/421 tests passing (100% green).

---

## 20. Build Verification
- Production build succeeded cleanly via `tsc -b && vite build`.
- 0 TypeScript compilation errors, 0 linter warnings.

---

## 21. Manual Visual Validation
- Visual verification performed via headless Edge across 10 scenarios:
  1. `ui08_zero_desktop.png`: Calm, clean normal weather view with zero wasted vertical space.
  2. `ui08_zero_mobile.png`: Clean 390px mobile view with quiet zero state.
  3. `ui08_single_active_vandal_desktop.png`: Promoted top banner + compact deduplicated reference in lower section.
  4. `ui08_single_active_vandal_mobile.png`: Responsive stacking of alert banner and location identity.
  5. `ui08_multiple_active_vandal_desktop.png`: Compact scannable list with disclosure toggle.
  6. `ui08_upcoming_vandal_desktop.png`: Secondary yellow watch card below map; no false top promotion.
  7. `ui08_aqi_vandal_desktop.png`: Distinct CPCB NAQI bulletin below map; no false storm banner.
  8. `ui08_single_active_atheris.png`: Atheris cyan chrome with immutable official red warning colors.
  9. `ui08_single_active_midnight.png`: Midnight violet/amber chrome with immutable official red warning colors.
  10. `ui08_single_active_light.png`: Daylight surface with immutable official red warning colors.

---

## 22. Deviations from Initial Plan
- Air quality bulletins were explicitly excluded from top-level `OfficialAdvisoryBanner` promotion to prevent ambient air pollution readings from masquerading as urgent meteorological storm warnings.

---

## 23. Deferred Work
- Real-time push notification streaming for advisories (to be considered in future backend phases).
- Dynamic polygon drawing tools for custom user alert subscriptions (post-v1 roadmap).

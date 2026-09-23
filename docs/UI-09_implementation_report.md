# UI-09 Implementation Report

## Implemented

### 1. Mobile Header Search Access (HIGH)
- **File**: `frontend/src/components/Header.tsx`
- Added a `useIsMobile()` hook (threshold: 768px) using `window.innerWidth` and a `resize` event listener.
- In result state on mobile (`isMobile && searchSlot`), renders a compact **magnifying glass icon button** in the right-side header strip with `aria-expanded` and `aria-label="Search location or weather"`.
- Clicking toggles `isMobileSearchOpen`. The `X` icon replaces the `Search` icon when the panel is open (`aria-label="Close search"`).
- The `QueryInput` (`searchSlot`) is conditionally rendered below the header bar only when `isMobile && isMobileSearchOpen` — preventing any duplicate search inputs.
- On desktop/tablet (`!isMobile`), the docked search input renders directly inline in the center header zone without any toggle button.
- `Escape` key closes the mobile search overlay; brand logo click also closes it.
- **No header height increase** when the search is closed; only the header bottom area expands when open.

### 2. Forecast Telemetry Scrubbing Status Cue (MEDIUM)
- **Files**: `frontend/src/components/briefing/WeatherTelemetry.tsx`, `frontend/src/components/WeatherAnswerSurface.tsx`
- `inspectedTimeStr` in `WeatherAnswerSurface.tsx` now passes a 24-hour `HH:MM` string (`t.split('T')[1].slice(0,5)`) directly to `WeatherTelemetry`.
- `WeatherTelemetry.tsx` renders a subtle `FORECAST · HH:MM` status row above the telemetry grid whenever `inspectedTime` is not null.
  - Uses a `animate-pulse` dot (1.5px) + `FORECAST · {inspectedTime}` in `text-[11px] font-mono uppercase` — visually subordinate to telemetry values.
  - "Back to Current" button is smaller (`text-[10px]`, `w-2.5 h-2.5` icon) and has `aria-label="Return telemetry to current observation"`.
  - The indicator has a `data-testid="forecast-scrubbing-indicator"` for testability.
  - Vanishes completely when `inspectedTime` is null (live / NOW state).

### 3. Ultra-wide Header Omnibar Width (MEDIUM)
- **File**: `frontend/src/components/Header.tsx`
- Changed desktop search slot container from `max-w-md` to `max-w-md xl:max-w-lg 2xl:max-w-xl`.
- At 1280px (`xl`): ≈512px search field — improved header tension.
- At 1920px (`2xl`): ≈576px search field — better three-zone balance without appearing oversized.

### 4. IMD Bulletin External Links (MEDIUM)
- **File**: `frontend/src/components/advisory/OfficialAdvisorySection.tsx`
- In the compact multi-advisory scannable list rows (both **active** and **upcoming**), if `adv.source_url` is present in the data, an `ExternalLink` icon link is now rendered alongside the status badge.
- Uses `aria-label="Open official source bulletin from {authority} in a new tab"`, `target="_blank"`, `rel="noopener noreferrer"`.
- Clicking the link does not propagate to the row (`e.stopPropagation()`).
- Already present on full `OfficialAdvisoryCard` and `OfficialAdvisoryBanner` — no changes needed there.
- **Confirmed**: `source_url` is a verified field populated by backend providers (IMD: `https://mausam.imd.gov.in`, CPCB: `https://app.cpcbccr.com/ccr/`, INCOIS: `https://incois.gov.in`, SACHET: `https://sachet.ndma.gov.in`).

### 5. Telemetry Temperature Feels-Like Delta (LOW)
- **File**: `frontend/src/components/briefing/WeatherTelemetry.tsx`
- Computed `tempDiff = Math.round(feels_like) - Math.round(temperature)`.
- Subtext shows `"Feels {N}°C (+2°)"` or `"Feels {N}°C (-3°)"` when a delta exists, or `"Feels {N}°C"` when 0.
- This replaces the flat `Feels {N}°C` string with a delta that is genuinely informative rather than redundant with the main temperature value.

---

## Deferred

### IMD URL Construction (explicitly deferred)
- Per the brief: "Do NOT construct URLs from bulletin numbers." No constructed URLs were added. Only `source_url` values already stored in advisory data by the backend providers are surfaced.

---

## Files Changed

| File | Change |
| :--- | :--- |
| `frontend/src/components/Header.tsx` | Added `useIsMobile` hook, mobile search toggle button (`Search`/`X` icon), conditional search slot rendering per viewport, ultra-wide `max-w` responsive constraints |
| `frontend/src/components/Header.test.tsx` | Added `afterEach` cleanup, added mobile search toggle test (3 tests total — all passing) |
| `frontend/src/components/WeatherAnswerSurface.tsx` | `inspectedTimeStr` now returns `HH:MM` 24h format for telemetry strip consumption |
| `frontend/src/components/briefing/WeatherTelemetry.tsx` | Removed unused `Clock` import; added subtle `FORECAST · HH:MM` indicator; added feels-like delta computation and display |
| `frontend/src/components/advisory/OfficialAdvisorySection.tsx` | Added `ExternalLink` import; exposed verified `source_url` link in active and upcoming compact advisory rows |

---

## Tests

```
7 test files passed, 81 tests passed (0 failed)
```

New test coverage added:
- `renders mobile search trigger and toggles search slot on mobile viewport` — verifies toggle opens/closes, no duplicate inputs

---

## Build

```
✓ built in 3.83s (all 2346 modules transformed, no TypeScript errors)
```

---

## Visual Verification

| Viewport | Theme | State | Verified |
| :--- | :--- | :--- | :--- |
| 390px | Vandal | Result state — mobile search toggle visible, slot opens on tap | ✅ |
| 430px | Vandal | Same as above | ✅ |
| 768px+ | All | Desktop search visible inline, no toggle button present | ✅ |
| 1280px | Atheris | Header balanced, search `max-w-md` | ✅ |
| 1440px | Midnight | No regression to docked search proportions | ✅ |
| 1920px | Light | Search field widens to `max-w-xl` on `2xl`, improved center-zone balance | ✅ |
| Any | Vandal | Forecast scrubbing shows `FORECAST · 19:00` subtle chip, vanishes on release | ✅ |
| Any | Atheris/Midnight/Light | Forecast scrubbing chip uses `var(--accent-primary)` — fully themed | ✅ |
| Any | All | Telemetry temp subtext: `Feels 34°C (+2°)` or `Feels 31°C` | ✅ |
| Any | All | Advisory compact row — ExternalLink icon visible when source_url present | ✅ |

---

## Regression Check

| Behavior | Result |
| :--- | :--- |
| Discovery canvas — hero search intact | ✅ No change |
| Normal weather result layout | ✅ No change |
| Follow-up query from docked search (desktop) | ✅ No change |
| Forecast scrubbing — telemetry values update | ✅ Confirmed (new state cue is additive) |
| Forecast NOW state — no cue displayed | ✅ Confirmed |
| Map interaction | ✅ No change |
| Official advisories — promoted banner above WeatherGPT | ✅ No change |
| Advisory deduplication — reference strip below | ✅ No change |
| AQI / environmental section | ✅ No change |
| Severe advisory promotion | ✅ No change |
| Theme switching — all 4 themes | ✅ No change to theme identities |
| Severity colors (Red/Orange/Yellow/Green) | ✅ Immutable — not touched |
| Mobile layout — 2x2 telemetry grid | ✅ No change |
| Desktop layout — 4-column telemetry strip | ✅ No change |

---

## Commit

```
91bf567
fix: apply UI-09 product cohesion corrections
```

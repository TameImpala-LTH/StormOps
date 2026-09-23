# StormOps Product Experience Blueprint
**Phase UI-02: Interaction Architecture, Information Hierarchy & Experience Specification**

---

## 1. Product Experience Principles

StormOps is a conversational weather intelligence system. It must not present itself as:
- A conventional weather application (a grid of colorful metric boxes and animated sun icons)
- A generic weather dashboard (a crowded control room of gauges and tables)
- A collection of disconnected forecast cards
- A heavy desktop GIS application
- A generic AI chatbot with a text bubble prompt

### The Core Interaction Model
```
User asks naturally
       ↓
StormOps resolves location & temporal intent
       ↓
StormOps retrieves grounded meteorological observation & forecast data
       ↓
StormOps interprets the conditions & derives real-world impact
       ↓
StormOps explains WHAT MATTERS in authoritative natural language
       ↓
StormOps provides verified supporting EVIDENCE (metrics & hourly curves)
       ↓
StormOps optionally exposes deeper SPATIAL & OFFICIAL context
```

### The Guiding Mandate: "Less UI. More Intelligence."
- **Calm Authority**: The screen should evoke the quiet confidence of an expert meteorologist giving a personal briefing.
- **Synthesized over Fragmented**: Never force the user to synthesize 6 different numbers to figure out if they need an umbrella or if travel is hazardous. State the synthesis first; provide the numbers as proof.
- **Atmospheric Restraint**: Interfaces should feel spacious, dark, and tactile, using typography and subtle lighting rather than thick borders and bright cards.
- **Truth to Data & Safety**: Official government warnings (IMD/CAP) remain sovereign and distinct; AI synthesis never dilutes or recolors authoritative safety advisories.

---

## 2. Discovery State (State A)

State A is the welcoming, quiet canvas when the application is launched or reset, before an active weather query is issued.

```
+-----------------------------------------------------------------------------------+
|  [Logo] StormOps                     [Device: New Delhi 28°C] [Theme] [Profile]   |
|                                                                                   |
|                                                                                   |
|                                                                                   |
|                                                                                   |
|                                   STORMOPS                                        |
|                          Weather Intelligence Engine                              |
|                                                                                   |
|         +---------------------------------------------------------------+         |
|         | [Search] Ask about weather anywhere...            [Mic] [Loc] |         |
|         +---------------------------------------------------------------+         |
|                                                                                   |
|                  Search beyond cities · Towns · Villages · Localities             |
|                                                                                   |
|            [Recent: Darjeeling]    [Recent: Koramangala]    [Recent: Leh]         |
|                                                                                   |
|                                                                                   |
|                                                                                   |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Visual Center & Atmospheric Canvas
- **Visual Center**: Positioned at approximately 38% down the vertical viewport. This places the search interaction directly in the natural eye-landing zone without feeling crowded.
- **Branding**: Minimalist wordmark: `StormOps` in clean geometric sans-serif (font-weight 500, tracking -0.02em), with a subtle monospace badge or sub-label `Weather Intelligence Engine`.
- **Atmospheric Background**: Subtle vignette with an ambient, deep-field radial gradient centered behind the search bar. This gives a sense of looking into a clear night sky or distant atmospheric horizon without distracting movement.
- **Search Placement**: Generous, elegant omnibar (max-width: 640px, height: 56px, rounded-2xl). Subtle border with soft backdrop blur. Inside the bar: search icon, input field, microphone icon for multilingual voice input, and geolocation trigger icon.

### Geographic Capability Messaging
- **Evaluated Options**:
  1. *"Ask about the weather anywhere."* — Too generic; sounds like Apple Weather or Google.
  2. *"690,000+ settlements across India."* — Strictly forbidden at this phase; over-claims coverage before final gazetteer validation.
  3. *"Search beyond cities."* — Strong, provocative, immediately communicates geographic differentiation.
  4. *"Cities · Towns · Villages · Localities"* — Concrete, educational, sets user expectations.
- **Recommended Approach**:
  A two-tier subtle micro-caption beneath the omnibar:
  `Search beyond cities · Towns · Villages · Localities`
  Followed by rotating, gentle prompt placeholders inside the input:
  - *"Will it rain in Darjeeling this evening?"*
  - *"Cherrapunji 24-hour rainfall outlook"*
  - *"Wind conditions in Rohtang Pass tomorrow morning"*
  *Rationale*: This immediately breaks the mental model that weather apps only know capital cities, without making unverified quantitative statistical claims.

### Secondary Utility Controls
- **Header Placement**: Pinned to the top edge:
  - Left: Minimalist logo icon.
  - Right: Device weather snapshot (e.g. `New Delhi 28°C`), theme selector, and user account button.
- **Recent Searches**: Below the capability prompt, render up to 3 subtle pill tokens for recent or favorited settlements (e.g., `Darjeeling`, `Koramangala`, `Leh`).

### What is Intentionally NOT Shown in Discovery
- No empty dashboard panels or placeholder card outlines.
- No unsolicited global capitals (`Tokyo`, `London`, `New York`).
- No fake animated radar maps.
- No heavy marketing banners or feature bullet points.
- No news feeds or sponsored content.

---

## 3. Intelligence State (State B)

When the user submits a query, State A transitions into the Intelligence Briefing.

```
+-----------------------------------------------------------------------------------+
|  [Logo] StormOps   [ Search: Koramangala, Bengaluru... [Mic] ]  [Theme] [Profile] |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  Koramangala                                                                      |
|  Bengaluru South · Karnataka · India                                              |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | [!] IMD ORANGE ALERT · Heavy rainfall warning active until 21:00 IST       |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  "Heavy convective showers will begin around 16:30 and disrupt the evening         |
|   commute. Rain will taper off after 19:30, with 22mm total expected."            |
|                                                                                   |
|  [ Umbrella Required · High Confidence ]                                          |
|                                                                                   |
|  -------------------------------------------------------------------------------  |
|  23°C                 Feels 21°C               85% Rain Chance (Peak 17:00)       |
|  Wind 18 km/h W       Humidity 88%             AQI 32 · Satisfactory              |
|  -------------------------------------------------------------------------------  |
|                                                                                   |
|  HOURLY PROGRESSION (Next 24 Hours)                                               |
|  [ Interactive Spline Curve with Hover Scrubber & Precipitation Hyetograph ]      |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | SPATIAL CONTEXT & RADAR PERSPECTIVE                                         |  |
|  | [ Themed Leaflet Map showing location marker & official warning polygon ]   |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  Follow-up: [ "What about tomorrow morning?" ] [ "How does this compare to Whitefield?" ]
+-----------------------------------------------------------------------------------+
```

### The Transition Dynamics (State A → State B)
- **Zero Layout Shock**: The transition must feel continuous, not like a page reload or route navigation.
- **The Morph**:
  1. The central omnibar smoothly elevates and docks to the top header area (resizing from 640px to 480px).
  2. The hero branding and discovery copy fade out (`duration: 200ms`).
  3. The Intelligence Briefing streams in from `opacity: 0, y: 12px` to `opacity: 1, y: 0px` with a clean staggered cadence (`staggerChildren: 0.05s`).
- **Follow-up Interaction**: The docked search bar remains active for natural language follow-ups (*"What about tomorrow?"*, *"Will winds pick up tonight?"*). Contextual suggested follow-up chips appear at the base of the briefing.

---

## 4. Primary Information Hierarchy

The screen strictly adheres to the four cognitive tiers:

```
┌────────────────────────────────────────────────────────┐
│ 1. WHAT MATTERS                                        │
│ WeatherGPT Immediate Synthesis + Action Verdict        │
├────────────────────────────────────────────────────────┤
│ 2. WHY                                                 │
│ Core Dynamic Telemetry (Temp, Feels-like, Peak Rain)   │
├────────────────────────────────────────────────────────┤
│ 3. EVIDENCE                                            │
│ 24-Hour Continuous Hourly Forecast & Scrubber          │
├────────────────────────────────────────────────────────┤
│ 4. DETAIL & CONTEXT                                    │
│ Spatial Map · Official IMD Bulletins · Air Quality     │
└────────────────────────────────────────────────────────┘
```

### Visual Dominance Rules
1. **Visually Dominant**: The WeatherGPT 1-to-2 sentence synthesis. It is set in large, clear, high-contrast type. If the user only looks at the screen for 2 seconds, they get the full answer.
2. **Secondary**: The Core Dynamic Telemetry row. High-contrast tabular figures providing instantaneous verification of temperatures and precipitation probabilities.
3. **Tertiary**: The 24-hour interactive progression graph. Accessible at a glance, allowing the user to trace how the weather evolves throughout their day.
4. **Progressive Disclosure**: Spatial map, deep meteorological diagnostics (atmospheric pressure, dew point, UV index), and detailed official meteorological bulletin text. Available by scrolling or toggling, never cluttering the initial viewport.

---

## 5. WeatherGPT Must Be the Hero

The WeatherGPT synthesis is the intellectual signature of StormOps. It must look like an authoritative briefing statement, **never** an "AI chat bubble" or a boxed-in card.

```
                                  WEATHERGPT HERO TREATMENT

  "Heavy convective showers will begin around 16:30 and disrupt the evening
   commute. Rain will taper off after 19:30, with 22mm total expected."

  [ UMBRELLA REQUIRED ]    High confidence · Peak precipitation at 17:00
```

### Typographic Specifications
- **Headline / Primary Insight**:
  - Size: `1.375rem` (22px) on desktop, `1.125rem` (18px) on mobile.
  - Weight: 400 (Regular) with selective semi-bold emphasis on key temporal and meteorological anchors.
  - Line Height: 1.5.
  - Max Width: `68ch` (characters per line). Exceeding this width causes ocular fatigue; keeping it under 68ch ensures effortless reading.
  - Color: Primary high-contrast text token (`var(--text-primary)`).
- **Supporting Narrative (Detailed Interpretation)**:
  - If the user asked an analytical or comparative question, a secondary paragraph sits beneath the primary insight in `0.9375rem` (15px), `var(--text-secondary)`, line-height 1.6.

### Action & Confidence Treatment
- Immediately below the synthesis:
  - **Action Token**: A clean, pill-shaped badge displaying the concrete recommendation:
    `[ Umbrella Required ]`, `[ Outdoor Activities Favorable ]`, `[ Commute Disruption Expected ]`, `[ Heat Protection Advised ]`.
    - Recommended: subtle emerald border and background tint (`rgba(16, 185, 129, 0.1)`).
    - Not Recommended / Caution: subtle rose/amber border and background tint.
  - **Confidence Indicator**: Quiet monospace text beside the badge: `High confidence · Derived from ECMWF/GFS ensemble consensus`.

### Distinction: Synthesis vs Metric Repetition
- **BAD (Redundant)**: *"The temperature in Koramangala is 23°C. Humidity is 88%. The rain probability is 85%."* (This is just repeating numbers the user can already see).
- **GOOD (Intelligent Synthesis)**: *"Rain is likely to disrupt the evening commute, with the strongest downpours between 17:00 and 19:00. Cooler westerly winds will lower temperatures to 21°C by nightfall."*

---

## 6. Core Weather Telemetry

We completely eliminate the redundant 4-box card grids and nested tile borders. Telemetry is expressed through **typography, alignment, and whitespace**.

```
  +---------------------------------------------------------------------------------+
  |  23°C               FEELS LIKE 21°C          85% RAIN CHANCE (Peak 17:00)       |
  |  Scattered Showers  Low: 19° · High: 27°     Wind: 18 km/h W · Humidity: 88%   |
  +---------------------------------------------------------------------------------+
```

### Primary vs Secondary vs Contextual Metrics
| Tier | Metrics | Treatment | Display Rule |
| :--- | :--- | :--- | :--- |
| **Primary** | Current Temperature, Condition Label, Feels-Like, Precipitation Probability & Peak Window | Large tabular numerals (36px/24px), prominent label | Always visible across all queries |
| **Secondary** | Wind Speed & Direction, Humidity, Air Quality Index (AQI), Today's High/Low | Clean monospace/sans subline (13px), subtle mute | Always visible in one clean horizontal strip |
| **Contextual** | UV Index, Visibility, Atmospheric Pressure, Dew Point | Micro-metadata badges | **Only visible when relevant** (e.g. UV $\ge 6$, Visibility $\le 2\text{km}$, Barometric drops) |

### Horizontal Streamlined Architecture
- Rather than carving the screen into 4 separate rectangular cards with heavy borders, the metrics sit in a **single, unified, borderless telemetry bar**.
- Columns are separated by subtle vertical dividers (`1px solid var(--border-muted)`) or pure whitespace.
- Temperature and Feels-Like are tightly coupled: `23°C` with a quiet subscript `Feels 21°C` directly adjacent, preventing the eye from jumping across the screen.

---

## 7. Official Advisory Experience

Official government bulletins (IMD, SDMA, CAP) are legal instruments of public safety. They must remain strictly separated from StormOps AI interpretations.

```
  +---------------------------------------------------------------------------------+
  | [!] IMD ORANGE ALERT · HEAVY RAINFALL                                           |
  | Effective: 23 Sep 14:00 IST – 24 Sep 08:30 IST · Bengaluru Urban District       |
  | Heavy to very heavy rainfall accompanied by gusty winds (30-40 km/h) is likely. |
  +---------------------------------------------------------------------------------+
```

### Strict Severity Semantics
Official advisory severities must **never be recolored to match app themes**:
- **IMD RED / WARNING**: High-contrast Crimson (`#ef4444` / `rgba(239, 68, 68, 0.12)`).
- **IMD ORANGE / ALERT**: High-contrast Tangerine (`#f97316` / `rgba(249, 115, 22, 0.12)`).
- **IMD YELLOW / WATCH**: Amber (`#eab308` / `rgba(234, 179, 8, 0.10)`).
- **IMD GREEN / NO WARNING**: Suppressed; zero visual noise.

### Placement & Lifecycle
1. **When Active**: If an active warning exists for the queried district, it sits **directly above the WeatherGPT synthesis**, immediately under the location title. It serves as an authoritative preamble.
2. **When Upcoming**: If an advisory is valid starting later in the day/tomorrow, it displays with an `UPCOMING` badge and exact start timestamp.
3. **When Absent**: If no advisory is in effect, **the component takes up 0 pixels**. No empty state banner, no "No active warnings" placeholder.

---

## 8. Forecast Experience (24-Hour Timeline)

The 24-hour interactive forecast chart is one of StormOps' greatest assets. We preserve its Catmull-Rom spline precision while deeply integrating it with the intelligence surface.

```
  24-HOUR OUTLOOK
  14:00    16:00    18:00    20:00    22:00    00:00    02:00    04:00    06:00
   24°      23°      21°      20°      19°      19°      18°      18°      21°
    .--------.
              \
               \________.________.________.________.________.________.
    |        ||||     |||        |        |        |        |        |
   10%      85%      70%       20%       0%       0%       0%       0%       0%
```

### Relationship: WeatherGPT → Telemetry → Timeline
- **The Scrubber Connection**:
  - Hovering or scrubbing across any hour on the timeline (e.g., `17:00`) instantly updates the Core Telemetry row to reflect conditions at that specific hour.
  - A subtle cursor line traces the spline curve, with a floating micro-card showing: `17:00 · 21°C · 85% Rain (4.2mm) · Wind 22 km/h NW`.
- **Precipitation Hyetograph Integration**:
  - Rain probability and precipitation volume (mm) are visualized as vertical soft bars directly below the temperature spline, giving an immediate correlation between temperature drops and rain onset.

### Capability Boundary for Forecast
- **SUPPORTED NOW**:
  - Hourly temperature, feels-like, precipitation probability, rain volume (mm), humidity, wind speed, weather condition code.
  - Interactive scrubbing and local timezone calculations.
- **FUTURE / REQUIRES ARCHITECTURE**:
  - Multi-day (7-day/14-day) interactive scrubbing (requires expanding API payload caching).
  - Historical weather replay (requires archive database integration).

---

## 9. Map Experience

### Evaluation of Compositions

```
  OPTION A: Integrated Lower Surface         OPTION B: Desktop Split (55/45)
  +-----------------------------------+      +-------------------+-----------------+
  | WeatherGPT Briefing               |      | WeatherGPT        | Persistent      |
  | Core Telemetry                    |      | Core Telemetry    | Fluid           |
  | 24h Timeline                      |      | 24h Timeline      | Interactive     |
  +-----------------------------------+      | Advisories        | Synoptic Map    |
  | Interactive Map (Full Width)      |      |                   |                 |
  +-----------------------------------+      +-------------------+-----------------+
```

#### Option A: Integrated Lower Spatial Surface
- **Description**: Map sits below the 24-hour timeline across the full width of the content column (height: 380px), framed with subtle corner radii.
- **Strengths**: Familiar reading order; vertical flow is simple and natural; works identically across small and large screens.
- **Weaknesses**: Requires scrolling to view; isolates spatial context from the headline synthesis.
- **Desktop Behavior**: Centered column, max-width 880px.
- **Mobile Behavior**: Stacks naturally at the bottom of the briefing.
- **Complexity**: Low.

#### Option B: Desktop Split Intelligence + Map
- **Description**: On viewports $\ge 1280\text{px}$, the screen splits into two synchronized columns: Left (55%) contains the intelligence briefing; Right (45%) contains a full-height, pinned Leaflet map canvas.
- **Strengths**: True command-center feel; immediate spatial reinforcement; no scrolling needed to understand geography and warnings.
- **Weaknesses**: On screens with moderate height, the left column can feel constrained; Leaflet wheel-zoom can capture user scroll events accidentally.
- **Desktop Behavior**: Dual-column pinned split.
- **Mobile Behavior**: Collapses to single column with map below or in a secondary view.
- **Complexity**: Moderate.

#### Option C: Expandable / Immersive Map Mode
- **Description**: The briefing displays in a clean single column. A persistent, ambient mini-map pill sits beside the location header. Clicking it smoothly expands the map into an edge-to-edge backdrop or overlay drawer.
- **Strengths**: Keeps the default briefing 100% focused on text and telemetry; zero clutter; extraordinary visual impact when toggled.
- **Weaknesses**: Spatial context is hidden behind an explicit click; users may miss warning boundary polygons.
- **Desktop Behavior**: Default compact preview $\to$ full-screen toggle.
- **Mobile Behavior**: Floating map preview button $\to$ full-screen modal map.
- **Complexity**: Moderate-High.

### Architecture Recommendation: Hybrid Option A + C
- **Primary**: Deploy **Option A (Integrated Lower Spatial Surface)** as the default document flow, but refine it so it has zero heavy container borders and uses theme-tailored tile maps (CartoDB DarkMatter / Positron).
- **Secondary**: Provide an unobtrusive "Expand Map" control in the map header that effortlessly transitions into an immersive edge-to-edge modal view for in-depth spatial analysis.

### Boundary of Current Map Capabilities
- **SUPPORTED NOW**:
  - Settlement focal marker with animated pulse.
  - Comparison dual-marker view with auto-bounding fit.
  - Official advisory spatial geometry: circle overlays (`radius_km`), point markers, and GeoJSON multi-polygons with official severity colors.
  - Tile layer switching (Dark, Light, Satellite/Terrain).
- **FUTURE / DO NOT PROMISE IN UI**:
  - Live animated radar Doppler tiles (requires NEXRAD/IMD radar tile server integration).
  - Dynamic wind streamline particle animations (requires GRIB2 vector field rendering).
  - Real-time cloud satellite feeds (requires INSAT-3D tile ingestion).

---

## 10. Search / Omnibar

The Omnibar is the primary steering wheel of StormOps. It must handle free-form queries, structured locations, and voice without mode-switching.

```
  +---------------------------------------------------------------------------------+
  | [Search] Narsingpur, Madhya Pradesh                                 [Mic] [Loc] |
  +---------------------------------------------------------------------------------+
  | SUGGESTIONS / DISAMBIGUATION:                                                   |
  |  * Narsinghpur (District HQ) · Madhya Pradesh                                   |
  |  * Narsingpur (Revenue Village) · Hoshangabad · Madhya Pradesh                  |
  |  * Narsingpur (Town) · Cuttack · Odisha                                         |
  +---------------------------------------------------------------------------------+
```

### Discovery vs Intelligence Search States
- **Discovery**: Centered, 56px height, 640px wide, large placeholder with capability hints.
- **Intelligence**: Docks to top header, 44px height, 480px wide, displays the active query with clear one-click clear (`X`) and edit capability.

### Keyboard & Voice Navigation
- **Keyboard Shortcut**: Pressing `/` or `Ctrl+K` (`Cmd+K`) anywhere in the app immediately focuses the search bar and selects existing text.
- **Voice Trigger**: Microphone button supports speech-to-text in English, Hindi, and Bengali. While listening, an unobtrusive waveform pulse animates within the button, not taking over the screen.
- **Location Trigger**: The `LocateFixed` icon requests high-accuracy browser geolocation, immediately resolving coordinates into the nearest Indian administrative entity.

---

## 11. Geographic Identity

StormOps has sub-district, tehsil, and revenue village intelligence. The presentation must celebrate this spatial resolution without creating bureaucratic clutter.

```
                                  GEOGRAPHIC HIERARCHY

  Park Street
  Kolkata · West Bengal · India

  Narsingpur
  Tehsil Narsinghpur · Narsinghpur District · Madhya Pradesh
```

### Representation Rules
1. **Primary Headline**: The specific locality, village, or town name (`font-size: 1.75rem`, `font-weight: 300`, `letter-spacing: -0.02em`).
2. **Context Subtitle**: Monospace or clean sans micro-label directly underneath (`font-size: 0.8125rem`, `color: var(--text-secondary)`).
   - If Settlement is a Locality: `Locality · City · State` (e.g. `Koramangala · Bengaluru · Karnataka`)
   - If Settlement is a Village/Town: `Village · Tehsil / Sub-district · District · State`
   - If Settlement is a District HQ: `District HQ · State · India`
3. **Collapsing Rule**: Drop the country (`India`) whenever the state is clear to keep the header uncluttered on mobile devices.

---

## 12. Ambiguity Resolution

When a user searches for a name that exists across multiple states or districts (e.g. *Rampur, Bilaspur, Hariharpur*), StormOps must **never make an arbitrary silent guess**.

```
  +---------------------------------------------------------------------------------+
  | Multiple locations found for "Rampur". Select the intended location:            |
  |                                                                                 |
  | [Loc] Rampur (District HQ)                                                      |
  |       Moradabad Division · Uttar Pradesh                                        |
  |                                                                                 |
  | [Loc] Rampur Bushahr (Statutory Town)                                           |
  |       Shimla District · Himachal Pradesh                                        |
  |                                                                                 |
  | [Loc] Rampur (Sub-district)                                                     |
  |       Samastipur District · Bihar                                               |
  +---------------------------------------------------------------------------------+
```

### Disambiguation Mechanics
- **Display Form**: An inline dropdown anchored to the search omnibar (desktop) or a focused modal sheet (mobile).
- **Candidates Capped**: Display the top 4 most prominent candidates based on administrative rank (District HQ > Sub-district > Town > Village).
- **Metadata per Row**:
  - Entity Name
  - Administrative classification badge (`Statutory Town`, `Census Town`, `District HQ`, `Village`)
  - Full parent hierarchy (Sub-district, District, State)
- **Selection Action**: Clicking immediately dispatches the weather intelligence query with the precise entity ID and coordinates.

---

## 13. Desktop Composition

### Text Wireframe: Standard Desktop (1440px Viewport)

```
===================================================================================
HEADER: 64px height | Max-width 1280px | Pinned Top
[Icon] StormOps     [ Omnibar: "Cherrapunji, Meghalaya"  [Mic] ]     [28°C] [Theme] [User]
===================================================================================

MAIN BRIEFING CONTAINER (Max-width: 880px, Centered, Padding-X: 24px)

  1. GEOGRAPHIC IDENTITY (Margin-Top: 32px)
     Cherrapunji (Sohra)
     East Khasi Hills District · Meghalaya
     [Star Favorite] · [Share Briefing]

  2. OFFICIAL WARNING RIBBON (Conditional — only if active)
     +---------------------------------------------------------------------------+
     | [!] IMD RED WARNING · EXTREMELY HEAVY RAIN ACTIVE TILL 24 SEP 08:30 IST   |
     | Monsoon surge active; intense precipitation exceedances > 200mm likely.   |
     +---------------------------------------------------------------------------+

  3. WEATHERGPT SYNTHESIS (The Intellectual Hero)
     "Continuous torrential rain will persist throughout the day and overnight,
      with peak intensities between 18:00 and 23:00. Localized flash runoff
      and reduced visibility below 500m across ghat roads will severely impair travel."

     [ Travel Strongly Discouraged · High Confidence ]
     ECMWF/GFS ensemble consensus · 98% agreement

  4. CORE WEATHER TELEMETRY (Unified Borderless Row)
     ---------------------------------------------------------------------------
     18°C                 FEELS LIKE 16°C          100% RAIN CHANCE (Peak 19:00)
     Heavy Monsoon Rain   Low: 17° · High: 19°     Wind: 26 km/h SW · Hum: 99%
     ---------------------------------------------------------------------------

  5. 24-HOUR INTERACTIVE FORECAST TIMELINE
     +---------------------------------------------------------------------------+
     | HOURLY OUTLOOK                                             Local: 14:45   |
     | [ Splined temperature curve with Catmull-Rom interpolation ]              |
     | [ Integrated precipitation hyetograph bars (mm) ]                         |
     | [ Hover / Touch scrubber with live telemetry coupling ]                   |
     +---------------------------------------------------------------------------+

  6. SPATIAL CONTEXT & ADVISORY GEOMETRY (Height: 380px)
     +---------------------------------------------------------------------------+
     | Leaflet Map Canvas (DarkMatter / Positron)                                |
     | - Active location marker with live weather badge                          |
     | - Official IMD Red warning polygon for East Khasi Hills                   |
     | - [Expand Fullscreen] [Toggle Layer]                                      |
     +---------------------------------------------------------------------------+

  7. CONTEXTUAL FOLLOW-UP CHIPS
     [ "When will rain subside?" ]  [ "Compare with Shillong" ]  [ "Tomorrow's outlook" ]

===================================================================================
FOOTER: Minimalist metadata · Last updated: 14:30 IST · Data: Open-Meteo & IMD
===================================================================================
```

### Responsive Desktop Scaling Rules
- **1366px**: Container width sets to `780px`. Map height: `340px`.
- **1440px**: Container width sets to `880px`. Map height: `380px`.
- **1920px+ (Ultra-wide)**:
  - Container width expands gracefully to `960px` with generous ambient margins.
  - Never allow text lines to stretch beyond `68ch`.
  - The atmospheric background radial glow expands proportionally to maintain visual warmth.

---

## 14. Mobile Composition

Mobile is designed as a focused, single-thumb intelligence briefing.

```
+------------------------------------------+
| =  StormOps          [28°] [Theme] [User] |
+------------------------------------------+
| [Search: Cherrapunji...            [Mic] |
+------------------------------------------+
|                                          |
| Cherrapunji                              |
| East Khasi Hills · Meghalaya             |
|                                          |
| +--------------------------------------+ |
| | [!] IMD RED WARNING · HEAVY RAINFALL | |
| +--------------------------------------+ |
|                                          |
| "Continuous torrential rain will         |
|  persist throughout the day. Travel is   |
|  severely discouraged."                  |
|                                          |
| [ Travel Not Recommended ]               |
|                                          |
| 18°C  Feels 16°C  ·  100% Rain (19:00)   |
| Wind: 26 km/h SW  ·  Humidity: 99%       |
|                                          |
| ---------------------------------------- |
| 24-HOUR FORECAST                         |
| [ Horizontal swipeable hourly curve ]    |
|                                          |
| ---------------------------------------- |
| SPATIAL RADAR & MAP                      |
| [ Compact 220px map with warning poly ]  |
|                                          |
| [ Ask follow-up...                     ] |
+------------------------------------------+
```

### Mobile Optimization Principles
1. **No Tab Hunting**: Users should not have to toggle between `Overview`, `Hourly`, and `Radar` tabs just to see if it will rain. The entire briefing flows naturally down a single vertical scroll.
2. **First Viewport Guarantee**: In the first 600px of vertical space, the mobile user receives: Location Name $\to$ Active Official Warning $\to$ WeatherGPT Verdict $\to$ Action Pill $\to$ Current Temperature.
3. **Touch-Optimized Hourly Timeline**: The forecast chart supports smooth horizontal touch scrubbing with haptic feedback (where browser supported) on hour ticks.
4. **Docked Mobile Follow-up Bar**: A fixed 50px bottom input allows instantaneous voice or typed follow-up queries without having to scroll back to the top.

---

## 15. Theme System

StormOps supports four carefully calibrated themes. Each maintains absolute architectural consistency while projecting a unique atmospheric personality.

```
  +------------------+------------------+------------------+------------------+
  |     ATHERIS      |      VANDAL      |     MIDNIGHT     |      LIGHT       |
  |  Pitch Black     |  Pitch Black     |  Cosmic Purple   |  Warm Stone      |
  |  Cool Sky Blue   |  Neon Rose / Red |  Warm Amber      |  Emerald Green   |
  |  #000000 / #38b  |  #000000 / #f43  |  #080612 / #fb  |  #f5f5f4 / #059  |
  +------------------+------------------+------------------+------------------+
```

### Personality Profiles
1. **Atheris (Default Dark)**:
   - *Personality*: Cool, technical, calm, precision instrument.
   - *Base*: `#000000` (Pitch Black) with `#090d16` surfaces.
   - *Accent*: Sky Blue (`#38bdf8`) and Cool Slate (`#94a3b8`).
2. **Vandal**:
   - *Personality*: Tactical, urgent, storm-tracking energy.
   - *Base*: `#000000` (Pitch Black) with `#14090b` surfaces.
   - *Accent*: Signal Crimson / Rose (`#ff2a55`) and Warm Charcoal.
3. **Midnight (Night Mode)**:
   - *Personality*: Deep, astronomical, quiet, contemplative.
   - *Base*: Cosmic Obsidian (`#080612`) with translucent violet glass (`rgba(18, 12, 34, 0.60)`).
   - *Accent*: Warm Starlight Amber (`#fbbf24`) and Muted Violet (`#818cf8`).
4. **Light**:
   - *Personality*: Crisp editorial, clean paper, daylight clarity.
   - *Base*: Warm Stone (`#f5f5f4`) with Pure White (`#ffffff`) elevated surfaces.
   - *Accent*: Deep Forest Emerald (`#059669`) and Neutral Slate (`#475569`).

### Strict Theme Boundary Rules
- **ALLOWED FOR THEME ACCENTS**:
  - Brand typography highlights.
  - Search bar active focus glow.
  - Forecast spline curve stroke.
  - Interactive buttons, sliders, and toggle switches.
  - Base Leaflet tile map styling (DarkMatter vs Positron).
- **STRICTLY FORBIDDEN FOR THEME ACCENTS**:
  - Official IMD / CAP advisory severities (Red is always red; Orange is always orange; Yellow is always yellow).
  - Safety-critical action badges (`Travel Not Recommended` must retain semantic danger styling regardless of whether the theme is Atheris or Light).

---

## 16. Visual Language

- **Typography**:
  - System sans-serif stack (`Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`).
  - Monospace accents for metrics and coordinates (`JetBrains Mono`, `ui-monospace`, `monospace`).
  - Strict line-height hierarchy: Headings `1.2`, Body `1.5`, Micro-labels `1.0`.
- **Spacing System**: Strictly based on an 8pt modular grid (`4px`, `8px`, `16px`, `24px`, `32px`, `48px`, `64px`).
- **Radii**:
  - Omnibar & Large Containers: `16px` (`rounded-2xl`).
  - Badges & Buttons: `8px` (`rounded-lg`) or fully pill-shaped `9999px`.
- **Borders & Elevation**:
  - Border width: Exactly `1px`.
  - Border color: Subtle semantic tokens (`var(--border)` = `rgba(255, 255, 255, 0.08)` in dark themes).
  - Zero heavy drop shadows. Elevation is conveyed by background color steps:
    `--surface-base` (`#000000`) $\to$ `--surface-elevated` (`#0c0f17`) $\to$ `--surface-hover` (`#141923`).
- **Glassmorphism**: Minimal and restrained. Only applied to pinned navigation headers and floating tooltips using `backdrop-filter: blur(12px)`.

---

## 17. Motion Principles

Motion in StormOps is functional and atmospheric. It communicates state changes and data causality, never decorative gimmickry.

1. **State Transition (Discovery → Intelligence)**:
   - Smooth physical spring transition using Framer Motion.
   - Docking Omnibar: `transition: { type: 'spring', damping: 26, stiffness: 220 }`.
2. **Progressive Telemetry Reveal**:
   - Staggered entry for the briefing tiers (`staggerChildren: 0.04s`, `y: 8px -> 0px`). Total reveal completes in $<350\text{ms}$.
3. **Forecast Hover Synchronization**:
   - Scrubbing the 24-hour curve instantly updates metric values with zero lag (`duration: 0`). Tabular numbers use `font-variant-numeric: tabular-nums` to prevent horizontal jitter.
4. **Precipitation Pulse**:
   - When active rain is falling, the condition icon receives a subtle, slow breath effect (`scale: [1, 1.03, 1]`, duration: 4s). Never rapid blinking.
5. **Accessibility**:
   - If `prefers-reduced-motion` is detected, all spatial movements (`y` translations, spring morphs) collapse to instantaneous opacity crossfades (`duration: 0.15s`).

---

## 18. What We Remove

The following elements from the current codebase are explicitly marked for **PERMANENT REMOVAL**:

| Element | Current Location | Rationale for Removal |
| :--- | :--- | :--- |
| **Secondary Key Metrics Grid** | [WeatherAnswerSurface.tsx#L1003-L1100](file:///C:/StormOps/frontend/src/components/WeatherAnswerSurface.tsx#L1003-L1100) | Complete 1:1 duplication of metrics already present in the WeatherGPT/Hero card. Removes 100 lines of redundant DOM. |
| **Hero Weather Temperature Card** | [WeatherAnswerSurface.tsx#L954-L998](file:///C:/StormOps/frontend/src/components/WeatherAnswerSurface.tsx#L954-L998) | A redundant 5xl temperature box that separates the WeatherGPT synthesis from its decision badge. |
| **Global City Preset Pills** | [locations.ts#L3-L10](file:///C:/StormOps/frontend/src/utils/locations.ts#L3-L10) | Conflates global capitals and whole Indian states (`Kerala`, `Rajasthan`); completely misrepresents our local gazetteer capabilities. |
| **Nested Card-in-Card Borders** | [WeatherAnswerSurface.tsx#L671-L676](file:///C:/StormOps/frontend/src/components/WeatherAnswerSurface.tsx#L671-L676) | Creates visual noise with boxes inside boxes inside boxes. Replaced by a clean, borderless surface. |
| **Empty State Advisory Cards** | [OfficialAdvisorySection.tsx](file:///C:/StormOps/frontend/src/components/advisory/OfficialAdvisorySection.tsx) | Renders empty containers when no warnings exist. When clear, warnings should occupy 0 pixels. |
| **Looping Icon Breathing & Ping Rings** | [WeatherAnswerSurface.tsx#L957](file:///C:/StormOps/frontend/src/components/WeatherAnswerSurface.tsx#L957) | Distracting non-functional CSS animation loops that degrade the calm, professional tone. |

---

## 19. What We Keep

The following elements represent strong engineering and design foundations and will be **PRESERVED**:

| Component / Feature | Location | Value to Preserve |
| :--- | :--- | :--- |
| **Catmull-Rom Splined Forecast Chart** | [InteractiveForecastChart.tsx](file:///C:/StormOps/frontend/src/components/InteractiveForecastChart.tsx) | Mathematically elegant, smooth temperature and precipitation visualization. |
| **Multilingual Voice Recording Hook** | [useVoiceRecording.ts](file:///C:/StormOps/frontend/src/hooks/useVoiceRecording.ts) | Seamless speech recognition across English, Hindi, and Bengali. |
| **Official Advisory CAP Parser & Severity Models** | [OfficialAdvisoryBanner.tsx](file:///C:/StormOps/frontend/src/components/advisory/OfficialAdvisoryBanner.tsx) | Robust CAP-compliant parsing of IMD hazard warnings and spatial GeoJSON polygons. |
| **Leaflet Themed Map Architecture** | [WeatherMap.tsx](file:///C:/StormOps/frontend/src/components/WeatherMap.tsx) | Battle-tested geometry rendering for advisory circles, points, and warning polygons with theme tile switching. |
| **Auth Context & Saved Locations Storage** | [AuthContext.tsx](file:///C:/StormOps/frontend/src/context/AuthContext.tsx) | Lightweight user authentication and persistent favorite locations. |

---

## 20. What We Elevate

The redesign elevates three critical capabilities into undisputed prominence:

1. **The WeatherGPT Synthesis**:
   - From: A text block inside a secondary card.
   - To: The undisputed headline of the entire application. The primary focal point that delivers the answer in 2 seconds.
2. **Unified Search & Spatial Omnibar**:
   - From: A simple text input box with static pill buttons.
   - To: An intelligent spatial omnibar with natural language parsing, voice input, and settlement disambiguation.
3. **Synchronous Forecast Scrubber**:
   - From: A passive static SVG chart.
   - To: An interactive timeline that drives real-time metric updates across the entire briefing as the user scrubs.

---

## 21. Product Capability Communication ("Sell Itself" Principle)

StormOps communicates sophistication through **behavior and precision**, never through hyperbolic marketing jargon.

### Strict Copy Guidelines
- **PROHIBITED MARKETING BUZZWORDS**:
  - *"World-Class AI"*
  - *"Revolutionary Weather Assistant"*
  - *"Next-Gen Forecasting"*
  - *"Powered by 690,000+ Locations"*
- **AUTHORITATIVE DEMONSTRATION MECHANISMS**:
  - **Precision Geocoding Proof**: When a user types a small town or village, display the exact administrative parentage: `Mawsynram · East Khasi Hills District · Meghalaya`. The depth of data speaks for itself.
  - **Meteorological Grounding**: In the synthesis, reference physical mechanisms naturally: *"Orographic lifting along the southern slopes will accelerate rain onset by mid-afternoon."*
  - **Source Transparency**: Display quiet metadata tokens: `Grounded in ECMWF HRES 0.1° & IMD CAP Bulletins`.

---

## 22. Capability Boundary Matrix

To guarantee that design never outpaces engineering reality, every feature in this blueprint is classified against our verified system capabilities:

| Feature / UI Element | Classification | Current Engineering Status |
| :--- | :---: | :--- |
| **Natural Language Weather Query Parsing** | **A** | Fully supported by existing `/query` backend API. |
| **Multilingual Voice Input (EN/HI/BN)** | **A** | Fully supported by existing Web Speech API hooks. |
| **24-Hour Spline Chart & Interactive Scrubbing** | **A** | Fully supported by Open-Meteo hourly feed and local chart state. |
| **Official IMD Advisory Banner & Severity Badging** | **A** | Fully supported by backend advisory service and CAP parser. |
| **Settlement Coordinate Map Marker & Warning Polygon** | **A** | Fully supported by Leaflet map component and GeoJSON polygon renderer. |
| **Streamlined Borderless Single Telemetry Strip** | **A** | Frontend layout refinement only; uses existing response schema. |
| **Elimination of Duplicate Card Grids** | **A** | Frontend DOM refactor only. |
| **Locality / Settlement Ambiguity Resolver Dropdown** | **B** | Requires returning structured candidate lists from backend geocoder. |
| **Administrative Breadcrumb Display (Village/Tehsil/Dist)** | **C** | Requires linking the gazetteer resolution schema to the geocode response. |
| **Multi-Settlement Comparison on Unified Time Axis** | **B** | Supported in data; requires minor frontend alignment polish. |
| **Live Doppler Radar Animation Overlay** | **D** | **Future Capability / Not Supported** (No radar tile server). |
| **Wind Particle Streamlines on Map** | **D** | **Future Capability / Not Supported** (No GRIB2 vector engine). |
| **Cloud Satellite Layer Overlay** | **D** | **Future Capability / Not Supported** (No satellite imagery API). |

*Key*:
- **A**: Supported by current frontend/backend right now.
- **B**: Requires minor backend payload adjustment.
- **C**: Requires future nationwide gazetteer runtime integration (Phase 22E).
- **D**: Future capability / not currently supported (Must NOT be promised in UI).

---

## 23. Proposed Implementation Sequence

Following review and acceptance of this blueprint, implementation should proceed through structured, incremental phases:

1. **Phase UI-03 — Design Tokens & Core Layout Skeleton**:
   - Establish semantic CSS custom properties across Atheris, Vandal, Midnight, and Light.
   - Build the responsive, centered briefing container and base grid.
2. **Phase UI-04 — Unified Search Omnibar & Discovery State**:
   - Build the State A discovery canvas with capability messaging and voice controls.
   - Implement the smooth physical spring docking transition into State B.
3. **Phase UI-05 — WeatherGPT Hero & Streamlined Telemetry**:
   - Refactor `WeatherAnswerSurface` to make WeatherGPT the headline hero.
   - Eliminate duplicate card grids; build the unified, borderless telemetry row.
4. **Phase UI-06 — Interactive Forecast Scrubber Integration**:
   - Couple the 24-hour spline timeline to the Core Telemetry row so scrubbing updates metrics in real time.
5. **Phase UI-07 — Spatial Context & Map Polish**:
   - Refactor `WeatherMap` into the clean lower surface with edge-to-edge expandability.
   - Verify official advisory polygon rendering across all 4 themes.
6. **Phase UI-08 — Mobile Optimization & Visual Verification**:
   - Optimize single-thumb scrolling, touch scrubbing, and sticky navigation.
   - Full regression verification across all 418 backend tests and responsive viewports.

---

## 24. Open Questions for Technical Review

1. **Scrubber Persistence**: When the user hovers over an hour (e.g. 19:00), should the telemetry reset back to "current conditions" upon mouse-leave, or stay pinned until clicked/toggled? *(Recommendation: Automatically reset to current conditions 500ms after mouse-leave)*.
2. **Comparison Map Multi-Bounding**: In comparison queries (`Delhi vs Mumbai`), should the map automatically fit bounds to show both cities simultaneously, or provide a toggle to jump between them? *(Recommendation: Auto-fit bounds on load, with quick-focus chips for each city)*.
3. **Voice Feedback**: Should StormOps provide optional text-to-speech audio playback of the 1-sentence WeatherGPT synthesis for accessibility? *(Recommendation: Expose a quiet speaker icon next to the WeatherGPT headline for opt-in playback)*.

---

*This blueprint constitutes the complete design and interaction specification for StormOps Phase UI-02. All implementation work remains paused awaiting user review.*

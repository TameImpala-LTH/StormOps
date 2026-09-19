import React, { useMemo } from 'react';
import {
  MapPin,
  Thermometer,
  CloudRain,
  Droplets,
  Wind,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  Scale,
} from 'lucide-react';
import { ComparisonResponse, WeatherAlert } from '../types/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { useTheme } from '../context/ThemeContext';

interface ComparisonSurfaceProps {
  comparison: ComparisonResponse;
}

interface MetricRowData {
  key: string;
  label: string;
  icon: React.ReactNode;
  valA: number;
  valB: number;
  displayA: string;
  displayB: string;
  pctA: number;
  pctB: number;
  deltaText: string;
  deltaLead: 'a' | 'b' | 'equal';
  impactNote?: string;
}

export const ComparisonSurface: React.FC<ComparisonSurfaceProps> = ({ comparison }) => {
  const { theme, darkVariant, accentColor } = useTheme();

  const {
    location_a: locA,
    location_b: locB,
    period_weather_a: pwA,
    period_weather_b: pwB,
    decision: compDec,
    alerts_a: alertsA = [],
    alerts_b: alertsB = [],
    comparison_goal: goal = 'general',
  } = comparison;

  // Harmonious theme-aware accent colors matching WeatherMap markers
  const colorA = accentColor;
  const colorB = theme === 'night' ? '#38bdf8' : theme === 'light' ? '#0284c7' : darkVariant === 'vandal' ? '#fb923c' : '#a78bfa';

  const isWinnerA = compDec.recommended_key === 'a';
  const isWinnerB = compDec.recommended_key === 'b';
  const isSimilar = compDec.recommended_key === 'equal';

  // Compute the 6 key shared meteorological metrics
  const metrics = useMemo<MetricRowData[]>(() => {
    const list: MetricRowData[] = [];

    // Helper to find impact note from backend factors
    const findNote = (matchKeys: string[]): string | undefined => {
      const f = compDec.factors?.find((factor) =>
        matchKeys.some((k) => factor.metric.toLowerCase().includes(k))
      );
      return f?.impact_note;
    };

    // 1. Temperature
    const tA = Math.round(pwA.temperature);
    const tB = Math.round(pwB.temperature);
    const tDiff = tB - tA;
    const tMin = Math.min(0, Math.min(tA, tB) - 5);
    const tMax = Math.max(42, Math.max(tA, tB) + 5);
    const tRange = Math.max(1, tMax - tMin);
    list.push({
      key: 'temperature',
      label: 'Temperature',
      icon: <Thermometer className="w-3.5 h-3.5" />,
      valA: tA,
      valB: tB,
      displayA: `${tA}°C`,
      displayB: `${tB}°C`,
      pctA: Math.max(6, Math.min(100, ((tA - tMin) / tRange) * 100)),
      pctB: Math.max(6, Math.min(100, ((tB - tMin) / tRange) * 100)),
      deltaText: tDiff === 0 ? '0°C' : tDiff > 0 ? `+${tDiff}°C` : `${tDiff}°C`,
      deltaLead: tDiff === 0 ? 'equal' : tDiff > 0 ? 'b' : 'a',
      impactNote: findNote(['temperature', 'temp']),
    });

    // 2. Feels-Like Temperature
    const flA = Math.round(pwA.feels_like);
    const flB = Math.round(pwB.feels_like);
    const flDiff = flB - flA;
    const flMin = Math.min(0, Math.min(flA, flB) - 5);
    const flMax = Math.max(42, Math.max(flA, flB) + 5);
    const flRange = Math.max(1, flMax - flMin);
    list.push({
      key: 'feels_like',
      label: 'Feels Like',
      icon: <Thermometer className="w-3.5 h-3.5 opacity-75" />,
      valA: flA,
      valB: flB,
      displayA: `${flA}°C`,
      displayB: `${flB}°C`,
      pctA: Math.max(6, Math.min(100, ((flA - flMin) / flRange) * 100)),
      pctB: Math.max(6, Math.min(100, ((flB - flMin) / flRange) * 100)),
      deltaText: flDiff === 0 ? '0°C' : flDiff > 0 ? `+${flDiff}°C` : `${flDiff}°C`,
      deltaLead: flDiff === 0 ? 'equal' : flDiff > 0 ? 'b' : 'a',
      impactNote: findNote(['feels_like', 'apparent']),
    });

    // 3. Rain Probability
    const rpA = pwA.precipitation_probability;
    const rpB = pwB.precipitation_probability;
    const rpDiff = rpB - rpA;
    list.push({
      key: 'rain_probability',
      label: 'Rain Probability',
      icon: <CloudRain className="w-3.5 h-3.5" />,
      valA: rpA,
      valB: rpB,
      displayA: `${rpA}%`,
      displayB: `${rpB}%`,
      pctA: rpA,
      pctB: rpB,
      deltaText: rpDiff === 0 ? '0%' : rpDiff > 0 ? `+${rpDiff}%` : `${rpDiff}%`,
      deltaLead: rpDiff === 0 ? 'equal' : rpDiff > 0 ? 'b' : 'a',
      impactNote: findNote(['precipitation_probability', 'rain', 'probability']),
    });

    // 4. Precipitation Amount
    const prA = pwA.precipitation;
    const prB = pwB.precipitation;
    const prDiff = Math.round((prB - prA) * 10) / 10;
    const prMax = Math.max(10, Math.max(prA, prB) * 1.25);
    list.push({
      key: 'precipitation',
      label: 'Precipitation',
      icon: <Droplets className="w-3.5 h-3.5" />,
      valA: prA,
      valB: prB,
      displayA: `${prA} mm`,
      displayB: `${prB} mm`,
      pctA: prA === 0 ? 0 : Math.max(5, Math.min(100, (prA / prMax) * 100)),
      pctB: prB === 0 ? 0 : Math.max(5, Math.min(100, (prB / prMax) * 100)),
      deltaText: prDiff === 0 ? '0 mm' : prDiff > 0 ? `+${prDiff} mm` : `${prDiff} mm`,
      deltaLead: prDiff === 0 ? 'equal' : prDiff > 0 ? 'b' : 'a',
      impactNote: findNote(['precipitation', 'rainfall']),
    });

    // 5. Wind Speed
    const wsA = Math.round(pwA.wind_speed);
    const wsB = Math.round(pwB.wind_speed);
    const wsDiff = wsB - wsA;
    const wsMax = Math.max(45, Math.max(wsA, wsB) * 1.2);
    list.push({
      key: 'wind_speed',
      label: 'Wind Speed',
      icon: <Wind className="w-3.5 h-3.5" />,
      valA: wsA,
      valB: wsB,
      displayA: `${wsA} km/h`,
      displayB: `${wsB} km/h`,
      pctA: Math.max(5, Math.min(100, (wsA / wsMax) * 100)),
      pctB: Math.max(5, Math.min(100, (wsB / wsMax) * 100)),
      deltaText: wsDiff === 0 ? '0 km/h' : wsDiff > 0 ? `+${wsDiff} km/h` : `${wsDiff} km/h`,
      deltaLead: wsDiff === 0 ? 'equal' : wsDiff > 0 ? 'b' : 'a',
      impactNote: findNote(['wind_speed', 'wind']),
    });

    // 6. Humidity
    const hA = pwA.humidity;
    const hB = pwB.humidity;
    const hDiff = hB - hA;
    list.push({
      key: 'humidity',
      label: 'Humidity',
      icon: <Droplets className="w-3.5 h-3.5 opacity-75" />,
      valA: hA,
      valB: hB,
      displayA: `${hA}%`,
      displayB: `${hB}%`,
      pctA: hA,
      pctB: hB,
      deltaText: hDiff === 0 ? '0%' : hDiff > 0 ? `+${hDiff}%` : `${hDiff}%`,
      deltaLead: hDiff === 0 ? 'equal' : hDiff > 0 ? 'b' : 'a',
      impactNote: findNote(['humidity']),
    });

    return list;
  }, [pwA, pwB, compDec.factors]);

  // Render individual alert badge
  const renderAlertItem = (alert: WeatherAlert) => {
    const isWarn = alert.severity === 'warning';
    const isWatch = alert.severity === 'watch';
    // Advisory fallback color: uses the themed accent (Vandal=red, Atheris=blue, etc.)
    const advisoryColor = colorA;
    const bg = isWarn ? 'rgba(225,29,72,0.10)' : isWatch ? 'rgba(217,119,6,0.10)' : 'rgba(56,189,248,0.10)';
    const border = isWarn ? 'rgba(225,29,72,0.30)' : isWatch ? 'rgba(217,119,6,0.30)' : 'rgba(56,189,248,0.25)';
    const color = isWarn ? '#f43f5e' : isWatch ? '#fbbf24' : advisoryColor;

    return (
      <div
        key={alert.id}
        className="p-2.5 rounded-xl border text-xs flex items-start gap-2"
        style={{ backgroundColor: bg, borderColor: border, color }}
      >
        {isWarn ? (
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        ) : (
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <div className="font-semibold leading-tight">{alert.title}</div>
          {alert.summary && (
            <div className="text-[11px] opacity-90 mt-0.5 line-clamp-2 leading-relaxed">
              {alert.summary}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 pt-2">
      {/* 1. Comparison Recommendation Hero Box */}
      <div
        className="p-5 sm:p-6 rounded-3xl border space-y-4 shadow-sm relative overflow-hidden"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border)',
        }}
      >
        {/* Top Header Row */}
        <div
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b"
          style={{ borderColor: 'var(--border-muted)' }}
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Scale className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-mono uppercase tracking-wider font-semibold" style={{ color: 'var(--accent)' }}>
                Location Comparison
              </span>
              <span
                className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border"
                style={{
                  backgroundColor: 'var(--surface)',
                  borderColor: 'var(--border-muted)',
                  color: 'var(--text-secondary)',
                }}
              >
                Goal: {goal.replace(/_/g, ' ')}
              </span>
            </div>
            <h3 className="text-xl sm:text-2xl font-light tracking-tight flex items-center gap-2 flex-wrap" style={{ color: 'var(--text-primary)' }}>
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ backgroundColor: colorA, boxShadow: `0 0 6px ${colorA}` }}
                />
                {locA.name}
              </span>
              <span className="text-xs font-mono px-1.5 py-0.5 rounded text-zinc-500 bg-zinc-800/40">
                VS
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ backgroundColor: colorB, boxShadow: `0 0 6px ${colorB}` }}
                />
                {locB.name}
              </span>
            </h3>
          </div>

          {/* Recommendation & Confidence Badges */}
          <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
            <span
              className="px-3.5 py-1.5 rounded-full text-xs font-mono font-bold uppercase tracking-wider border flex items-center gap-1.5"
              style={{
                backgroundColor: isSimilar ? 'rgba(217,119,6,0.12)' : 'rgba(16,185,129,0.12)',
                borderColor: isSimilar ? 'rgba(217,119,6,0.30)' : 'rgba(16,185,129,0.30)',
                color: isSimilar ? '#fbbf24' : '#34d399',
              }}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {isSimilar ? 'Broadly Similar' : `Winner: ${compDec.recommended_location}`}
            </span>
            <span
              className="text-[11px] font-mono uppercase px-2.5 py-1 rounded-lg border"
              style={{
                backgroundColor: 'var(--surface)',
                color: 'var(--text-secondary)',
                borderColor: 'var(--border-muted)',
              }}
            >
              {compDec.confidence} confidence
            </span>
          </div>
        </div>

        {/* Summary & Reasoning */}
        <div className="space-y-2">
          <p className="text-sm font-medium leading-relaxed" style={{ color: 'var(--text-primary)' }}>
            {compDec.summary}
          </p>
          {compDec.winner_reason && (
            <div
              className="text-xs p-3 rounded-xl border flex items-start gap-2 leading-relaxed font-mono"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
                color: 'var(--text-secondary)',
              }}
            >
              <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-zinc-400" />
              <div>
                <span className="font-semibold text-zinc-300">Decision factors: </span>
                {compDec.winner_reason}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. Side-by-Side Location Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Location A Card */}
        <div
          className={`p-5 rounded-2xl border space-y-4 relative transition-all ${
            isWinnerA ? 'ring-2' : ''
          }`}
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: isWinnerA ? colorA : 'var(--border-muted)',
            boxShadow: isWinnerA ? `0 0 20px -5px ${colorA}30` : undefined,
          }}
        >
          {isWinnerA && (
            <div
              className="absolute top-3.5 right-3.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border flex items-center gap-1"
              style={{
                backgroundColor: `${colorA}18`,
                borderColor: `${colorA}40`,
                color: colorA,
              }}
            >
              <CheckCircle2 className="w-3 h-3" /> Recommended
            </div>
          )}

          {/* Location A Header */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span
                className="w-4 h-4 rounded flex items-center justify-center font-bold text-[10px]"
                style={{ backgroundColor: `${colorA}25`, color: colorA }}
              >
                A
              </span>
              <MapPin className="w-3.5 h-3.5" style={{ color: colorA }} />
              <span style={{ color: colorA }} className="font-semibold tracking-wider">
                LOCATION A
              </span>
            </div>
            <h4 className="text-xl font-medium tracking-tight" style={{ color: 'var(--text-primary)' }}>
              {locA.name}
              {locA.admin1 ? `, ${locA.admin1}` : ''}
              {locA.country ? ` (${locA.country})` : ''}
            </h4>
          </div>

          {/* Temp + Condition Hero */}
          <div className="flex items-center gap-3">
            <div
              className="p-2.5 rounded-xl border flex-shrink-0"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              {getWeatherIcon(pwA.weather_code, 'w-6 h-6')}
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl sm:text-4xl font-light" style={{ color: 'var(--text-primary)' }}>
                  {Math.round(pwA.temperature)}°C
                </span>
                <span className="text-xs capitalize font-medium" style={{ color: 'var(--text-secondary)' }}>
                  {pwA.condition}
                </span>
              </div>
              <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                Feels like {Math.round(pwA.feels_like)}°C
              </span>
            </div>
          </div>

          {/* Alerts Area */}
          <div className="pt-1 border-t" style={{ borderColor: 'var(--border-muted)' }}>
            {alertsA.length > 0 ? (
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono uppercase text-rose-400 font-semibold block">
                  Active Alerts ({alertsA.length})
                </span>
                {alertsA.map(renderAlertItem)}
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs font-mono py-1" style={{ color: 'var(--text-tertiary)' }}>
                <CheckCircle2 className="w-3 h-3 text-emerald-500/70" />
                <span>No active weather alerts</span>
              </div>
            )}
          </div>
        </div>

        {/* Location B Card */}
        <div
          className={`p-5 rounded-2xl border space-y-4 relative transition-all ${
            isWinnerB ? 'ring-2' : ''
          }`}
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: isWinnerB ? colorB : 'var(--border-muted)',
            boxShadow: isWinnerB ? `0 0 20px -5px ${colorB}30` : undefined,
          }}
        >
          {isWinnerB && (
            <div
              className="absolute top-3.5 right-3.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border flex items-center gap-1"
              style={{
                backgroundColor: `${colorB}18`,
                borderColor: `${colorB}40`,
                color: colorB,
              }}
            >
              <CheckCircle2 className="w-3 h-3" /> Recommended
            </div>
          )}

          {/* Location B Header */}
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span
                className="w-4 h-4 rounded flex items-center justify-center font-bold text-[10px]"
                style={{ backgroundColor: `${colorB}25`, color: colorB }}
              >
                B
              </span>
              <MapPin className="w-3.5 h-3.5" style={{ color: colorB }} />
              <span style={{ color: colorB }} className="font-semibold tracking-wider">
                LOCATION B
              </span>
            </div>
            <h4 className="text-xl font-medium tracking-tight" style={{ color: 'var(--text-primary)' }}>
              {locB.name}
              {locB.admin1 ? `, ${locB.admin1}` : ''}
              {locB.country ? ` (${locB.country})` : ''}
            </h4>
          </div>

          {/* Temp + Condition Hero */}
          <div className="flex items-center gap-3">
            <div
              className="p-2.5 rounded-xl border flex-shrink-0"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              {getWeatherIcon(pwB.weather_code, 'w-6 h-6')}
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl sm:text-4xl font-light" style={{ color: 'var(--text-primary)' }}>
                  {Math.round(pwB.temperature)}°C
                </span>
                <span className="text-xs capitalize font-medium" style={{ color: 'var(--text-secondary)' }}>
                  {pwB.condition}
                </span>
              </div>
              <span className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                Feels like {Math.round(pwB.feels_like)}°C
              </span>
            </div>
          </div>

          {/* Alerts Area */}
          <div className="pt-1 border-t" style={{ borderColor: 'var(--border-muted)' }}>
            {alertsB.length > 0 ? (
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono uppercase text-rose-400 font-semibold block">
                  Active Alerts ({alertsB.length})
                </span>
                {alertsB.map(renderAlertItem)}
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs font-mono py-1" style={{ color: 'var(--text-tertiary)' }}>
                <CheckCircle2 className="w-3 h-3 text-emerald-500/70" />
                <span>No active weather alerts</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Visual Metric-by-Metric Comparison Gauges */}
      <div
        className="p-5 sm:p-6 rounded-3xl border space-y-5"
        style={{
          backgroundColor: 'var(--surface-elevated)',
          borderColor: 'var(--border-muted)',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-3 border-b" style={{ borderColor: 'var(--border-muted)' }}>
          <div>
            <h4 className="text-sm font-semibold tracking-tight uppercase font-mono" style={{ color: 'var(--text-primary)' }}>
              Direct Metric Comparison
            </h4>
            <span className="text-xs text-zinc-400">
              Normalized comparative gauges with exact delta calculations
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono mt-1 sm:mt-0">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colorA }} />
              <span style={{ color: 'var(--text-secondary)' }}>A: {locA.name}</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colorB }} />
              <span style={{ color: 'var(--text-secondary)' }}>B: {locB.name}</span>
            </span>
          </div>
        </div>

        {/* 6 Metric Comparison Cards in a 2-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {metrics.map((m) => (
            <div
              key={m.key}
              className="p-4 rounded-2xl border space-y-3 transition-colors"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-muted)',
              }}
            >
              {/* Metric Title & Delta */}
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                  <span style={{ color: 'var(--accent)' }}>{m.icon}</span>
                  {m.label}
                </span>
                <span
                  className="font-mono text-[11px] px-2 py-0.5 rounded border font-semibold"
                  style={{
                    backgroundColor: 'var(--surface-elevated)',
                    borderColor: 'var(--border-muted)',
                    color:
                      m.deltaLead === 'equal'
                        ? 'var(--text-tertiary)'
                        : m.deltaLead === 'a'
                        ? colorA
                        : colorB,
                  }}
                  title={`Delta: ${m.deltaText}`}
                >
                  Δ {m.deltaText}
                </span>
              </div>

              {/* Bar Visuals for A and B */}
              <div className="space-y-2">
                {/* Location A Bar */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="flex items-center gap-1 font-medium" style={{ color: colorA }}>
                      <span className="text-[10px] px-1 py-0.2 rounded font-bold" style={{ backgroundColor: `${colorA}20` }}>
                        A
                      </span>
                      <span className="truncate max-w-[120px]">{locA.name}</span>
                    </span>
                    <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {m.displayA}
                    </span>
                  </div>
                  <div
                    className="w-full h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-muted)' }}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${m.pctA}%`,
                        backgroundColor: colorA,
                        opacity: 0.85,
                      }}
                    />
                  </div>
                </div>

                {/* Location B Bar */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="flex items-center gap-1 font-medium" style={{ color: colorB }}>
                      <span className="text-[10px] px-1 py-0.2 rounded font-bold" style={{ backgroundColor: `${colorB}20` }}>
                        B
                      </span>
                      <span className="truncate max-w-[120px]">{locB.name}</span>
                    </span>
                    <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {m.displayB}
                    </span>
                  </div>
                  <div
                    className="w-full h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: 'var(--surface-elevated)', border: '1px solid var(--border-muted)' }}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${m.pctB}%`,
                        backgroundColor: colorB,
                        opacity: 0.85,
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Contextual Factor Impact Note */}
              {m.impactNote && (
                <div
                  className="text-[11px] pt-2 border-t font-mono leading-relaxed"
                  style={{
                    borderColor: 'var(--border-muted)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <span className="text-zinc-400">Context: </span>
                  {m.impactNote}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

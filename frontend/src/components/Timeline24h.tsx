import React from 'react';
import { HourlyForecast } from '../types/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { Clock } from 'lucide-react';

interface Timeline24hProps {
  hourly: HourlyForecast[];
}

export const Timeline24h: React.FC<Timeline24hProps> = ({ hourly }) => {
  if (!hourly || hourly.length === 0) return null;

  return (
    <div className="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-3xl p-6 backdrop-blur shadow-xl space-y-4">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-medium text-zinc-300 uppercase tracking-wider flex items-center gap-2">
          <Clock className="w-4 h-4 text-emerald-400" /> 24-Hour Hourly Timeline
        </h3>
        <span className="text-xs text-zinc-500 font-mono">Scroll →</span>
      </div>

      <div className="flex space-x-4 overflow-x-auto pb-4 pt-2 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent">
        {hourly.map((item, index) => {
          const timeStr = item.time.includes('T') ? item.time.split('T')[1].substring(0, 5) : item.time;

          return (
            <div
              key={index}
              className="flex-none w-24 bg-zinc-950/60 border border-zinc-800/60 hover:border-zinc-700/80 rounded-2xl p-4 text-center space-y-3 transition-colors group"
            >
              <div className="text-xs font-mono text-zinc-400">{timeStr}</div>

              <div className="flex justify-center py-1 group-hover:scale-110 transition-transform">
                {getWeatherIcon(item.weather_code, 'w-7 h-7')}
              </div>

              <div className="text-lg font-light text-zinc-100">{Math.round(item.temperature)}°</div>

              {item.precipitation_probability !== null && item.precipitation_probability !== undefined && item.precipitation_probability > 0 ? (
                <div className="text-[10px] font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 py-0.5 px-1.5 rounded-full inline-block">
                  {item.precipitation_probability}% rain
                </div>
              ) : (
                <div className="text-[10px] text-zinc-600 py-0.5 px-1.5 inline-block">0%</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

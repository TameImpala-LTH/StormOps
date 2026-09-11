import React from 'react';
import { CurrentWeather, LocationCoordinates } from '../types/weather';
import { getWeatherIcon } from '../utils/weatherIcons';
import { Droplets, Wind, Umbrella, Thermometer } from 'lucide-react';

interface CurrentWeatherCardProps {
  location: LocationCoordinates;
  current: CurrentWeather;
  displayName: string;
}

export const CurrentWeatherCard: React.FC<CurrentWeatherCardProps> = ({
  location,
  current,
  displayName,
}) => {
  return (
    <div className="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-3xl p-8 backdrop-blur shadow-xl space-y-8">
      {/* Location & Time Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-light text-zinc-100 tracking-tight">{displayName}</h2>
          <p className="text-sm text-zinc-500 mt-0.5">
            {location.timezone ? `Timezone: ${location.timezone}` : `Lat: ${location.latitude}, Lon: ${location.longitude}`}
          </p>
        </div>
        <div className="px-3 py-1 bg-zinc-800/60 rounded-full text-xs font-mono text-zinc-400 border border-zinc-700/40">
          Observed {current.time.includes('T') ? current.time.split('T')[1] : current.time}
        </div>
      </div>

      {/* Main Temperature & Condition Display */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 py-2">
        <div className="flex items-center space-x-6">
          <div className="p-4 bg-zinc-800/40 rounded-2xl border border-zinc-700/30">
            {getWeatherIcon(current.weather_code, 'w-12 h-12')}
          </div>
          <div>
            <div className="text-6xl font-extralight text-white tracking-tighter">
              {Math.round(current.temperature)}°
              <span className="text-3xl font-light text-zinc-400 font-sans ml-1">C</span>
            </div>
            <p className="text-lg font-normal text-zinc-300 capitalize mt-1">
              {current.condition}
            </p>
          </div>
        </div>

        <div className="sm:text-right border-t sm:border-t-0 sm:border-l border-zinc-800 pt-4 sm:pt-0 sm:pl-8">
          <div className="text-xs uppercase tracking-wider text-zinc-500 font-medium">Feels Like</div>
          <div className="text-3xl font-light text-zinc-200 mt-1">
            {Math.round(current.feels_like)}°C
          </div>
        </div>
      </div>

      {/* Metric Pills Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
        <div className="bg-zinc-950/50 border border-zinc-800/60 rounded-2xl p-4 flex items-center space-x-3">
          <div className="p-2 bg-blue-500/10 rounded-xl text-blue-400">
            <Droplets className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-zinc-500 font-medium">Humidity</div>
            <div className="text-base font-medium text-zinc-200">{current.humidity}%</div>
          </div>
        </div>

        <div className="bg-zinc-950/50 border border-zinc-800/60 rounded-2xl p-4 flex items-center space-x-3">
          <div className="p-2 bg-teal-500/10 rounded-xl text-teal-400">
            <Wind className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-zinc-500 font-medium">Wind Speed</div>
            <div className="text-base font-medium text-zinc-200">{current.wind_speed} km/h</div>
          </div>
        </div>

        <div className="bg-zinc-950/50 border border-zinc-800/60 rounded-2xl p-4 flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400">
            <Umbrella className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-zinc-500 font-medium">Rain Chance</div>
            <div className="text-base font-medium text-zinc-200">
              {current.precipitation_probability !== null && current.precipitation_probability !== undefined
                ? `${current.precipitation_probability}%`
                : '0%'}
            </div>
          </div>
        </div>

        <div className="bg-zinc-950/50 border border-zinc-800/60 rounded-2xl p-4 flex items-center space-x-3">
          <div className="p-2 bg-purple-500/10 rounded-xl text-purple-400">
            <Thermometer className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-zinc-500 font-medium">Precipitation</div>
            <div className="text-base font-medium text-zinc-200">{current.precipitation} mm</div>
          </div>
        </div>
      </div>
    </div>
  );
};

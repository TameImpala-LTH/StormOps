import React from 'react';
import {
  Sun,
  CloudSun,
  Cloud,
  CloudDrizzle,
  CloudRain,
  CloudSnow,
  CloudLightning,
  CloudFog,
} from 'lucide-react';

export const getWeatherIcon = (code: number, className = 'w-6 h-6'): React.ReactNode => {
  if (code === 0) {
    return <Sun className={`${className} text-amber-400`} />;
  }
  if (code === 1 || code === 2) {
    return <CloudSun className={`${className} text-sky-300`} />;
  }
  if (code === 3) {
    return <Cloud className={`${className} text-slate-400`} />;
  }
  if (code === 45 || code === 48) {
    return <CloudFog className={`${className} text-slate-400`} />;
  }
  if (code >= 51 && code <= 57) {
    return <CloudDrizzle className={`${className} text-blue-300`} />;
  }
  if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) {
    return <CloudRain className={`${className} text-blue-400`} />;
  }
  if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) {
    return <CloudSnow className={`${className} text-indigo-200`} />;
  }
  if (code >= 95) {
    return <CloudLightning className={`${className} text-amber-300`} />;
  }
  return <Cloud className={`${className} text-slate-400`} />;
};

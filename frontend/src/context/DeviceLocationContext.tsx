import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { GeocodedLocationSchema } from '../types/weather';
import { fetchCurrentWeather } from '../services/weather';

interface DeviceLocationContextType {
  deviceLocation: GeocodedLocationSchema | null;
  deviceTemperature: number | null;
  isLocating: boolean;
  requestDeviceLocation: () => Promise<void>;
}

const DeviceLocationContext = createContext<DeviceLocationContextType | undefined>(undefined);

export const DeviceLocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [deviceLocation, setDeviceLocation] = useState<GeocodedLocationSchema | null>(null);
  const [deviceTemperature, setDeviceTemperature] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);

  const requestDeviceLocation = useCallback(async () => {
    if (!navigator.geolocation) {
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          
          // Fetch current weather at device coordinates to get current temp & timezone
          const weatherData = await fetchCurrentWeather(lat, lon);
          
          // Reverse geocode via OpenStreetMap Nominatim client-side or fallback to weather location
          let locationName = weatherData.location?.name;
          let country = 'India';
          let admin1: string | undefined = undefined;
          
          try {
            const nomRes = await fetch(
              `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=16`,
              { headers: { 'User-Agent': 'StormOps-WeatherGPT/1.0' } }
            );
            if (nomRes.ok) {
              const data = await nomRes.json();
              const addr = data.address || {};
              const locality =
                addr.suburb ||
                addr.neighbourhood ||
                addr.quarter ||
                addr.city_district ||
                addr.residential ||
                addr.village ||
                addr.hamlet;
              const city =
                addr.city ||
                addr.town ||
                addr.municipality ||
                addr.county ||
                addr.state_district;
              country = addr.country || country;
              admin1 = addr.state;
              
              if (locality && city && locality.toLowerCase() !== city.toLowerCase()) {
                locationName = `${locality}, ${city}`;
              } else if (locality) {
                locationName = locality;
              } else if (city) {
                locationName = city;
              }
            }
          } catch {
            // Use fallback name if reverse geocoding fails
          }

          const devLoc: GeocodedLocationSchema = {
            name: locationName || `Current Location (${lat.toFixed(2)}, ${lon.toFixed(2)})`,
            country: country,
            admin1: admin1,
            latitude: lat,
            longitude: lon,
            timezone: weatherData.location?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          };

          setDeviceLocation(devLoc);
          if (typeof weatherData.current?.temperature === 'number') {
            setDeviceTemperature(weatherData.current.temperature);
          }
        } catch {
          // If network fails, silently maintain previous or neutral state
        } finally {
          setIsLocating(false);
        }
      },
      () => {
        // Geolocation permission denied or unavailable - keep neutral state, do not spam prompts
        setIsLocating(false);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }, []);

  // Safe one-time initialization attempt on app load
  useEffect(() => {
    // Check permission state if permissions API is available to avoid unexpected prompts
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'geolocation' as PermissionName }).then((result) => {
        if (result.state === 'granted') {
          requestDeviceLocation();
        }
      }).catch(() => {
        // Fallback: don't auto-prompt if permissions API check fails
      });
    }
  }, [requestDeviceLocation]);

  return (
    <DeviceLocationContext.Provider
      value={{
        deviceLocation,
        deviceTemperature,
        isLocating,
        requestDeviceLocation,
      }}
    >
      {children}
    </DeviceLocationContext.Provider>
  );
};

export const useDeviceLocation = (): DeviceLocationContextType => {
  const ctx = useContext(DeviceLocationContext);
  if (!ctx) {
    throw new Error('useDeviceLocation must be used within a DeviceLocationProvider');
  }
  return ctx;
};

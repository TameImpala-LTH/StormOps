import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { GeocodedLocationSchema } from '../types/weather';
import { fetchCurrentWeather } from '../services/weather';

interface DeviceLocationContextType {
  deviceLocation: GeocodedLocationSchema | null;
  deviceTemperature: number | null;
  isLocating: boolean;
  requestDeviceLocation: () => Promise<void>;
}

const DeviceLocationContext = createContext<DeviceLocationContextType | undefined>(undefined);

// 5-minute cooldown for client-side device weather re-fetching
const REFETCH_COOLDOWN_MS = 5 * 60 * 1000;

export const DeviceLocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [deviceLocation, setDeviceLocation] = useState<GeocodedLocationSchema | null>(null);
  const [deviceTemperature, setDeviceTemperature] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);

  const isLocatingRef = useRef<boolean>(false);
  const deviceLocationRef = useRef<GeocodedLocationSchema | null>(null);
  const lastFetchRef = useRef<{ lat: number; lon: number; timestamp: number } | null>(null);

  const requestDeviceLocation = useCallback(async () => {
    if (!navigator.geolocation || isLocatingRef.current) {
      return;
    }

    isLocatingRef.current = true;
    setIsLocating(true);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          const now = Date.now();

          // Check if we recently fetched weather for these exact coordinates and already have location set
          if (
            deviceLocationRef.current &&
            lastFetchRef.current &&
            Math.abs(lastFetchRef.current.lat - lat) < 0.01 &&
            Math.abs(lastFetchRef.current.lon - lon) < 0.01 &&
            now - lastFetchRef.current.timestamp < REFETCH_COOLDOWN_MS
          ) {
            // Already have recent weather for these coordinates
            return;
          }

          // Concurrently fetch current weather and reverse geocode with timeout
          const nomController = new AbortController();
          const nomTimeout = setTimeout(() => nomController.abort(), 2500);

          const [weatherRes, nomRes] = await Promise.allSettled([
            fetchCurrentWeather(lat, lon),
            fetch(
              `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=16`,
              { signal: nomController.signal }
            ).then((r) => (r.ok ? r.json() : null)),
          ]);
          clearTimeout(nomTimeout);

          let weatherData: any = null;
          if (weatherRes.status === 'fulfilled') {
            weatherData = weatherRes.value;
            if (typeof weatherData?.current?.temperature === 'number') {
              setDeviceTemperature(weatherData.current.temperature);
            }
          }
          lastFetchRef.current = { lat, lon, timestamp: now };

          // Reverse geocode via OpenStreetMap Nominatim client-side or fallback to weather location
          let locationName = weatherData?.location?.name;
          let country = 'India';
          let admin1: string | undefined = undefined;

          if (nomRes.status === 'fulfilled' && nomRes.value) {
            const data = nomRes.value;
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

          const devLoc: GeocodedLocationSchema = {
            name: locationName || 'Current Location',
            country: country,
            admin1: admin1,
            latitude: lat,
            longitude: lon,
            timezone: weatherData?.location?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
          };

          deviceLocationRef.current = devLoc;
          setDeviceLocation(devLoc);
        } catch {
          // If unexpected error, silently maintain previous state
        } finally {
          isLocatingRef.current = false;
          setIsLocating(false);
        }
      },
      () => {
        // Geolocation permission denied or unavailable
        isLocatingRef.current = false;
        setIsLocating(false);
      },
      { timeout: 15000, enableHighAccuracy: true, maximumAge: 60000 }
    );
  }, []);

  // Safe one-time initialization attempt on app load
  useEffect(() => {
    if (!navigator.geolocation) {
      return;
    }

    let permissionStatus: PermissionStatus | null = null;

    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions
        .query({ name: 'geolocation' as PermissionName })
        .then((result) => {
          permissionStatus = result;
          if (result.state === 'granted' || result.state === 'prompt') {
            requestDeviceLocation();
          }
          result.onchange = () => {
            if (result.state === 'granted') {
              requestDeviceLocation();
            }
          };
        })
        .catch(() => {
          // Fallback for browsers (like Safari) where permissions.query for geolocation fails
          requestDeviceLocation();
        });
    } else {
      // Fallback for browsers without permissions.query
      requestDeviceLocation();
    }

    return () => {
      if (permissionStatus) {
        permissionStatus.onchange = null;
      }
    };
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

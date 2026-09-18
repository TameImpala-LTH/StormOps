/**
 * Frontend weather API service for fetching current weather, forecast, and posting natural language queries to FastAPI backend.
 */

import axios from 'axios';
import { CoordinateInput, CurrentWeatherResponse, ForecastResponse, QueryResponse } from '../types/weather';

const API_BASE_URL = '/api/weather';

// In-memory cache & in-flight deduplication for current weather
const currentWeatherCache = new Map<string, { data: CurrentWeatherResponse; timestamp: number }>();
const inFlightCurrentWeather = new Map<string, Promise<CurrentWeatherResponse>>();
const WEATHER_CACHE_TTL_MS = 60_000; // 1 minute client cache

export const fetchCurrentWeather = async (
  latitude: number,
  longitude: number
): Promise<CurrentWeatherResponse> => {
  const cacheKey = `${latitude.toFixed(2)},${longitude.toFixed(2)}`;
  const cached = currentWeatherCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < WEATHER_CACHE_TTL_MS) {
    return cached.data;
  }

  if (inFlightCurrentWeather.has(cacheKey)) {
    return inFlightCurrentWeather.get(cacheKey)!;
  }

  const promise = (async () => {
    try {
      const response = await axios.get<CurrentWeatherResponse>(`${API_BASE_URL}/current`, {
        params: { latitude, longitude },
      });
      currentWeatherCache.set(cacheKey, { data: response.data, timestamp: Date.now() });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        throw new Error(error.response.data?.detail || 'Failed to fetch current weather.');
      }
      throw new Error('Network error while connecting to weather service.');
    } finally {
      inFlightCurrentWeather.delete(cacheKey);
    }
  })();

  inFlightCurrentWeather.set(cacheKey, promise);
  return promise;
};

export const fetchForecast = async (
  latitude: number,
  longitude: number,
  hours: number = 24
): Promise<ForecastResponse> => {
  try {
    const response = await axios.get<ForecastResponse>(`${API_BASE_URL}/forecast`, {
      params: { latitude, longitude, hours },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(error.response.data?.detail || 'Failed to fetch weather forecast.');
    }
    throw new Error('Network error while connecting to weather service.');
  }
};

const SESSION_ID = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

export const postWeatherQuery = async (
  message: string,
  customSessionId?: string,
  location?: CoordinateInput,
  language?: string
): Promise<QueryResponse> => {
  try {
    const response = await axios.post<QueryResponse>('/api/chat', {
      message,
      session_id: customSessionId || SESSION_ID,
      ...(location ? { location } : {}),
      ...(language && language !== 'auto' ? { language } : {}),
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(error.response.data?.detail || 'Failed to process natural language weather query.');
    }
    throw new Error('Network error while connecting to weather service.');
  }
};

export const fetchLocationEvents = async (location: string): Promise<import('../types/weather').EnvironmentalEvent[]> => {
  try {
    const response = await axios.get<import('../types/weather').EnvironmentalEvent[]>(`${API_BASE_URL}/events`, {
      params: { location },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch environmental events:', error);
    return [];
  }
};

// In-memory cache & in-flight deduplication for advisories
const advisoryCache = new Map<string, { data: import('../types/advisory').OfficialAdvisory[]; timestamp: number }>();
const inFlightAdvisories = new Map<string, Promise<import('../types/advisory').OfficialAdvisory[]>>();
const ADVISORY_CACHE_TTL_MS = 60_000; // 1 minute client cache

export const fetchOfficialAdvisories = async (
  params: import('../types/advisory').AdvisoryQueryParams
): Promise<import('../types/advisory').OfficialAdvisory[]> => {
  const cacheKey = JSON.stringify(params);
  const cached = advisoryCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < ADVISORY_CACHE_TTL_MS) {
    return cached.data;
  }

  if (inFlightAdvisories.has(cacheKey)) {
    return inFlightAdvisories.get(cacheKey)!;
  }

  const promise = (async () => {
    try {
      const response = await axios.get<import('../types/advisory').AdvisoryListResponse>(`${API_BASE_URL}/advisories`, {
        params,
      });
      const advisories = response.data?.advisories || [];
      advisoryCache.set(cacheKey, { data: advisories, timestamp: Date.now() });
      return advisories;
    } catch (error) {
      // Graceful degradation: never crash UI on advisory lookup failure
      console.warn('Official advisory lookup failed, degrading gracefully:', error);
      return [];
    } finally {
      inFlightAdvisories.delete(cacheKey);
    }
  })();

  inFlightAdvisories.set(cacheKey, promise);
  return promise;
};



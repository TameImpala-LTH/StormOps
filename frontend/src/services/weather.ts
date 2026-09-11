/**
 * Frontend weather API service for fetching current weather, forecast, and posting natural language queries to FastAPI backend.
 */

import axios from 'axios';
import { CoordinateInput, CurrentWeatherResponse, ForecastResponse, QueryResponse } from '../types/weather';

const API_BASE_URL = '/api/weather';

export const fetchCurrentWeather = async (
  latitude: number,
  longitude: number
): Promise<CurrentWeatherResponse> => {
  try {
    const response = await axios.get<CurrentWeatherResponse>(`${API_BASE_URL}/current`, {
      params: { latitude, longitude },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(error.response.data?.detail || 'Failed to fetch current weather.');
    }
    throw new Error('Network error while connecting to weather service.');
  }
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


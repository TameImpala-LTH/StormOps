/**
 * Frontend authentication, history, and saved location API client.
 */

import axios from 'axios';
import {
  User,
  TokenResponse,
  ConversationSummary,
  ConversationDetail,
  SavedLocationItem,
} from '../types/auth';

const TOKEN_STORAGE_KEY = 'stormops_access_token';

// Retrieve stored token
export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
};

// Store token
export const setStoredToken = (token: string | null): void => {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage quota or access errors
  }
};

// Configure Axios default request interceptor to attach Bearer token automatically
axios.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Configure Axios response interceptor to handle expired tokens gracefully
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && getStoredToken()) {
      // Clear expired token and trigger storage event
      setStoredToken(null);
      window.dispatchEvent(new CustomEvent('stormops_auth_expired'));
    }
    return Promise.reject(error);
  }
);

export const registerUser = async (
  email: string,
  password: string,
  displayName: string
): Promise<TokenResponse> => {
  const response = await axios.post<TokenResponse>('/api/auth/register', {
    email,
    password,
    display_name: displayName,
  });
  setStoredToken(response.data.access_token);
  return response.data;
};

export const loginUser = async (email: string, password: string): Promise<TokenResponse> => {
  const response = await axios.post<TokenResponse>('/api/auth/login', {
    email,
    password,
  });
  setStoredToken(response.data.access_token);
  return response.data;
};

export const fetchCurrentUser = async (): Promise<User> => {
  const response = await axios.get<User>('/api/auth/me');
  return response.data;
};

export const logoutUser = (): void => {
  setStoredToken(null);
};

// Conversation History API
export const fetchUserHistory = async (): Promise<ConversationSummary[]> => {
  const response = await axios.get<ConversationSummary[]>('/api/history');
  return response.data;
};

export const fetchConversationDetail = async (conversationId: string): Promise<ConversationDetail> => {
  const response = await axios.get<ConversationDetail>(`/api/history/${conversationId}`);
  return response.data;
};

export const deleteUserConversation = async (conversationId: string): Promise<void> => {
  await axios.delete(`/api/history/${conversationId}`);
};

// Saved Locations API
export const fetchSavedLocations = async (): Promise<SavedLocationItem[]> => {
  const response = await axios.get<SavedLocationItem[]>('/api/locations');
  return response.data;
};

export const createSavedLocation = async (
  name: string,
  latitude: number,
  longitude: number,
  country?: string
): Promise<SavedLocationItem> => {
  const response = await axios.post<SavedLocationItem>('/api/locations', {
    name,
    latitude,
    longitude,
    country,
  });
  return response.data;
};

export const deleteSavedLocation = async (locationId: string): Promise<void> => {
  await axios.delete(`/api/locations/${locationId}`);
};

// Environmental Outlook API
export const fetchEnvironmentalOutlook = async (
  currentLocation?: string | null
): Promise<import('../types/auth').EnvironmentalOutlookResponse> => {
  const params: Record<string, string> = {};
  if (currentLocation && currentLocation.trim()) {
    params.current_location = currentLocation.trim();
  }
  const response = await axios.get<import('../types/auth').EnvironmentalOutlookResponse>(
    '/api/environmental/outlook',
    { params }
  );
  return response.data;
};


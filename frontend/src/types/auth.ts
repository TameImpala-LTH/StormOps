/**
 * TypeScript definitions for multi-user authentication, history, and saved locations.
 */

export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  location_name?: string | null;
  created_at: string;
  updated_at: string;
  last_query?: string | null;
  last_answer?: string | null;
}

export interface ConversationDetail {
  id: string;
  title: string;
  location_name?: string | null;
  created_at: string;
  updated_at: string;
  messages: MessageItem[];
}

export interface SavedLocationItem {
  id: string;
  user_id: string;
  name: string;
  latitude: number;
  longitude: number;
  country?: string | null;
  created_at: string;
}

export interface EnvironmentalOutlookItem {
  event_id: string;
  event_title: string;
  category: string;
  location_name: string;
  start_date: string;
  end_date?: string | null;
  post_event_days: number;
  status: 'active' | 'upcoming' | 'post_event' | string;
  days_until?: number | null;
  advisory_summary: string;
  evidence_note: string;
  environmental_pressures: {
    type: string;
    level: string;
    evidence_type: string;
  }[];
  key_recommendations: string[];
  source_metadata: string;
}

export interface EnvironmentalOutlookResponse {
  items: EnvironmentalOutlookItem[];
  total_events: number;
  locations_evaluated: string[];
}


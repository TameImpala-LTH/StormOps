/**
 * Normalized Weather & Query Data Types matching backend Pydantic models.
 */

export interface CoordinateInput {
  latitude: number;
  longitude: number;
}

export interface LocationCoordinates {
  latitude: number;
  longitude: number;
  name?: string | null;
  timezone?: string | null;
}


export interface CurrentWeather {
  temperature: number;
  feels_like: number;
  condition: string;
  weather_code: number;
  humidity: number;
  wind_speed: number;
  precipitation: number;
  precipitation_probability?: number | null;
  time: string;
}

export interface HourlyForecast {
  time: string;
  temperature: number;
  feels_like?: number | null;
  condition: string;
  weather_code: number;
  precipitation_probability?: number | null;
  precipitation: number;
  wind_speed: number;
}

export interface CurrentWeatherResponse {
  location: LocationCoordinates;
  current: CurrentWeather;
  source: string;
  timestamp: string;
}

export interface ForecastResponse {
  location: LocationCoordinates;
  hourly: HourlyForecast[];
  source: string;
  timestamp: string;
}

export interface ExtractedQueryInfo {
  original_query: string;
  intent: string;
  extracted_location?: string | null;
  extracted_location_a?: string | null;
  extracted_location_b?: string | null;
  comparison_goal?: string | null;
  date_context: string;
  time_period: string;
  language?: 'en' | 'hi' | 'bn' | 'ta' | 'te' | 'mr' | string;
}

export type LanguageCode = 'auto' | 'en' | 'hi' | 'bn' | 'ta' | 'te' | 'mr';

export interface GeocodedLocationSchema {
  name: string;
  country: string;
  admin1?: string | null;
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface TargetPeriodWeather {
  period_label: string;
  temperature: number;
  feels_like: number;
  condition: string;
  weather_code: number;
  humidity: number;
  wind_speed: number;
  precipitation: number;
  precipitation_probability: number;
  rain_duration_hours?: number;
  peak_hour?: string | null;
  total_precipitation?: number;
}

export interface DecisionFactor {
  metric: string;
  value: any;
  impact: string;
}

export interface DecisionResponse {
  type: string;
  recommendation: string;
  confidence: string;
  summary: string;
  factors: DecisionFactor[];
}

export interface AlertFactor {
  metric: string;
  value: any;
  threshold: string;
}

export interface WeatherAlert {
  id: string;
  severity: 'warning' | 'watch' | 'advisory' | string;
  category: string;
  title: string;
  summary: string;
  factors: AlertFactor[];
}

export interface ComparisonMetricDifference {
  metric: string;
  value_a: string;
  value_b: string;
  better_location: string;
  impact_note: string;
}

export interface ComparisonDecision {
  recommended_location: string;
  recommended_key: string;
  confidence: string;
  summary: string;
  winner_reason: string;
  factors: ComparisonMetricDifference[];
}

export interface ComparisonResponse {
  location_a: GeocodedLocationSchema;
  location_b: GeocodedLocationSchema;
  target_period: string;
  period_weather_a: TargetPeriodWeather;
  period_weather_b: TargetPeriodWeather;
  decision: ComparisonDecision;
  alerts_a: WeatherAlert[];
  alerts_b: WeatherAlert[];
  comparison_goal: string;
}

export interface EnvironmentalPressureItem {
  type: string;
  level: string;
  evidence_type: string;
}

export interface EventOccurrence {
  year: number;
  start_date: string;
  end_date: string;
  post_event_days: number;
}

export interface EnvironmentalEvent {
  id: string;
  title: string;
  category: string;
  geographic_scope: string[];
  occurrences: EventOccurrence[];
  environmental_pressures: EnvironmentalPressureItem[];
  advisory_summary: string;
  key_recommendations: string[];
  source_metadata: string;
  status?: 'upcoming' | 'active' | 'post_event' | 'expired' | string;
  days_until?: number;
}

export interface QueryResponse {
  query: ExtractedQueryInfo;
  location?: GeocodedLocationSchema | null;
  current?: CurrentWeather | null;
  period_weather?: TargetPeriodWeather | null;
  period_forecast?: HourlyForecast[] | null;
  forecast?: HourlyForecast[] | null;
  decision?: DecisionResponse | null;
  alerts?: WeatherAlert[] | null;
  environmental_events?: EnvironmentalEvent[] | null;
  comparison?: ComparisonResponse | null;
  summary: string;
  official_advisories?: import('./advisory').OfficialAdvisory[] | null;
  needs_clarification?: boolean;
  language?: 'en' | 'hi' | 'bn' | string;
  session_id?: string | null;
  timestamp: string;
}


export interface PresetLocation {
  name: string;
  country: string;
  latitude: number;
  longitude: number;
}

export * from './advisory';



/**
 * Official Environmental & Hazard Advisory Types for StormOps.
 * Corresponds to backend Pydantic schemas in app/schemas/advisory.py.
 */

export type AdvisorySeverity = 'red' | 'orange' | 'yellow' | 'green' | 'unknown';

export interface OfficialAdvisory {
  id: string;
  source_id: string;
  authority: string; // 'IMD' | 'NDMA' | 'CWC' | 'INCOIS' | 'CPCB' | string
  source_url?: string | null;
  hazard_type: string;
  severity: AdvisorySeverity | string;
  official_level?: string | null;
  urgency?: string | null;
  certainty?: string | null;
  issued_at: string;
  effective_at: string;
  expires_at: string;
  is_active: boolean;
  granularity: string; // 'nowcast' | 'district' | 'subdivision' | 'state' | 'national'
  state?: string | null;
  district?: string | null;
  subdivision?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  radius_km?: number | null;
  polygon_geojson?: string | null;
  headline: string;
  description: string;
  action_guidance?: string | null;
  raw_payload?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AdvisoryListResponse {
  total: number;
  advisories: OfficialAdvisory[];
  district?: string | null;
  state?: string | null;
  timestamp: string;
}

export interface AdvisoryQueryParams {
  district?: string;
  state?: string;
  subdivision?: string;
  latitude?: number;
  longitude?: number;
  authority?: string;
  hazard_type?: string;
  severity?: string;
  include_expired?: boolean;
}

export type AdvisoryTemporalState = 'ACTIVE' | 'UPCOMING' | 'EXPIRED';

/**
 * Determine the temporal state of an advisory based strictly on authoritative temporal fields:
 * - ACTIVE: effective_at <= now < expires_at
 * - UPCOMING: effective_at > now
 * - EXPIRED: expires_at <= now
 *
 * Does NOT assume is_active === false implies UPCOMING.
 */
export function getAdvisoryTemporalState(
  adv: { effective_at: string; expires_at: string; is_active?: boolean },
  referenceDate: Date = new Date()
): AdvisoryTemporalState {
  const effective = new Date(adv.effective_at);
  const expires = new Date(adv.expires_at);
  const nowMs = referenceDate.getTime();

  if (isNaN(effective.getTime()) || isNaN(expires.getTime())) {
    return adv.is_active ? 'ACTIVE' : 'EXPIRED';
  }

  // EXPIRED: expires_at <= now
  if (expires.getTime() <= nowMs) {
    return 'EXPIRED';
  }

  // UPCOMING: effective_at > now
  if (effective.getTime() > nowMs) {
    return 'UPCOMING';
  }

  // ACTIVE: effective_at <= now < expires_at
  return 'ACTIVE';
}


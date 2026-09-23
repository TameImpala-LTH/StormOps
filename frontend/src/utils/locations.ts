import { PresetLocation } from '../types/weather';

export const PRESET_LOCATIONS: PresetLocation[] = [
  { name: 'Kolkata', country: 'India', latitude: 22.5726, longitude: 88.3639 },
  { name: 'Darjeeling', country: 'India', latitude: 27.0410, longitude: 88.2663 },
  { name: 'Koramangala', country: 'India', latitude: 12.9352, longitude: 77.6245 },
  { name: 'Cherrapunji', country: 'India', latitude: 25.2744, longitude: 91.7323 },
  { name: 'Munnar', country: 'India', latitude: 10.0889, longitude: 77.0595 },
  { name: 'Leh', country: 'India', latitude: 34.1526, longitude: 77.5771 },
];

export const findLocationByName = (query: string): PresetLocation | undefined => {
  const normalized = query.trim().toLowerCase();
  return PRESET_LOCATIONS.find(
    (loc) =>
      loc.name.toLowerCase() === normalized ||
      loc.name.toLowerCase().includes(normalized) ||
      `${loc.name}, ${loc.country}`.toLowerCase().includes(normalized)
  );
};

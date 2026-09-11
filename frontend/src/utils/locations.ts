import { PresetLocation } from '../types/weather';

export const PRESET_LOCATIONS: PresetLocation[] = [
  { name: 'Kolkata', country: 'India', latitude: 22.5726, longitude: 88.3639 },
  { name: 'Delhi', country: 'India', latitude: 28.6139, longitude: 77.2090 },
  { name: 'Mumbai', country: 'India', latitude: 19.0760, longitude: 72.8777 },
  { name: 'Kerala', country: 'India', latitude: 10.3529, longitude: 76.5120 },
  { name: 'Goa', country: 'India', latitude: 15.3005, longitude: 74.0855 },
  { name: 'Rajasthan', country: 'India', latitude: 27.0238, longitude: 74.2179 },
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

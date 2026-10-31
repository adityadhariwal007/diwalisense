import type { Comparison, LocationChoice } from './ComparisonPage';
const url = import.meta.env?.VITE_SUPABASE_URL;
const key = import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY;
export const cloudEnabled = Boolean(url && key);
type Area = LocationChoice & { station_id: string; comparison_snapshots: { complete: boolean }[] };
async function read<T>(query: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${url}/rest/v1/${query}`, { headers: { apikey: key }, signal });
  if (!response.ok) throw new Error('Air data is unavailable. Please try again.');
  return response.json() as Promise<T>;
}
export function distanceKm(latitude: number, longitude: number, area: LocationChoice) {
  const radians = (degrees: number) => degrees * Math.PI / 180;
  const a = Math.sin(radians(area.latitude - latitude) / 2) ** 2 + Math.cos(radians(latitude)) * Math.cos(radians(area.latitude)) * Math.sin(radians(area.longitude - longitude) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, a))));
}
export async function cloudData(path: string, signal: AbortSignal, body?: unknown): Promise<unknown> {
  const areas = await read<Area[]>('air_locations?select=*,comparison_snapshots!inner(complete)&comparison_snapshots.year=eq.2025&order=name', signal);
  if (path === '/locations') return areas.map(({ name, latitude, longitude }) => ({ name, latitude, longitude }));
  if (path !== '/comparison') throw new Error('Unknown air data request.');
  const { latitude, longitude } = body as LocationChoice;
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) throw new Error('Choose a valid location.');
  // GPS coordinates stay in the browser; only a public source ID is sent to Supabase.
  const nearby = areas.map(area => ({ ...area, distance: distanceKm(latitude, longitude, area) })).filter(area => area.distance <= 35).sort((a, b) => a.distance - b.distance);
  const area = nearby.find(item => item.comparison_snapshots.some(snapshot => snapshot.complete)) ?? nearby[0];
  if (!area) throw new Error('We only have Delhi data. Choose a Delhi area or try the Delhi demo.');
  const snapshots = await read<{ phases: Comparison['phases'] }[]>(`comparison_snapshots?select=phases&station_id=eq.${encodeURIComponent(area.station_id)}&year=eq.2025&limit=1`, signal);
  if (!snapshots[0]) throw new Error('Air data is not ready for this area. Try a nearby area.');
  return { area: area.name, distance_km: area.distance, phases: snapshots[0].phases, details: {} } satisfies Comparison;
}

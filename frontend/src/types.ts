// These types are the JSON contract with the backend.
// Keep src/mocks/*.json in sync with them and share both with your backend teammate.

export type LatLng = { lat: number; lng: number };

export type FloodStatus = 'clear' | 'flooding_nearby' | 'no_safe_route';

export type Destination = {
  id: string;
  name: string;
  subtitle: string;
  location: LatLng;
  distanceKm: number;
  floodStatus: FloodStatus;
};

export type Maneuver = 'straight' | 'left' | 'right' | 'arrive';

export type RouteStep = {
  instruction: string;
  distanceM: number;
  maneuver: Maneuver;
};

export type Route = {
  destinationId: string;
  path: LatLng[];
  steps: RouteStep[];
  etaMinutes: number;
  distanceKm: number;
};

export type FloodZone = {
  id: string;
  label: string;
  polygon: LatLng[];
};

export type FloodAlert = {
  id: string;
  title: string;
  detail: string;
  severity: 'warning' | 'watch';
};

// App-wide UI state
export type Tab = 'home' | 'map' | 'ollie';
export type CallState = 'none' | 'ollie' | 'emergency';
export type VoiceState = 'idle' | 'listening' | 'thinking' | 'speaking';

/** Compass bearing between two points, in degrees (0 = north). */
export function bearing(a: LatLng, b: LatLng): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const dLng = toRad(b.lng - a.lng);
  const y = Math.sin(dLng) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

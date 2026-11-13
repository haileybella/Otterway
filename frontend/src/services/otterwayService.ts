import type { Destination, FloodAlert, FloodZone, Route } from '../types';
import destinations from '../mocks/destinations.json';
import routes from '../mocks/routes.json';
import floodZones from '../mocks/flood_zones.json';
import alerts from '../mocks/alerts.json';

/**
 * Everything the UI needs from the backend.
 * Screens only talk to this interface, so connecting the real API means
 * writing one new object that implements it. No component changes.
 */
export interface OtterwayService {
  search(query: string): Promise<Destination[]>;
  route(to: Destination): Promise<Route | null>;
  floodZones(): Promise<FloodZone[]>;
  alerts(): Promise<FloodAlert[]>;
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Reads the JSON files in src/mocks. */
export const mockService: OtterwayService = {
  async search(query) {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return (destinations as Destination[]).filter((d) => d.name.toLowerCase().includes(q));
  },

  async route(to) {
    await wait(600); // simulate network so the loading state is visible
    if (to.floodStatus === 'no_safe_route') return null;
    return (routes as Route[]).find((r) => r.destinationId === to.id) ?? null;
  },

  async floodZones() {
    return floodZones as FloodZone[];
  },

  async alerts() {
    return alerts as FloodAlert[];
  },
};

// Later:
// export const apiService: OtterwayService = {
//   async search(q) { const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}`); return res.json(); },
//   ...
// };

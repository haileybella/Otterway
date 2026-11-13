import { useEffect, useMemo, useState, type ReactNode } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, Polygon, Polyline, TileLayer, useMap } from 'react-leaflet';
import { Flag, LocateFixed, Phone, Search } from 'lucide-react';
import { useAppState } from '../state/appStateContext';
import { CallBar } from '../components/CallBar';
import { TripCard, TurnBanner } from '../components/TripComponents';
import { PillButton } from '../components/PillButton';
import { otterMarkerIcon } from '../components/otterMarker';
import { bearing, type LatLng } from '../types';
import { city } from '../config/city';
import './MapScreen.css';

const DEFAULT_CENTER: [number, number] = [29.4245, -98.4915]; // San Antonio (mock data area)
const toLatLng = (p: LatLng): [number, number] => [p.lat, p.lng];

const destinationIcon = L.divIcon({
  className: 'dest-pin',
  iconSize: [40, 50],
  iconAnchor: [20, 49],
  html: `<svg width="40" height="50" viewBox="0 0 40 50"><path d="M20 49C20 49 38 32 38 19A18 18 0 002 19C2 32 20 49 20 49Z" fill="#16587B"/><circle cx="20" cy="19" r="7" fill="#F5EEDD"/></svg>`,
});

const floodLabelIcon = (label: string) =>
  L.divIcon({ className: 'flood-label', iconSize: undefined, html: `<span>≈ ${label}</span>` });

export function MapScreen() {
  const app = useAppState();
  const { route, destination, floodZones, call } = app;
  const [recenterKey, setRecenterKey] = useState(0);

  const heading = useMemo(() => (route && route.path.length >= 2 ? bearing(route.path[0], route.path[1]) : 0), [route]);

  return (
    <main className="screen map-screen">
      <MapContainer center={DEFAULT_CENTER} zoom={15} zoomControl={false} className="map-screen__map">
        {/* OpenStreetMap tiles are fine for development. For production, use a tile provider (MapTiler, Stadia, etc.). */}
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          maxZoom={19}
        />

        {floodZones.map((zone) => (
          <Polygon
            key={zone.id}
            positions={zone.polygon.map(toLatLng)}
            pathOptions={{
              color: '#2E9BD6',
              weight: 2,
              opacity: 0.6,
              dashArray: '6 6',
              fillColor: '#2E9BD6',
              fillOpacity: 0.22,
            }}
          />
        ))}
        {floodZones.map((zone) => (
          <Marker
            key={`${zone.id}-label`}
            position={centroid(zone.polygon)}
            icon={floodLabelIcon(zone.label)}
            interactive={false}
          />
        ))}

        {route && (
          <>
            <Polyline
              positions={route.path.map(toLatLng)}
              pathOptions={{ color: '#16587B', opacity: 0.15, weight: 16, lineCap: 'round', lineJoin: 'round' }}
            />
            <Polyline
              positions={route.path.map(toLatLng)}
              pathOptions={{ color: '#2E9BD6', weight: 8, lineCap: 'round', lineJoin: 'round' }}
            />
            <Marker position={toLatLng(route.path[0])} icon={otterMarkerIcon(heading)} zIndexOffset={1000} />
          </>
        )}

        {destination && (
          <Marker position={toLatLng(destination.location)} icon={destinationIcon} title={destination.name} />
        )}

        <FitToTrip recenterKey={recenterKey} />
      </MapContainer>

      {/* Top: live call + next turn */}
      <div className="map-screen__top">
        {call !== 'none' && (
          <CallBar
            call={call}
            startedAt={app.callStartedAt}
            isMuted={app.isMuted}
            onOpen={() => app.setCallScreenOpen(true)}
            onToggleMute={app.toggleMute}
            onEnd={app.endCall}
          />
        )}
        {route?.steps[0] && <TurnBanner step={route.steps[0]} />}
      </div>

      <button className="map-screen__recenter" onClick={() => setRecenterKey((k) => k + 1)} aria-label="Recenter map">
        <LocateFixed />
      </button>

      {city.has311 && (
        <button className="map-screen__report" onClick={() => app.setReportOpen(true)}>
          <Flag aria-hidden /> Report to 311
        </button>
      )}

      {/* Bottom card changes with trip state */}
      <div className="map-screen__bottom">
        {import.meta.env.DEV && <DebugMenu />}
        {route && destination ? (
          <TripCard
            route={route}
            destination={destination}
            call={call}
            onEndRoute={app.endRoute}
            onTalkToOllie={() => app.startOllieCall()}
            onSwitchTo911={app.switchToEmergency}
            onBackToOllie={app.returnToOllie}
          />
        ) : app.isLoadingRoute ? (
          <InfoCard title="Finding the safest route…" message="Checking flood alerts and avoiding flooded roads.">
            <span className="spinner" aria-label="Loading" />
          </InfoCard>
        ) : destination ? (
          <InfoCard
            title="No safe route right now"
            message="Every road there is flooded. Try another destination or call 911."
          >
            <div className="row">
              <PillButton variant="secondary" onClick={() => app.setSearchOpen(true)}>
                Change
              </PillButton>
              <PillButton variant="danger" icon={<Phone />} onClick={app.switchToEmergency}>
                Call 911
              </PillButton>
            </div>
          </InfoCard>
        ) : (
          <InfoCard title="Where to?" message="Choose a destination and Ollie will route you around flooding.">
            <PillButton icon={<Search />} onClick={() => app.setSearchOpen(true)}>
              Search
            </PillButton>
          </InfoCard>
        )}
      </div>
    </main>
  );
}

/** Fits the map to the route + flood zones whenever the route changes or Recenter is tapped. */
function FitToTrip({ recenterKey }: { recenterKey: number }) {
  const map = useMap();
  const { route, destination, floodZones } = useAppState();

  useEffect(() => {
    const points: [number, number][] = [
      ...(route?.path.map(toLatLng) ?? []),
      ...(destination ? [toLatLng(destination.location)] : []),
      ...floodZones.flatMap((z) => z.polygon.map(toLatLng)),
    ];
    if (points.length < 2) return;
    // Leave room for the top banners and bottom card.
    map.fitBounds(L.latLngBounds(points), { paddingTopLeft: [24, 200], paddingBottomRight: [24, 300], maxZoom: 16 });
  }, [map, route, destination, floodZones, recenterKey]);

  return null;
}

function InfoCard({ title, message, children }: { title: string; message: string; children: ReactNode }) {
  return (
    <div className="card info-card">
      <h2 className="display">{title}</h2>
      <p>{message}</p>
      {children}
    </div>
  );
}

/** Dev-only: flip call states without dialing anything. */
function DebugMenu() {
  const { debugSetCall } = useAppState();
  return (
    <div className="debug-menu" aria-hidden>
      <span>Debug</span>
      <button onClick={() => debugSetCall('none')}>No call</button>
      <button onClick={() => debugSetCall('ollie')}>Ollie</button>
      <button onClick={() => debugSetCall('emergency')}>911 (no dial)</button>
    </div>
  );
}

function centroid(points: LatLng[]): [number, number] {
  const lat = points.reduce((s, p) => s + p.lat, 0) / points.length;
  const lng = points.reduce((s, p) => s + p.lng, 0) / points.length;
  return [lat, lng];
}

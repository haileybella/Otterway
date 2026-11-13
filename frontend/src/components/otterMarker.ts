import L from 'leaflet';
import './OtterMarker.css';

/**
 * The user's moving location on the map: Ollie's face with a cone showing
 * direction of travel (Figma: "Map marker / You (Ollie)").
 * `heading` is in degrees (0 = north). Feed it live values from
 * DeviceOrientation / Geolocation `heading` later.
 */
export function otterMarkerIcon(heading = 0): L.DivIcon {
  return L.divIcon({
    className: 'otter-marker',
    iconSize: [72, 72],
    iconAnchor: [36, 36],
    html: `
      <span class="otter-marker__halo"></span>
      <span class="otter-marker__heading" style="transform: rotate(${heading}deg)"><i></i></span>
      <span class="otter-marker__disc"><img src="/otter-face.png" alt="Your location" /></span>
    `,
  });
}

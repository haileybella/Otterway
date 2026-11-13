# Otterway (web app)

Flood-aware navigation with **Ollie**, a voice guide, and a one-swipe handoff to 911.
It's a mobile-first web app (PWA), so it runs on Android, iPhone and desktop. Users can "Add to Home Screen" to get an app icon.
It runs on mock data, so you can build the whole UI before the backend exists.

**Stack:** React + TypeScript + Vite · Leaflet + OpenStreetMap · vite-plugin-pwa · lucide icons · Fraunces (headings)

## Run it in VS Code

1. Install **Node.js 20 or newer** (nodejs.org), then open this folder in VS Code.
2. Accept the recommended extensions when VS Code prompts: Prettier, plus Oxc for linting.
3. In VS Code's terminal (View → Terminal):
   ```bash
   npm install
   npm run dev
   ```
4. Open the link it prints (http://localhost:5173).
   - On desktop, the app shows as a phone-width column.
   - For a closer look, open Chrome DevTools → Toggle device toolbar → pick an iPhone or Pixel.

### Try it on your phone
```bash
npm run dev:phone
```
This serves the app over HTTPS on your Wi-Fi.
1. On your phone (same Wi-Fi network), open the **Network** URL it prints.
2. Accept the "not secure" warning. It's a local development certificate.

HTTPS matters because phones only allow location and microphone access on secure pages.

## Walk through the flow
1. **Home:** tap **Where do you need to go?** and type `oak`.
2. Pick **1420 Oak St** (Route clear). The map shows the flood zone, the route, your otter marker and the trip card.
3. Tap **Talk to Ollie** to open the full-screen call. This also asks the phone agent to ring your phone (see "Call with Ollie from the app" in the root README); if `agent.py` isn't running, the screen shows "Call didn’t start". In dev, tap the orb to cycle Idle → Listening → Thinking → Speaking.
4. Tap **Map**. The call stays live in the call bar at the top.
5. Tap **Switch to 911**, or use **Slide to call 911** on the call screen.
6. Search again and pick **Oak Hills Center** to see the "No safe route" state.
7. Tap **Report to 311** on the map (or **Report 311** during a call) for non-emergency problems. The sheet keeps a **Someone in danger? Call 911** button at the bottom.
8. The **Debug** pill above the trip card (dev only) switches call states instantly.

### 911 and 311 safety
`src/services/emergencyDialer.ts` is the **only** place that places calls (911 and 311).

311 settings (number, hours, online portal) live in `src/config/city.ts`, one entry per city. The 311 option is always secondary: it never stands between the user and 911.
- In development (`npm run dev`) it **never dials**. It only logs a warning in the browser console.
- Production builds open `tel:911`, and the phone shows its own confirmation before calling.
- If you test a production build on a real phone, cancel at that confirmation.

## Project structure
```
src/
  types.ts            Data types: the JSON contract with the backend
  mocks/              Mock JSON (destinations, routes, flood_zones, alerts)
  config/city.ts      311 number, hours and online portal per city
  services/           OtterwayService interface + mock version; dialer (911/311)
  state/AppState.tsx  Single source of truth: tab, call (none/ollie/emergency), voice, trip
  hooks/              useElapsed (call timers)
  styles/             Design tokens from Figma + global styles
  components/         TabBar, CallBar, otter map marker, VoiceOrb, TripCard, TurnBanner, SlideToCall, PillButton
  screens/            Home, SetDestination, Map, Call (Ollie + Ollie tab), EmergencyCall, Report (311)
public/               Otter images and app icons
```

**How it fits together**
- Every screen reads `useAppState()`, so the call bar, trip card and call screens can't disagree about what's happening.
- To connect the real backend, implement `OtterwayService` (see the comment at the bottom of `otterwayService.ts`) and pass it to `<AppStateProvider service={...}>`. No screens change.
- Share `src/types.ts` and `src/mocks/` with your backend teammate. They're the contract.

## Commit it page by page (you push)
`commit-by-page.sh` creates one commit per part of the app, under **your** Git name and email. It never pushes. Run it on a fresh folder (no earlier commits); if you already committed an older version, just commit the 311 changes on top: `git add -A && git commit -m "Add 311 reporting"`.
```bash
bash commit-by-page.sh          # all commits, then push once yourself
STEP=1 bash commit-by-page.sh   # pause after each commit so you can push each page
```
On Windows, run it from **Git Bash** (comes with Git for Windows), not PowerShell.

The commits, in order:
1. Project setup
2. Shared components
3. Set destination screen
4. Home screen
5. Map screen
6. Call with Ollie screen
7. Emergency call screen
8. Report to 311 sheet
9. Wiring the screens together

The app is fully runnable from the last commit.

First push: `git remote add origin https://github.com/<you>/<repo>.git`, then `git push -u origin main`.

## Next steps
1. **Live location:** use `navigator.geolocation.watchPosition` for the otter marker's position and heading instead of the route start.
2. **Remaining Figma screens:** Permissions, Finding a safe route (full version), Offline, No safe route sheet.
3. **Offline:** cache the last route, flood zones and alerts in `localStorage` or IndexedDB. The service worker already caches the app and recently viewed map tiles.
4. **Map tiles for production:** the OpenStreetMap tile server is for light use only. Switch to a provider (MapTiler, Stadia Maps, etc.) before launch.
5. **Deploy:** `npm run build` outputs `dist/`. Vercel or Netlify can host it for free from your GitHub repo.

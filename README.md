# Otterway
Dell Social AI Impact Datathon


## Otterway backend

The CSV is an index of historical images. Each row describes an image, and its coordinates may be the center of an aerial footprint. The backend converts those rows into GeoJSON pins. Historical observations carry no live road-closure status.

## Start locally

From the Otterway folder, run `python3 server.py` with Python 3.9 or newer. By default it reads the CSV and images from the sibling GB10competition folder. Set `OTTERWAY_CSV` and `OTTERWAY_IMAGES` to override those paths. Restart after adding images or changing the CSV.

| Endpoint | What it gives you |
|---|---|
| `GET /api/health` | Server status and whether a key is configured |
| `GET /api/observations` | Map pins as a GeoJSON FeatureCollection |
| `GET /api/images/{image_id}` | An image if the corresponding file exists locally |
| `GET /api/reverse?lat=29.4241&lon=-98.4936` | An approximate nearby address or place label |
| `POST /api/route` | Driving route geometry and turn steps |

## Connect the mapping APIs

[Sign up with HeiGIT](https://account.heigit.org/) and copy the full Standard API key from your dashboard. Enter it privately in your terminal using the default macOS shell, zsh.

```zsh
read -rs 'HEIGIT_API_KEY?Paste your HeiGIT key and press Return: '
export HEIGIT_API_KEY
python3 server.py
```

Then try these in a second terminal.

```sh
curl 'http://127.0.0.1:8000/api/reverse?lat=29.4241&lon=-98.4936'
curl http://127.0.0.1:8000/api/route -H 'Content-Type: application/json' \
  -d '{"origin":{"lat":29.4241,"lon":-98.4936},"destination":{"lat":29.4407,"lon":-98.4803}}'
```

Routes and map geometry use GeoJSON order `[longitude, latitude]`. The app sends named `lat` and `lon` fields so the backend can put them in the right order. The route's `properties.segments[].steps` contain instructions the frontend can speak. The frontend owns device GPS and decides when to advance or request a new route. Live flood closure data and avoidance would be a separate integration.

The basemap is separate. For a small interactive demo, a map library can display OpenStreetMap tiles under the [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/) with visible attribution. The directions and address services come from [HeiGIT](https://api.heigit.org/). The API key stays in the backend terminal. For a separate local frontend origin, set `OTTERWAY_FRONTEND_ORIGIN` to its exact origin, for example `http://localhost:5173`.

## Add the photos

Find the image's row by `image_id`. Check `source_url`, `source_download_url`, `reuse`, and `attribution`. Start with one before/after pair and follow the source's download and reuse terms. Save each image using the filename from the row's `image_path` under the configured images folder. The backend accepts both the CSV's relative directory layout and a flat folder with the same filenames. Restart and look for an `image_url` on the pin. A missing photo has a null URL and the pin still displays if coordinates exist. Rows without coordinates have null geometry. For example, the local AF001 photo is available at /api/images/AF001 but has no map position in the CSV.

## In-app route and voice

Start the backend with your HeiGIT key, then open [the local map](http://127.0.0.1:8000/map.html). Select **Use my location**, enter a destination, and select **Get directions**. **Start voice guidance** reads the current maneuver using the browser voice and advances as accurate location updates approach the next maneuver. **Next step** lets you step through a route during a stationary demo. The prototype uses proximity to maneuvers and has no automatic off-route recalculation. The browser must allow location access.

To add verified active closures, set `OTTERWAY_CLOSURES` to the path of a GeoJSON FeatureCollection. Each feature needs a Polygon geometry with closed rings in longitude, latitude order and a `properties.source` identifying the closure report. An optional `properties.label` appears on the map. Keep the file current by removing reopened roads. The server reads it for each route request and sends the polygons as areas to avoid. A route can be unavailable if a closure blocks access to an endpoint.

Historical observations appear as brown points. The closure polygons are red. Use official closure reports to choose polygons. CSV points often represent aerial image centers and do not establish current closures.

## Call with Ollie from the app

**Talk to Ollie** (and **Start talking** on the Ollie tab) asks `agent.py` to ring your phone, so the conversation with Ollie happens on a real phone call. Run these three on the same machine, each in its own terminal.

1. `python agent.py`, with `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER` and `MY_PHONE` set in that terminal. `MY_PHONE` is the phone that rings, and on a Twilio trial it must be a verified number.
2. `ngrok http 5000`, so Twilio can reach `agent.py`. The address it prints must match `BASE_URL` in `agent.py`.
3. `npm run dev` in `frontend/`.

The app sends `POST /agent/call` to its own address, and the Vite dev server forwards that to `agent.py` on port 5000 (see `proxy` in `frontend/vite.config.ts`). `agent.py` refuses the same request when it arrives through the ngrok tunnel, so only the app on this machine can make the phone ring, and it ignores a second request within 20 seconds. If the call can't be started, the call screen says so and offers **Try again**. `call.py` still places the same call from a terminal.

## Flood visualization

The map refreshes the flood layer from the CSV every 30 seconds. By default it uses the workshop metadata CSV. Set `OTTERWAY_FLOOD_CSV` to point to a different detection CSV. The layer reads `latitude`, `longitude`, and `flood_visible` (true, yes, or 1 for a confirmed observation). If `flood_visible` is blank, `candidate_condition` can mark a point as `flood_candidate` or `visible_inundation_candidate`. Optional `locality` and `acquisition_date` appear in the popup.

When a flood row supplies valid `west`, `south`, `east`, and `north` bounds, the map shades its image footprint. A footprint shows the area covered by the source image. Current road closures use the separate verified closure input.

"""Local Otterway API. Run with Python 3, no packages required."""
import csv
import gzip
import json
import math
import mimetypes
import os
import shlex
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

WORKSHOP = Path(__file__).resolve().parent.parent / "GB10competition"
CSV_PATH = Path(os.getenv("OTTERWAY_CSV", str(WORKSHOP / "image_metadata(in).csv")))
IMAGE_ROOT = Path(os.getenv("OTTERWAY_IMAGES", str(WORKSHOP / "FloodImages"))).resolve()
API_ROOT = "https://api.heigit.org"


def coordinates(lat, lon):
    if isinstance(lat, bool) or isinstance(lon, bool):
        raise ValueError("Expected latitude and longitude as numbers.")
    lat, lon = float(lat), float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordinates are out of range.")
    return [lon, lat]


def load_observations():
    features, images = [], {}
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            image_id = row["image_id"]
            relative_path = Path(row["image_path"])
            for candidate in (relative_path, Path(relative_path.name)):
                path = (IMAGE_ROOT / candidate).resolve()
                if path.is_relative_to(IMAGE_ROOT) and path.suffix.lower() in {
                    ".png", ".jpg", ".jpeg", ".webp"
                } and path.is_file():
                    images[image_id] = path
                    break
            properties = {key: row[key] for key in (
                "image_id", "pair_id", "paired_image_id", "image_role", "event_name",
                "acquisition_date", "locality", "location_precision", "source_url",
                "attribution", "reuse", "annotation_status", "flood_visible",
            )}
            properties["fema_sfha"] = {"T": True, "F": False}.get(
                (row.get("fema_sfha_tf") or "").strip().upper()
            )
            subtype = row.get("fema_zone_subtypes") or ""
            if "FLOODWAY" in subtype:
                properties["hazard_band"] = "floodway"
            elif properties["fema_sfha"]:
                properties["hazard_band"] = "special"
            elif "0.2 PCT ANNUAL CHANCE FLOOD HAZARD" in subtype:
                properties["hazard_band"] = "moderate"
            try:
                west, south = coordinates(row.get("south"), row.get("west"))
                east, north = coordinates(row.get("north"), row.get("east"))
                if west < east and south < north:
                    properties["footprint_bounds"] = [[south, west], [north, east]]
            except (TypeError, ValueError):
                pass
            properties["kind"] = "historical_image"
            properties["image_url"] = "/api/images/" + quote(image_id, safe="") if image_id in images else None
            try:
                point = coordinates(row["latitude"], row["longitude"])
                geometry = {"type": "Point", "coordinates": point}
            except (ValueError, TypeError):
                geometry = None
            features.append({
                "type": "Feature", "geometry": geometry,
                "properties": properties,
            })
    return {"type": "FeatureCollection", "features": features}, images


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def load_flood_layer():
    path = Path(os.getenv("OTTERWAY_FLOOD_CSV", str(CSV_PATH)))
    features = []
    seen = set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            fields = set(reader.fieldnames or ())
            if not {"latitude", "longitude"} <= fields or not fields.intersection(
                {"flood_visible", "candidate_condition"}
            ):
                raise ValueError("Expected latitude, longitude and flood labels.")
            for row in reader:
                visible = (row.get("flood_visible") or "").strip().lower()
                candidate = (row.get("candidate_condition") or "").strip().lower()
                if visible in {"true", "yes", "1"}:
                    status = "confirmed"
                elif not visible and candidate in {"flood_candidate", "visible_inundation_candidate"}:
                    status = "candidate"
                else:
                    continue
                properties = {
                    "status": status,
                    "locality": row.get("locality") or "",
                    "date": row.get("acquisition_date") or "",
                }
                geometries = []
                try:
                    point = coordinates(row["latitude"], row["longitude"])
                    geometries.append(("Point", point))
                except (TypeError, ValueError):
                    pass
                try:
                    west, south = coordinates(row.get("south"), row.get("west"))
                    east, north = coordinates(row.get("north"), row.get("east"))
                    if west < east and south < north:
                        ring = [[west, south], [east, south], [east, north],
                                [west, north], [west, south]]
                        geometries.append(("Polygon", [ring]))
                except (TypeError, ValueError):
                    pass
                for kind, shape in geometries:
                    key = (status, kind, json.dumps(shape))
                    if key in seen:
                        continue
                    seen.add(key)
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": kind, "coordinates": shape},
                        "properties": properties,
                    })
    except (OSError, ValueError, csv.Error) as error:
        raise ApiError(503, "Could not read the flood CSV. Check OTTERWAY_FLOOD_CSV.") from error
    return {"type": "FeatureCollection", "features": features}


def heigit(path, payload=None):
    key = os.getenv("HEIGIT_API_KEY", "").strip()
    if not key:
        raise ApiError(503, "Set HEIGIT_API_KEY to enable routes and address lookup.")
    headers = {"Authorization": key, "Accept": "application/geo+json" if path.endswith("/geojson") else "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    request = Request(API_ROOT + path, data=data, headers=headers)
    try:
        with urlopen(request, timeout=12) as response:
            return json.load(response)
    except HTTPError as error:
        messages = {
            401: "HeiGIT rejected the API key.", 403: "HeiGIT denied access. Check your API key and plan.",
            404: "HeiGIT could not find a result.", 429: "HeiGIT quota reached. Try again later.",
        }
        status = error.code if error.code in (404, 429) else 502
        raise ApiError(status, messages.get(error.code, f"HeiGIT returned HTTP {error.code}.")) from error
    except (URLError, TimeoutError, ValueError) as error:
        raise ApiError(502, "Could not read a response from HeiGIT.") from error



def load_closures():
    """Read the operator's current, verified closure polygons."""
    path = os.getenv("OTTERWAY_CLOSURES")
    if not path:
        return {"type": "FeatureCollection", "features": []}
    try:
        data = json.loads(Path(path).read_text())
        if data["type"] != "FeatureCollection":
            raise ValueError("Expected a FeatureCollection.")
        for feature in data["features"]:
            geometry = feature["geometry"]
            properties = feature["properties"]
            if geometry["type"] != "Polygon" or not properties["source"]:
                raise ValueError("Each closure needs a Polygon and a source.")
            if not geometry["coordinates"]:
                raise ValueError("Expected polygon rings.")
            for ring in geometry["coordinates"]:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("Expected a closed polygon ring.")
                for lon, lat in ring:
                    coordinates(lat, lon)
        return data
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ApiError(503, "Could not load closure polygons. Check OTTERWAY_CLOSURES.") from error

def flood_avoidance_polygons(features):
    """Use CSV footprints and a roughly 50 m buffer around flood points."""
    polygons = []
    for feature in features:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            polygons.append(geometry["coordinates"])
        else:
            lon, lat = geometry["coordinates"]
            dy = 50 / 111_320
            dx = dy / max(0.001, math.cos(math.radians(lat)))
            west, east = max(-180, lon - dx), min(180, lon + dx)
            south, north = max(-90, lat - dy), min(90, lat + dy)
            polygons.append([[[west, south], [east, south], [east, north],
                              [west, north], [west, south]]])
    return polygons


def route_crosses_polygon(line, polygon):
    def orientation(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def intersects(a, b, c, d):
        return (
            max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
            and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1]))
            and orientation(a, b, c) * orientation(a, b, d) <= 0
            and orientation(c, d, a) * orientation(c, d, b) <= 0
        )

    x, y = line[0]
    inside = False
    for ring in polygon:
        for c, d in zip(ring, ring[1:]):
            if (c[1] > y) != (d[1] > y):
                if x < c[0] + (y - c[1]) * (d[0] - c[0]) / (d[1] - c[1]):
                    inside = not inside
            if any(intersects(a, b, c, d) for a, b in zip(line, line[1:])):
                return True
    return inside


def route_avoiding_floods(points, closures):
    polygons = [feature["geometry"]["coordinates"] for feature in closures["features"]]
    polygons.extend(flood_avoidance_polygons(load_flood_layer()["features"]))
    request = {"coordinates": points, "instructions": True, "instructions_format": "text"}
    exclusions = set()
    for _ in range(4):
        try:
            result = heigit("/openrouteservice/v2/directions/driving-car/geojson", request)
        except ApiError as error:
            if exclusions and error.status == 404:
                break
            raise
        features = result.get("features", [])
        if not features:
            break
        line = features[0]["geometry"]["coordinates"]
        crossings = {index for index, polygon in enumerate(polygons)
                     if route_crosses_polygon(line, polygon)}
        if not crossings:
            result["otterway_closures"] = closures
            result["otterway_detour"] = bool(exclusions)
            return result
        if crossings <= exclusions:
            break
        exclusions.update(crossings)
        request["options"] = {"avoid_polygons": {
            "type": "MultiPolygon", "coordinates": [polygons[index] for index in sorted(exclusions)]
        }}
    raise ApiError(422, "No route found that avoids mapped flood observations and closures. "
                       "Try a different starting point or destination.")


def fetch_flood_tile(path):
    try:
        z, x, y = map(int, path.removeprefix("/api/flood-tiles/").removesuffix(".mvt").split("/"))
        if not (0 <= z <= 19 and 0 <= x < 2**z and 0 <= y < 2**z):
            raise ValueError
    except ValueError as error:
        raise ApiError(400, "Invalid flood tile coordinates.") from error

    key = os.getenv("NATIONAL_FLOOD_DATA_API_KEY", "").strip()
    if not key:
        raise ApiError(503, "National Flood Data key is missing.")
    request = Request(
        f"https://api.nationalflooddata.com/v3/tiles/flood-vector/{z}/{x}/{y}.mvt",
        headers={"X-API-KEY": key},
    )
    try:
        with urlopen(request, timeout=8) as response:
            body = response.read()
            return gzip.decompress(body) if response.headers.get("Content-Encoding") == "gzip" else body
    except HTTPError as error:
        if error.code in (401, 403):
            raise ApiError(403, "National Flood Data denied tile access. Check the key and tile permissions.") from error
        raise ApiError(502, f"National Flood Data returned HTTP {error.code}.") from error
    except (URLError, OSError, EOFError) as error:
        raise ApiError(502, "National Flood Data tile service is unavailable.") from error


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        # Keep GPS query strings out of access logs.
        pass

    def send_body(self, status, body, content_type):
        self.send_response(status)
        origin = os.getenv("OTTERWAY_FRONTEND_ORIGIN")
        if origin and origin == self.headers.get("Origin"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def reply(self, status, data):
        self.send_body(status, json.dumps(data).encode(), "application/json")

    def do_OPTIONS(self):
        self.send_body(204, b"", "text/plain")

    def do_GET(self):
        url = urlsplit(self.path)
        try:
            if url.path in ("/", "/map.html"):
                page = Path(__file__).with_name("map.html")
                if not page.is_file():
                    raise ApiError(404, "Map page is unavailable.")
                self.send_body(200, page.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/search":
                query = parse_qs(url.query).get("q", [""])[0].strip()
                if not 2 <= len(query) <= 200:
                    raise ApiError(400, "Enter a place name or address.")
                params = urlencode({"text": query, "size": 1})
                result = heigit("/pelias/v1/search?" + params)
                matches = result.get("features", [])
                if not matches:
                    raise ApiError(404, "No destination found. Try adding the city or ZIP code.")
                match = matches[0]
                lon, lat = match["geometry"]["coordinates"]
                self.reply(200, {"lat": lat, "lon": lon, "label": match["properties"]["label"]})
            elif url.path == "/api/health":
                self.reply(200, {"status": "ok", "routing_configured": bool(os.getenv("HEIGIT_API_KEY", "").strip())})
            elif url.path == "/api/closures":
                self.reply(200, load_closures())
            elif url.path.startswith("/api/flood-tiles/"):
                tile = fetch_flood_tile(url.path)
                self.send_body(200, tile, "application/vnd.mapbox-vector-tile")
            elif url.path == "/api/floods":
                self.reply(200, load_flood_layer())
            elif url.path == "/api/observations":
                self.reply(200, self.server.observations)
            elif url.path.startswith("/api/images/"):
                image = self.server.images.get(unquote(url.path.removeprefix("/api/images/")))
                if image is None or not image.is_file():
                    raise ApiError(404, "Image is unavailable.")
                self.send_body(200, image.read_bytes(), mimetypes.guess_type(image.name)[0])
            elif url.path == "/api/reverse":
                query = parse_qs(url.query)
                lon, lat = coordinates(query["lat"][0], query["lon"][0])
                params = urlencode({"point.lat": lat, "point.lon": lon, "size": 1})
                result = heigit("/pelias/v1/reverse?" + params)
                matches = result.get("features", [])
                label = matches[0]["properties"].get("label") if matches else None
                self.reply(200, {"label": label, "approximate": True, "source": "HeiGIT/Pelias"})
            else:
                raise ApiError(404, "Unknown endpoint.")
        except (KeyError, TypeError, ValueError):
            self.reply(400, {"error": "Provide valid lat and lon query parameters."})
        except ApiError as error:
            self.reply(error.status, {"error": str(error)})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/route":
            self.reply(404, {"error": "Unknown endpoint."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError("Invalid request body size.")
            payload = json.loads(self.rfile.read(length))
            points = [coordinates(payload[name]["lat"], payload[name]["lon"])
                      for name in ("origin", "destination")]
            self.reply(200, route_avoiding_floods(points, load_closures()))
        except (KeyError, TypeError, ValueError):
            self.reply(400, {"error": "Provide origin and destination objects with lat and lon."})
        except ApiError as error:
            self.reply(error.status, {"error": str(error)})


def load_local_key(variable, filename):
    """Read the Desktop key file used by the local setup instructions."""
    if os.getenv(variable, "").strip():
        return

    key_file = Path.home() / "Desktop" / filename
    if not key_file.is_file():
        return

    for line in key_file.read_text(encoding="utf-8-sig").splitlines():
        if line.lstrip().startswith((f"export {variable}=", f"{variable}=")):
            try:
                assignment = shlex.split(line, comments=True)[-1]
            except (ValueError, IndexError):
                raise SystemExit(f"Check the {variable} line in Desktop/{filename}.")
            key = assignment.partition("=")[2].strip()
            if key and key != "PASTE_YOUR_KEY_HERE":
                os.environ[variable] = key
            return


if __name__ == "__main__":
    load_local_key("HEIGIT_API_KEY", "otterway.env")
    load_local_key("NATIONAL_FLOOD_DATA_API_KEY", "otterway-flood.env")
    observations, images = load_observations()
    with ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler) as server:
        server.observations = observations
        server.images = images
        print(f"Otterway http://127.0.0.1:{server.server_port} | "
              f"{len(observations['features'])} observations, {len(images)} local images", flush=True)
        server.serve_forever()

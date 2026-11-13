"""Local Otterway API. Run with Python 3, no packages required."""
import csv
import json
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
            closures = load_closures()
            request = {"coordinates": points, "instructions": True, "instructions_format": "text"}
            polygons = [feature["geometry"]["coordinates"] for feature in closures["features"]]
            if polygons:
                request["options"] = {
                    "avoid_polygons": {"type": "MultiPolygon", "coordinates": polygons}
                }
            result = heigit("/openrouteservice/v2/directions/driving-car/geojson", request)
            result["otterway_closures"] = closures
            self.reply(200, result)
        except (KeyError, TypeError, ValueError):
            self.reply(400, {"error": "Provide origin and destination objects with lat and lon."})
        except ApiError as error:
            self.reply(error.status, {"error": str(error)})


def load_local_key():
    """Read the Desktop key file used by the local setup instructions."""
    if os.getenv("HEIGIT_API_KEY", "").strip():
        return

    key_file = Path.home() / "Desktop" / "otterway.env"
    if not key_file.is_file():
        return

    for line in key_file.read_text(encoding="utf-8-sig").splitlines():
        if line.lstrip().startswith(("export HEIGIT_API_KEY=", "HEIGIT_API_KEY=")):
            try:
                assignment = shlex.split(line, comments=True)[-1]
            except (ValueError, IndexError):
                raise SystemExit("Check the HEIGIT_API_KEY line in Desktop/otterway.env.")
            key = assignment.partition("=")[2].strip()
            if key and key != "PASTE_YOUR_KEY_HERE":
                os.environ["HEIGIT_API_KEY"] = key
            return


if __name__ == "__main__":
    load_local_key()
    observations, images = load_observations()
    with ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler) as server:
        server.observations = observations
        server.images = images
        print(f"Otterway http://127.0.0.1:{server.server_port} | "
              f"{len(observations['features'])} observations, {len(images)} local images", flush=True)
        server.serve_forever()

"""Local Otterway API. Run with Python 3, no packages required."""
import csv
import json
import mimetypes
import os
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
    headers = {"Authorization": key, "Accept": "application/json"}
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
            if url.path == "/api/health":
                self.reply(200, {"status": "ok", "routing_configured": bool(os.getenv("HEIGIT_API_KEY", "").strip())})
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
            result = heigit("/openrouteservice/v2/directions/driving-car/geojson",
                            {"coordinates": points, "instructions": True})
            self.reply(200, result)
        except (KeyError, TypeError, ValueError):
            self.reply(400, {"error": "Provide origin and destination objects with lat and lon."})
        except ApiError as error:
            self.reply(error.status, {"error": str(error)})


if __name__ == "__main__":
    observations, images = load_observations()
    with ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PORT", "8000"))), Handler) as server:
        server.observations = observations
        server.images = images
        print(f"Otterway http://127.0.0.1:{server.server_port} | "
              f"{len(observations['features'])} observations, {len(images)} local images", flush=True)
        server.serve_forever()

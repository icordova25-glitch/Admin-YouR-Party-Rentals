import base64
import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"; UPLOADS_DIR = ROOT / "uploads" / "gallery"
AUTH_PATH = DATA_DIR / "admin-auth.json"; CATALOG_PATH = DATA_DIR / "catalog.json"; GALLERY_PATH = DATA_DIR / "gallery.json"; SETTINGS_PATH = DATA_DIR / "business-settings.json"; AVAILABILITY_PATH = DATA_DIR / "dropoff-availability.json"; BOOKINGS_PATH = DATA_DIR / "bookings.json"
USERNAME = os.getenv("GALLERY_ADMIN_USERNAME", "admin"); PASSWORD = os.getenv("GALLERY_ADMIN_PASSWORD", "yourr-admin"); CORS_ORIGIN = os.getenv("CORS_ALLOWED_ORIGIN", "*")
DEFAULT_CATALOG = {"items": [{"key": "tables", "name": "Tables", "description": "Rectangular and round event tables for dining and display.", "price": 10, "inventory": 100}, {"key": "chairs", "name": "Chairs", "description": "Comfortable, stackable seating for indoor and outdoor events.", "price": 2, "inventory": 250}, {"key": "canopies", "name": "Canopies", "description": "Shade coverage for backyard celebrations and open spaces.", "price": 75, "inventory": 20}, {"key": "fans", "name": "Fans", "description": "Portable cooling fans to keep guests comfortable all day.", "price": 20, "inventory": 30}, {"key": "iceChests", "name": "Ice Chests", "description": "Large-capacity coolers for drinks, food storage, and service.", "price": 15, "inventory": 40}], "packages": [{"id": "summer-special", "name": "Summer Special", "description": "4 Tables, 24 Chairs, one 10x20 Canopy, plus your choice of one add-on: Ice Chest, Fan, or Speaker.", "price": 169, "items": {"tables": 4, "chairs": 24, "canopies": 1, "fans": 0, "iceChests": 1}}]}
STATIC = {"/": "index.html", "/index.html": "index.html", "/script.js": "script.js", "/styles.css": "styles.css", "/config.js": "config.js", "/admin-gallery.html": "admin-gallery.html", "/admin-gallery.js": "admin-gallery.js"}
def read(path, fallback):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return fallback
def write(path, value): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2), encoding="utf-8")
def init():
    DATA_DIR.mkdir(exist_ok=True); UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not AUTH_PATH.exists(): write(AUTH_PATH, {"username": USERNAME, "password": PASSWORD})
    if not CATALOG_PATH.exists(): write(CATALOG_PATH, DEFAULT_CATALOG)
    for path, value in ((GALLERY_PATH, []), (SETTINGS_PATH, {}), (AVAILABILITY_PATH, {}), (BOOKINGS_PATH, [])):
        if not path.exists(): write(path, value)
def auth(value):
    if not value or not value.startswith("Basic "): return False
    try: username, _, password = base64.b64decode(value[6:]).decode().partition(":")
    except Exception: return False
    saved = read(AUTH_PATH, {"username": USERNAME, "password": PASSWORD}); return username == saved.get("username") and password == saved.get("password")
class Handler(BaseHTTPRequestHandler):
    server_version = "YouRPartyRentals/1.0"
    def log_message(self, *_): pass
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN); self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    def json(self, status, value):
        body = json.dumps(value).encode(); self.send_response(status); self.cors(); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self): return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode() or "{}")
    def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health": return self.json(200, {"ok": True})
        if path == "/api/catalog": return self.json(200, read(CATALOG_PATH, DEFAULT_CATALOG))
        if path == "/api/gallery": return self.json(200, read(GALLERY_PATH, []))
        if path == "/api/dropoff-slots": return self.json(200, read(AVAILABILITY_PATH, {}).get(parse_qs(urlparse(self.path).query).get("date", [""])[0], ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]))
        if path.startswith("/api/admin/") and not auth(self.headers.get("Authorization")): return self.unauthorized()
        if path == "/api/admin/ping": return self.json(200, {"ok": True})
        if path == "/api/admin/auth": return self.json(200, {"username": read(AUTH_PATH, {"username": USERNAME}).get("username")})
        if path == "/api/admin/catalog": return self.json(200, read(CATALOG_PATH, DEFAULT_CATALOG))
        if path == "/api/admin/settings": return self.json(200, read(SETTINGS_PATH, {}))
        if path == "/api/admin/availability": return self.json(200, read(AVAILABILITY_PATH, {}))
        if path == "/api/admin/bookings": return self.json(200, read(BOOKINGS_PATH, []))
        if path in STATIC: return self.file(ROOT / STATIC[path])
        self.json(404, {"error": "Not found."})
    def do_POST(self):
        if urlparse(self.path).path == "/api/bookings":
            value = self.body(); value["id"] = uuid.uuid4().hex; value["receivedAt"] = datetime.now(timezone.utc).isoformat(); bookings = read(BOOKINGS_PATH, []); bookings.append(value); write(BOOKINGS_PATH, bookings); return self.json(201, value)
        self.json(404, {"error": "Not found."})
    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/admin/") or not auth(self.headers.get("Authorization")): return self.unauthorized()
        value = self.body()
        if path == "/api/admin/auth": write(AUTH_PATH, {"username": str(value.get("username", "")).strip(), "password": str(value.get("password", ""))}); return self.json(200, {"username": value.get("username")})
        target = {"/api/admin/catalog": CATALOG_PATH, "/api/admin/settings": SETTINGS_PATH, "/api/admin/availability": AVAILABILITY_PATH}.get(path)
        if target: write(target, value); return self.json(200, value)
        self.json(404, {"error": "Not found."})
    def unauthorized(self): self.json(401, {"error": "Authorization required."})
    def file(self, path):
        if not path.is_file(): return self.json(404, {"error": "Not found."})
        data = path.read_bytes(); self.send_response(200); self.cors(); self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
def main():
    init()
    port = int(os.getenv("PORT", "3002"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"YouR Party Rentals server running at http://0.0.0.0:{port}", flush=True)
    server.serve_forever()
if __name__ == "__main__": main()

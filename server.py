import base64, json, mimetypes, os, re, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(DATA_DIR / "uploads" / "gallery")))
AUTH_PATH = DATA_DIR / "admin-auth.json"
CATALOG_PATH = DATA_DIR / "catalog.json"
GALLERY_PATH = DATA_DIR / "gallery.json"
SETTINGS_PATH = DATA_DIR / "business-settings.json"
AVAILABILITY_PATH = DATA_DIR / "dropoff-availability.json"
BOOKINGS_PATH = DATA_DIR / "bookings.json"
USERNAME = os.getenv("GALLERY_ADMIN_USERNAME", "admin")
PASSWORD = os.getenv("GALLERY_ADMIN_PASSWORD", "yourr-admin")
CORS_ORIGIN = os.getenv("CORS_ALLOWED_ORIGIN", "*")
DEFAULT = {"items": [{"key": "tables", "name": "Tables", "description": "Rectangular and round event tables for dining and display.", "price": 10, "inventory": 100}, {"key": "chairs", "name": "Chairs", "description": "Comfortable, stackable seating for indoor and outdoor events.", "price": 2, "inventory": 250}, {"key": "canopies", "name": "Canopies", "description": "Shade coverage for backyard celebrations and open spaces.", "price": 75, "inventory": 20}, {"key": "fans", "name": "Fans", "description": "Portable cooling fans to keep guests comfortable all day.", "price": 20, "inventory": 30}, {"key": "iceChests", "name": "Ice Chests", "description": "Large-capacity coolers for drinks, food storage, and service.", "price": 15, "inventory": 40}], "packages": [{"id": "summer-special", "name": "Summer Special", "description": "4 Tables, 24 Chairs, one 10x20 Canopy, plus your choice of one add-on: Ice Chest, Fan, or Speaker.", "price": 169, "items": {"tables": 4, "chairs": 24, "canopies": 1, "fans": 0, "iceChests": 1}}]}
STATIC = {"/": "index.html", "/index.html": "index.html", "/script.js": "script.js", "/styles.css": "styles.css", "/config.js": "config.js", "/admin-gallery.html": "admin-gallery.html", "/admin-gallery.js": "admin-gallery.js"}

def read(path, fallback):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return fallback

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2), encoding="utf-8")

def init():
    DATA_DIR.mkdir(exist_ok=True); UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for path, value in ((AUTH_PATH, {"username": USERNAME, "password": PASSWORD}), (CATALOG_PATH, DEFAULT), (GALLERY_PATH, []), (SETTINGS_PATH, {}), (AVAILABILITY_PATH, {}), (BOOKINGS_PATH, [])):
        if not path.exists(): write(path, value)

def authorized(value):
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
    def file(self, path):
        if not path.is_file(): return self.json(404, {"error": "Not found."})
        body = path.read_bytes(); self.send_response(200); self.cors(); self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def need_auth(self):
        if authorized(self.headers.get("Authorization")): return True
        self.json(401, {"error": "Authorization required."}); return False
    def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health": return self.json(200, {"ok": True})
        if path == "/api/gallery": return self.json(200, read(GALLERY_PATH, []))
        if path == "/api/catalog": return self.json(200, read(CATALOG_PATH, DEFAULT))
        if path.startswith("/uploads/gallery/"): return self.file(UPLOADS_DIR / os.path.basename(path))
        if path.startswith("/api/admin/") and not self.need_auth(): return
        routes = {"/api/admin/ping": {"ok": True}, "/api/admin/auth": {"username": read(AUTH_PATH, {"username": USERNAME}).get("username")}, "/api/admin/catalog": read(CATALOG_PATH, DEFAULT), "/api/admin/settings": read(SETTINGS_PATH, {}), "/api/admin/availability": read(AVAILABILITY_PATH, {}), "/api/admin/bookings": read(BOOKINGS_PATH, [])}
        if path in routes: return self.json(200, routes[path])
        if path in STATIC: return self.file(ROOT / STATIC[path])
        self.json(404, {"error": "Not found."})
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/bookings":
            value = self.body(); value.update(id=uuid.uuid4().hex, receivedAt=datetime.now(timezone.utc).isoformat()); rows = read(BOOKINGS_PATH, []); rows.append(value); write(BOOKINGS_PATH, rows); return self.json(201, value)
        if path != "/api/gallery" or not self.need_auth(): return
        value = self.body(); match = re.match(r"^data:(image/[\\w.+-]+);base64,(.+)$", str(value.get("image", "")), re.DOTALL)
        if not match: return self.json(400, {"error": "A valid image data URL is required."})
        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(match.group(1))
        if not extension: return self.json(400, {"error": "Unsupported image type."})
        try: data = base64.b64decode(match.group(2))
        except Exception: return self.json(400, {"error": "Could not decode image."})
        if len(data) > 8 * 1024 * 1024: return self.json(400, {"error": "Image is too large (max 8MB)."})
        filename = uuid.uuid4().hex + extension; (UPLOADS_DIR / filename).write_bytes(data); entry = {"id": uuid.uuid4().hex, "url": "/uploads/gallery/" + filename, "caption": str(value.get("caption", ""))[:200], "createdAt": datetime.now(timezone.utc).isoformat()}; rows = read(GALLERY_PATH, []); rows.append(entry); write(GALLERY_PATH, rows); self.json(201, entry)
    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/admin/") or not self.need_auth(): return
        value = self.body()
        if path == "/api/admin/auth": write(AUTH_PATH, {"username": str(value.get("username", "")).strip(), "password": str(value.get("password", ""))}); return self.json(200, {"username": value.get("username")})
        target = {"/api/admin/catalog": CATALOG_PATH, "/api/admin/settings": SETTINGS_PATH, "/api/admin/availability": AVAILABILITY_PATH}.get(path)
        if target: write(target, value); return self.json(200, value)
        self.json(404, {"error": "Not found."})
    def do_DELETE(self):
        match = re.match(r"^/api/gallery/([\\w-]+)$", urlparse(self.path).path)
        if not match or not self.need_auth(): return
        rows = read(GALLERY_PATH, []); target = next((row for row in rows if row.get("id") == match.group(1)), None)
        if not target: return self.json(404, {"error": "Image not found."})
        write(GALLERY_PATH, [row for row in rows if row.get("id") != match.group(1)]); file_path = UPLOADS_DIR / os.path.basename(target.get("url", "")); file_path.unlink(missing_ok=True); self.json(200, {"success": True})

def main():
    init(); port = int(os.getenv("PORT", "3002")); server = ThreadingHTTPServer(("0.0.0.0", port), Handler); print(f"YouR Party Rentals server running at http://0.0.0.0:{port}", flush=True); server.serve_forever()

if __name__ == "__main__": main()

"""Hello, world: the EyeOfTheTiger test app.

Shows your EOT-1's live stream with "Hello, world." over it. If you can see
that, the whole app path works: the app was built, installed, given its
EOT-1's API key, opened with a valid token, and can reach the live stream.

Standard library only. Endpoints:
  GET /status       health check (no token needed, no secrets in it)
  GET /             the page (needs ?token=)
  GET /live-stream  the stream's WebRTC playback URL (needs ?token=)
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Set by the platform on every cloud app it runs.
API_URL = os.environ["CAMERA_API_URL"].rstrip("/")
API_KEY = os.environ["CAMERA_API_KEY"]
CAMERA_ID = os.environ["CAMERA_ID"]
APP_NAME = os.environ.get("APP_NAME", "")
# Unset when you run it locally, which turns the token check off.
EMBED_TOKEN_SECRET = os.environ.get("EMBED_TOKEN_SECRET")
# Set by Cloud Run to the port you entered when you submitted the app.
PORT = int(os.environ.get("PORT", "8080"))

PAGE = (Path(__file__).parent / "index.html").read_bytes()


def token_ok(token):
    """The portal opens the app with ?token=<payload>.<signature>, signed
    with EMBED_TOKEN_SECRET. Your app's address is public, so check it on
    every request that shows or fetches anything from the EOT-1."""
    if not EMBED_TOKEN_SECRET:
        return True
    if not token or "." not in token:
        return False
    payload_b64, _, sig = token.partition(".")
    expected = base64.urlsafe_b64encode(
        hmac.new(EMBED_TOKEN_SECRET.encode(), payload_b64.encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
    except ValueError:
        return False
    return (
        payload.get("exp", 0) > time.time() * 1000
        and payload.get("cameraId") == CAMERA_ID
        and payload.get("name") == APP_NAME
    )


def live_stream():
    """(status, body) for the EOT-1's live stream. The API key stays here on
    the server; the browser only gets the playback URL."""
    req = urllib.request.Request(
        f"{API_URL}/api/v1/cameras/{CAMERA_ID}/live-stream",
        # Name your app here: the platform's firewall blocks Python's default
        # "Python-urllib" user agent.
        headers={"x-api-key": API_KEY, "user-agent": "hello-world-app/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            url = json.load(res).get("live_stream", {}).get("webrtc_playback_url")
            return (200, {"webrtc_playback_url": url}) if url else (404, {"error": "No live stream."})
    except urllib.error.HTTPError as e:
        return (404, {"error": "No live stream."}) if e.code == 404 else (502, {"error": f"API returned {e.code}."})
    except OSError as e:
        return 502, {"error": str(e)}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        token = urllib.parse.parse_qs(url.query).get("token", [None])[0]
        if url.path == "/status":
            return self.send(200, "application/json", b'{"ok": true}')
        if url.path not in ("/", "/live-stream"):
            return self.send(404, "text/plain", b"Not found")
        if not token_ok(token):
            return self.send(401, "text/plain", b"Open this app from your EOT-1's page in the EyeOfTheTiger portal.")
        if url.path == "/":
            return self.send(200, "text/html; charset=utf-8", PAGE)
        status, body = live_stream()
        self.send(status, "application/json", json.dumps(body).encode())

    def send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        # Keeps the token out of requests to other sites (the WHEP POST).
        self.send_header("referrer-policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

"""Run with: python -m unittest test_app"""
import base64
import hashlib
import hmac
import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECRET = "test-secret"


class FakeApi(BaseHTTPRequestHandler):
    """Stands in for the platform API: one EOT-1 with a live stream."""

    def do_GET(self):
        # Like the real platform, which blocks Python's default user agent.
        live = (
            self.path == "/api/v1/cameras/eot-test/live-stream"
            and self.headers.get("x-api-key") == "key"
            and not self.headers.get("user-agent", "").startswith("Python-urllib")
        )
        body = json.dumps({"live_stream": {"webrtc_playback_url": "https://stream.example/play"}}).encode()
        self.send_response(200 if live else 404)
        self.end_headers()
        self.wfile.write(body if live else b"{}")

    def log_message(self, *args):
        pass


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


api = serve(FakeApi)
os.environ.update(
    CAMERA_API_URL=f"http://127.0.0.1:{api.server_port}",
    CAMERA_API_KEY="key",
    CAMERA_ID="eot-test",
    APP_NAME="hello-world",
    EMBED_TOKEN_SECRET=SECRET,
)
import app  # noqa: E402  (reads the environment above at import)

app.Handler.log_message = lambda *args: None
server = serve(app.Handler)


def mint(camera="eot-test", name="hello-world", exp_ms=None, secret=SECRET):
    """Same format as the gateway's mintEmbedToken."""
    payload = json.dumps({"cameraId": camera, "name": name, "exp": exp_ms or (time.time() + 60) * 1000})
    p = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), p.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{p}.{sig}"


def get(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}") as res:
            return res.status, res.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class TokenTest(unittest.TestCase):
    def test_accepts_a_valid_token(self):
        self.assertTrue(app.token_ok(mint()))

    def test_rejects_bad_tokens(self):
        for bad in [None, "", "nodot", mint(secret="other"), mint(camera="eot-other"), mint(name="other-app"),
                    mint(exp_ms=(time.time() - 1) * 1000), mint()[:-2] + "xx"]:
            self.assertFalse(app.token_ok(bad), bad)


class HttpTest(unittest.TestCase):
    def test_status_needs_no_token(self):
        self.assertEqual(get("/status")[0], 200)

    def test_page_and_stream_need_a_token(self):
        self.assertEqual(get("/")[0], 401)
        self.assertEqual(get("/live-stream")[0], 401)

    def test_page_shows_hello_world(self):
        status, body = get(f"/?token={mint()}")
        self.assertEqual(status, 200)
        self.assertIn(b"Hello, world.", body)

    def test_live_stream_returns_only_the_playback_url(self):
        status, body = get(f"/live-stream?token={mint()}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"webrtc_playback_url": "https://stream.example/play"})


if __name__ == "__main__":
    unittest.main()

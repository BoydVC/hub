#!/usr/bin/env python3
"""TokenMax Hub server (stdlib, default port 4646). Read-only view over /workspace/tokenmax."""
import http.server
import json
import mimetypes
import os
import socketserver
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan  # noqa: E402

PORT = int(os.environ.get("HUB_PORT", "4646"))
SERVABLE = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".html", ".md"}


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(HERE, "web"), **k)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/health":
            return self._send(json.dumps({"ok": True, "app": "tokenmax-hub"}).encode(), "application/json")
        if u.path == "/api/hub":
            return self._send(json.dumps(scan.hub_data(do_ping=True)).encode(), "application/json")
        if u.path.startswith("/p/"):
            # /p/<project>/<relpath>: serve screenshots, snapshots, READMEs from sibling project folders (read-only)
            rel = urllib.parse.unquote(u.path[3:])
            full = os.path.realpath(os.path.join(scan.ROOT, rel))
            if not full.startswith(os.path.realpath(scan.ROOT) + os.sep) or os.path.splitext(full)[1].lower() not in SERVABLE or not os.path.isfile(full):
                return self._send(b"not found", "text/plain", 404)
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            if full.endswith(".md"):
                ctype = "text/plain; charset=utf-8"
            with open(full, "rb") as f:
                return self._send(f.read(), ctype)
        return super().do_GET()


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"TokenMax Hub on http://127.0.0.1:{PORT}")
    S(("127.0.0.1", PORT), H).serve_forever()

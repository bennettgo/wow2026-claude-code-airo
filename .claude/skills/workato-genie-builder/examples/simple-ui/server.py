#!/usr/bin/env python3
"""
Minimal proxy + static server for a Workato Genie chat UI.

Why a proxy?
  - The browser can't put the runtime api_key in JavaScript (any user could read it).
  - The proxy holds the api_key + IDP_USER_ID server-side and forwards Bearer auth.
  - In production, the proxy lives in your backend and identity comes from your SSO.

Run:
    GENIE_ID=gin-...-CD \\
    GENIE_API_TOKEN=<64-char api_key> \\
    IDP_USER_ID=<from provisioner> \\
    WORKATO_DC=us \\
    python3 server.py

Then open http://localhost:8088/
"""
import http.server, os, socketserver, sys, urllib.error, urllib.request
from pathlib import Path

GENIE_ID = os.environ["GENIE_ID"]
RT_TOKEN = os.environ["GENIE_API_TOKEN"]
IDP_USER = os.environ["IDP_USER_ID"]
DC = os.environ.get("WORKATO_DC", "us")
HEADLESS_HOST = "genie-api.workato.com" if DC == "us" else f"genie-api.{DC}.workato.com"
HEADLESS = f"https://{HEADLESS_HOST}/api/v1/genies/{GENIE_ID}/chat"
PORT = int(os.environ.get("PORT", 8088))

INDEX = (Path(__file__).parent / "index.html").read_bytes()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[ui] {fmt % args}\n")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_html(INDEX)
        elif self.path.startswith("/api/"):
            self._proxy("GET")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        else:
            self.send_error(404)

    def _send_html(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method):
        url = HEADLESS + self.path[len("/api"):]
        body = None
        if method == "POST":
            n = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(n) if n else b""
        headers = {
            "Authorization": f"Bearer {RT_TOKEN}",
            "X-IDP-User-Id": IDP_USER,
            "Accept": self.headers.get("Accept", "application/json, text/event-stream"),
        }
        if body:
            headers["Content-Type"] = self.headers.get("Content-Type", "application/json")
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            up = urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            up = e
        self.send_response(up.status)
        for k, v in up.headers.items():
            if k.lower() in ("transfer-encoding", "connection", "content-length", "content-encoding"):
                continue
            self.send_header(k, v)
        self.end_headers()
        while True:
            chunk = up.read(1024)
            if not chunk:
                break
            try:
                self.wfile.write(chunk)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                break


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


with ReusableTCPServer(("", PORT), Handler) as httpd:
    print(f"▶ Workato Genie chat UI on http://localhost:{PORT}")
    print(f"  Genie:  {GENIE_ID}")
    print(f"  DC:     {DC} ({HEADLESS_HOST})")
    print(f"  As:     {IDP_USER}")
    httpd.serve_forever()

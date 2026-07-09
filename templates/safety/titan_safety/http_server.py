"""Lightweight HTTP server for safety services (stdlib only)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .auth import verify_control_auth


RouteHandler = Callable[[dict[str, Any], dict[str, str]], tuple[int, dict[str, Any]]]

# Max request body (bytes) — prevents OOM from unbounded POSTs
MAX_BODY_BYTES = 4 * 1024 * 1024


class SafetyHTTPServer:
    def __init__(
        self,
        host: str,
        port: int,
        routes: dict[str, RouteHandler],
        *,
        auth_commands: dict[str, str] | None = None,
        safety_dir: Path | None = None,
        max_body_bytes: int = MAX_BODY_BYTES,
    ) -> None:
        """Create a safety HTTP server.

        auth_commands maps route keys (e.g. "POST /v1/flatten") to the HMAC
        command name required in X-Titan-Auth. Routes not listed are open
        (typically GET /health and GET /metrics).
        """
        self.host = host
        self.port = port
        self.routes = routes
        self.auth_commands = auth_commands or {}
        self.safety_dir = safety_dir
        self.max_body_bytes = max_body_bytes
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        routes = self.routes
        auth_commands = self.auth_commands
        safety_dir = self.safety_dir
        max_body = self.max_body_bytes

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _read_body(self) -> tuple[dict[str, Any] | None, str]:
                length = int(self.headers.get("Content-Length", 0))
                if length == 0:
                    return {}, ""
                if length > max_body:
                    return None, f"body too large ({length} > {max_body})"
                raw = self.rfile.read(length)
                try:
                    return json.loads(raw.decode()), ""
                except json.JSONDecodeError:
                    return None, "invalid JSON"

            def _send(self, code: int, payload: dict[str, Any]) -> None:
                if "_raw_prometheus" in payload:
                    body = payload["_raw_prometheus"].encode()
                    self.send_response(code)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                handler = routes.get(f"GET {path}")
                if not handler:
                    self._send(404, {"error": "not found"})
                    return
                code, payload = handler({}, dict(self.headers))
                self._send(code, payload)

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                route_key = f"POST {path}"
                handler = routes.get(route_key)
                body, err = self._read_body()
                if err:
                    status = 413 if "too large" in err else 400
                    self._send(status, {"error": err, "decision": "DENY"})
                    return
                if not handler:
                    self._send(404, {"error": "not found"})
                    return
                # Control-plane auth for mutating routes
                expected_cmd = auth_commands.get(route_key)
                if expected_cmd:
                    ok, reason = verify_control_auth(
                        dict(self.headers), expected_cmd, safety_dir
                    )
                    if not ok:
                        self._send(
                            401,
                            {"error": "unauthorized", "reason": reason, "decision": "DENY"},
                        )
                        return
                assert body is not None
                code, payload = handler(body, dict(self.headers))
                self._send(code, payload)

        return Handler

    def start(self, background: bool = True) -> None:
        self._httpd = HTTPServer((self.host, self.port), self._make_handler())
        if background:
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        else:
            self._httpd.serve_forever()

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()

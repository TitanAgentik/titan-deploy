#!/usr/bin/env python3
"""Temporary OpenAI-compat bridge: :30003 -> local Ollama (:11434).

Use only when Colibrì / llama-server-glm-5.2-offload is not available on this host.
Does not start cloud models itself — proxies whatever Ollama already serves.
"""
from __future__ import annotations

import argparse
import http.client
import http.server
import socketserver
import sys


class _Proxy(http.server.BaseHTTPRequestHandler):
    upstream_host = "127.0.0.1"
    upstream_port = 11434

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        conn = http.client.HTTPConnection(self.upstream_host, self.upstream_port, timeout=600)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length"}}
        if body is not None:
            headers["Content-Length"] = str(len(body))
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            payload = resp.read()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() in {"transfer-encoding", "connection"}:
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        finally:
            conn.close()

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._proxy()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=30003)
    p.add_argument("--upstream-host", default="127.0.0.1")
    p.add_argument("--upstream-port", type=int, default=11434)
    args = p.parse_args()
    _Proxy.upstream_host = args.upstream_host
    _Proxy.upstream_port = args.upstream_port
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((args.host, args.port), _Proxy) as httpd:
        print(f"[glm30003-bridge] listening http://{args.host}:{args.port}/v1 -> {args.upstream_host}:{args.upstream_port}", flush=True)
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

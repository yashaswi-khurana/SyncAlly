"""Expose only the Slack Events endpoint to a local development tunnel.

Run with ``python -m syncally.cli.slack_tunnel_proxy`` while the API is running.
The listener binds to loopback and forwards only Slack's signed event request
to the API. This keeps the rest of the development API off the public tunnel.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8001
API_EVENTS_URL = "http://127.0.0.1:8000/integrations/slack/events"
EVENTS_PATH = "/integrations/slack/events"
MAX_BODY_BYTES = 256 * 1024
FORWARDED_HEADERS = (
    "content-type",
    "x-slack-request-timestamp",
    "x-slack-signature",
)


class SlackEventsProxyHandler(BaseHTTPRequestHandler):
    server_version = "SyncAllySlackTunnelProxy/1.0"

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != EVENTS_PATH:
            self.send_error(404)
            return

        raw_length = self.headers.get("Content-Length")
        try:
            content_length = int(raw_length or "")
        except ValueError:
            self.send_error(411, "Content-Length is required")
            return
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            self.send_error(413, "Slack event body is too large")
            return

        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self.send_error(400, "Incomplete request body")
            return

        headers = {
            name: self.headers[name]
            for name in FORWARDED_HEADERS
            if self.headers.get(name) is not None
        }
        request = Request(API_EVENTS_URL, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=10) as response:
                payload = response.read(MAX_BODY_BYTES + 1)
                status = response.status
                content_type = response.headers.get("Content-Type", "application/json")
        except HTTPError as error:
            payload = error.read(MAX_BODY_BYTES + 1)
            status = error.code
            content_type = error.headers.get("Content-Type", "application/json")
        except (TimeoutError, URLError):
            self.send_error(502, "Local Slack Events API is unavailable")
            return

        if len(payload) > MAX_BODY_BYTES:
            self.send_error(502, "Local API response is too large")
            return
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self.send_error(404)

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        # Avoid logging request bodies, Slack signatures, or customer data.
        print(f"{self.log_date_time_string()} {self.address_string()} {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), SlackEventsProxyHandler)
    print(
        f"Slack Events tunnel proxy listening on http://{LISTEN_HOST}:{LISTEN_PORT}"
    )
    print(f"Forwarding only POST {EVENTS_PATH} to the local API.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Slack Events tunnel proxy.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

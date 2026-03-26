import os
import mimetypes
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

_WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
_SPLASH_TEMPLATE = os.path.join(_WORKSPACE_ROOT, "whateels", "assets", "html", "splash.html")

def _build_html(target_port: int) -> str:
    with open(_SPLASH_TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    return template.replace("{{TARGET_PORT}}", str(target_port))

def _make_handler(html: str):
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Serve static files (SVGs, etc.) requested by the browser after the HTML loads.
            if self.path not in ("/", ""):
                abs_path = os.path.join(_WORKSPACE_ROOT, self.path.lstrip("/"))
                if os.path.isfile(abs_path):
                    mime, _ = mimetypes.guess_type(abs_path)
                    with open(abs_path, "rb") as f:
                        body = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", mime or "application/octet-stream")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_error(404)
                return
            # Root path → splash HTML
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):  # type: ignore
            """ Override to disable logging every request to the console. Uncomment the line below to enable logging if needed. """
            pass

    return _Handler


def start(target_port: int, splash_port: int) -> None:
    """Start the splash HTTP server on *splash_port* and open the browser."""
    html = _build_html(target_port)
    handler = _make_handler(html)

    server = HTTPServer(("localhost", splash_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    webbrowser.open(f"http://localhost:{splash_port}/")

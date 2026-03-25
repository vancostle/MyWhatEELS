
import os
import mimetypes
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from whateels import App

_WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))

APP_NAME = "WhatEELS"
PORT = 5006
SPLASH_PORT = 5007

# ---------------------------------------------------------------------------
# Minimal splash page served while Panel is starting up.
# The JavaScript polls the Panel server every 500 ms; once it responds the
# page redirects automatically.  fetch() with mode:'no-cors' resolves as an
# opaque response when the server is reachable, and throws TypeError when it
# is not — making it a reliable "is the server up?" probe with no CORS issues.
# ---------------------------------------------------------------------------
_SPLASH_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Starting {APP_NAME}…</title>
  <style>
    :root {{
        --fill-color: #f7f7f7;
    }}
    *, *::before, *::after {{
        box-sizing: border-box; 
        margin: 0; padding: 0; 
    }}
    body {{
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      height: 100vh;
      font-family: system-ui, sans-serif;
      background: var(--fill-color);
    }}
    div.wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2rem;
        & h1 {{
            font-size: 1.6rem;
            color: #1b1b1b;
        }}
    }}
    .bouncing-dots {{
        display: flex;
        justify-content: center;
        align-items: flex-end;
        height: 32px;
        margin-top: 0.5rem;
        gap: 0.5rem;
    }}
    .dot {{
        width: 12px;
        height: 12px;
        background: #1b1b1b;
        border-radius: 50%;
        display: inline-block;
        animation: bounce 0.8s infinite;
    }}
    .images {{
        display: grid;
        place-items: center;
        position: relative;
        height: 300px;

        & img {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);

            &:last-of-type {{
                animation: rotate 10s ease-in-out infinite;
            }}
        }}
    }}
    .dot:nth-child(2) {{ animation-delay: 0.15s; }}
    .dot:nth-child(3) {{ animation-delay: 0.3s; }}

    footer {{
        position: absolute;
        bottom: 10px;
        font-size: 0.9rem;
        color: var(--fill-color);
    }}

    @keyframes bounce {{
        0%, 80%, 100% {{ transform: translateY(0); }}
        40% {{ transform: translateY(-16px); }}
    }}

    @keyframes rotate {{
        0% {{ transform: translate(-50%, -50%) rotate(0deg); }}
        100% {{ transform: translate(-50%, -50%) rotate(360deg); }}
    }}
    
  </style>
</head>
<body>
    <div class="wrapper">
        <div class="images">
            <img src="whateels/assets/img/w.svg" alt="WhatEELS W Logo" width="165" />
            <img src="whateels/assets/img/eel.svg" alt="WhatEELS Eel Logo" width="300" />
        </div>
        <div class="bouncing-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    </div>
    <footer>
        <address>
            Andry Alexis Reyes Cruz
        </address>
    </footer>
  <script>
    const TARGET = 'http://localhost:{PORT}/';
    let attempt = 0;
    async function probe() {{
      try {{
        await fetch(TARGET, {{ mode: 'no-cors' }});
        window.location.replace(TARGET);
      }} catch (_) {{
        setTimeout(probe, 200);
      }}
    }}
    probe();
  </script>
</body>
</html>
"""

class _SplashHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Serve static files (e.g. SVGs) — the browser requests these separately
        # after loading the HTML. Without this, every request gets back the HTML.
        if self.path != "/" and self.path != "":
            rel_path = self.path.lstrip("/")
            abs_path = os.path.join(_WORKSPACE_ROOT, rel_path)
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
        # Serve the splash HTML for the root path
        body = _SPLASH_HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):  # silence access logs
        pass

if __name__ == "__main__":
    # 1. Start the instant splash server on a secondary port.
    splash_server = HTTPServer(("localhost", SPLASH_PORT), _SplashHandler)
    splash_thread = threading.Thread(target=splash_server.serve_forever, daemon=True)
    splash_thread.start()

    # 2. Open the browser to the splash page straight away (no black screen).
    webbrowser.open(f"http://localhost:{SPLASH_PORT}/")

    # 3. Start the real Panel app (blocking call — runs until Ctrl+C).
    #    show=False because the browser is already open.
    app = App(title=APP_NAME)
    app.run(port=PORT, show=False)

from whateels import App
import threading
import time
import webview

APP_NAME = "WhatEELS"
PORT = 5006

if __name__ == "__main__":
    # Start Panel server in a background thread
    t = threading.Thread(
        target=lambda: App(title=APP_NAME).run(port=PORT, show=False),
        daemon=True
    )
    t.start()
    # Wait for server to start (adjust if needed)
    time.sleep(2)
    # Open PyWebView window to localhost
    webview.create_window(
        APP_NAME, 
        f'http://localhost:{PORT}',
    )
    webview.start()
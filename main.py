
import splash
from whateels import App

APP_NAME = "WhatEELS"
PORT = 5006
SPLASH_PORT = 5007

if __name__ == "__main__":
    # 1. Start the splash server and open the browser instantly.
    splash.start(APP_NAME, PORT, SPLASH_PORT)

    # 2. Start the real Panel app (blocking — runs until Ctrl+C).
    app = App(title=APP_NAME)
    app.run(port=PORT, show=False)
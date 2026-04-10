
import os
import sys
import traceback

import splash
from whateels import App

APP_NAME = "WhatEELS"
PORT = 5006
SPLASH_PORT = 5007

if __name__ == "__main__":
    try:
        # 1. Start the splash server and open the browser instantly.
        splash.start(PORT, SPLASH_PORT)

        # 2. Start the real Panel app (blocking - runs until Ctrl+C).
        app = App(title=APP_NAME)
        app.run(port=PORT, show=False)
    except Exception:
        print("\n[WhatEELS] Startup error:\n")
        traceback.print_exc()
        # Keep console open in frozen Windows executable so errors are readable.
        if getattr(sys, "frozen", False) and os.name == "nt":
            try:
                input("\nPress Enter to close...")
            except EOFError:
                pass
        raise
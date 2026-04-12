
import multiprocessing

# MUST be called before any other imports or code.
# Without this, ProcessPoolExecutor (used by multifitting) spawns worker copies
# of the frozen exe that re-run the full entry point — opening new Panel app
# instances and splash screens for each worker process.
multiprocessing.freeze_support()

import os
import sys
import traceback

APP_NAME = "WhatEELS"
PORT = 5006
SPLASH_PORT = 5007

if __name__ == "__main__":
    try:
        # splash has only lightweight stdlib imports, so it loads instantly.
        import splash

        # 1. Open the browser with the splash screen BEFORE any heavy import.
        #    The user sees the animation immediately while Panel/HoloViews load.
        splash.start(PORT, SPLASH_PORT)

        # 2. Heavy imports happen here, hidden behind the splash.
        from whateels import App

        # 3. Start the real Panel app (blocking - runs until Ctrl+C).
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
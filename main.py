
import multiprocessing

# MUST be called before any other imports or code.
# Without this, ProcessPoolExecutor (used by multifitting) spawns worker copies
# of the frozen exe that re-run the full entry point — opening new Panel app
# instances and splash screens for each worker process.
multiprocessing.freeze_support()

import sys

# On Windows, Python defaults to ProactorEventLoop (IOCP-based). Tornado's
# WebSocket handling works best with SelectorEventLoop — ProactorEventLoop
# adds measurable latency per small message, which is felt as sluggish hover
# in the frozen exe. Set this before any asyncio/tornado/panel import.
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import traceback

APP_NAME = "WhatEELS"
PORT = 5006
SPLASH_PORT = 5007

if __name__ == "__main__":
    try:
        # Print ASCII art banner on startup
        print(art.text2art(APP_NAME))

        # Display a bold, red-background message to keep the window open
        init(autoreset=True)
        msg = "Please keep this window open while WhatEELS is running."
        print(Back.RED + Style.BRIGHT + Fore.WHITE + f"  {msg}  ".center(80))

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
        raise

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
    # Enable ANSI/VT escape-code processing in the Windows console
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )

import traceback, logging

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_ANSI_RED_BG_BOLD_WHITE = "\033[41;1;97m"
_ANSI_RESET             = "\033[0m"

_BANNER = r"""
                __        ___           _   _____ _______      ____
                \ \      / / |__   __ _| |_| ____|  ___| |    / ___|
                 \ \ /\ / /| '_ \ / _` | __|  _| |  _| | |    \__ \
                  \ V  V / | | | | (_| | |_| |___| |___| |___ ___) |
                   \_/\_/  |_| |_|\__,_|\__|_____|_____|_____|____/

"""

# Suppress verbose Tornado/Bokeh access logs — writing to a Win32 console window
# is slower than a Unix terminal, and per-request logging adds overhead in the exe.
logging.getLogger('tornado.access').setLevel(logging.ERROR)
logging.getLogger('tornado.application').setLevel(logging.WARNING)
logging.getLogger('bokeh').setLevel(logging.WARNING)
logging.getLogger('markdown_it').setLevel(logging.WARNING)

APP_NAME = "WhatEELS"
PORT = 5006
SPLASH_PORT = 5007

if __name__ == "__main__":
    try:
        # Print ASCII art banner on startup
        print(_BANNER)

        # Display a bold, red-background message to keep the window open
        msg = "Please keep this window open while WhatEELS is running."
        print(f"{_ANSI_RED_BG_BOLD_WHITE}               {msg}                 {_ANSI_RESET}".center(80))
        print("\n")

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
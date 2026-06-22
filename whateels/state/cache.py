"""
Cache management for AppState instances.

Uses Panel's server-wide cache (pn.state.cache) to persist AppState across
page navigations. Each navigation creates a new Panel session, so AppState
must live outside the session to survive across pages.

AppState is intentionally persistent and never automatically deleted because:
- Page navigations create new sessions; tying cleanup to session end would
  delete state the user still needs when returning to a page.
- Data held by AppState (numpy arrays, xarray datasets) is freed explicitly
  when the user removes a file (AppState.clear_all()).
"""

import panel as pn
from .app_state import AppState

class CacheManager:

    _KEY = "app_state"

    @staticmethod
    def get_cached_app_state() -> "AppState":
        """Get the persistent AppState, creating it on first call.

        Returns:
            AppState: Single shared instance that survives page navigations.
        """
        if CacheManager._KEY not in pn.state.cache:  # type: ignore
            pn.state.cache[CacheManager._KEY] = AppState()  # type: ignore
        return pn.state.cache[CacheManager._KEY]  # type: ignore



"""
Cache management for AppState instances.

Handles user-scoped caching with fallback to global cache when no auth is configured.
Designed to scale to multi-user with minimal changes when authentication is added.
"""

import panel as pn
from .app_state import AppState

class CacheManager:
    """Manages caching of AppState instances, scoped to authenticated users when available.
    
    AppState is intentionally persistent — one instance per user, shared across all
    pages and browser tabs. It is never automatically deleted from cache because:
    - There is always at most one AppState per user (no accumulation risk).
    - Page navigations create new sessions; tying cleanup to session end would
      delete state the user still needs when returning to a page.
    - Data held by AppState (numpy arrays, xarray datasets) is freed explicitly
      when the user removes a file (AppState.clear_all()).
    """

    @staticmethod
    def _user_key(prefix: str) -> str:
        """Return a cache key scoped to the current authenticated user.

        Resolution order:
        1. ``pn.state.user`` — set automatically when Panel auth is enabled
        (OAuth2, BasicAuth, etc.).  Each user gets an isolated AppState so
        cross-tab sharing works (both tabs → same user → same key) while
        different users remain isolated.
        2. Global fallback (``"<prefix>_global"``) — used when auth is not yet
        configured (single-user / dev mode).  Replace step 2 with a real
        identity source (JWT claim, session cookie, …) when you add auth.
        """
        user = getattr(pn.state, "user", None)
        if user:
            return f"{prefix}_{user}"
        return f"{prefix}_global"

    @staticmethod
    def get_cached_app_state() -> "AppState":
        """Get the AppState scoped to the current user (or global if no auth).
        
        Returns:
            AppState: User-scoped or global AppState instance from cache.
            Persists across page navigations and browser tabs for the same user.
        """
        key = CacheManager._user_key("app_state")
        if key not in pn.state.cache:  # type: ignore
            pn.state.cache[key] = AppState()  # type: ignore
        return pn.state.cache[key]  # type: ignore



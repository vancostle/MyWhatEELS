"""
Shared state management for WhatEELS application.

Provides user-scoped, cached AppState instances for cross-component communication.
Automatically isolates state per user when authentication is enabled.
Includes automatic cleanup to prevent memory leaks when sessions end.
"""

from .cache import CacheManager
from .app_state import AppState

# Convenience aliases for direct access
get_cached_app_state = CacheManager.get_cached_app_state
_user_key = CacheManager._user_key

__all__ = ["CacheManager", "AppState", "get_cached_app_state", "_user_key"]

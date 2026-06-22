"""
Shared state management for WhatEELS application.

Provides a persistent AppState instance shared across all pages via Panel's
server-wide cache, surviving page navigations within the same session.
"""

from .cache import CacheManager
from .app_state import AppState

get_cached_app_state = CacheManager.get_cached_app_state

__all__ = ["CacheManager", "AppState", "get_cached_app_state"]

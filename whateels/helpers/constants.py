"""
Project-wide constants and paths for the WhatEELS application.

This module provides centralized access to common paths and constants
used throughout the application, avoiding circular imports and providing
a single source of truth for project configuration.
"""

from pathlib import Path

# Project root path - points to the whateels package directory
PROJECT_ROOT = Path(__file__).parent.parent

# Common asset paths
ASSETS_ROOT = PROJECT_ROOT / "assets"
CSS_ROOT = ASSETS_ROOT / "css"
HTML_ROOT = ASSETS_ROOT / "html"
JS_ROOT = ASSETS_ROOT / "js"
OOS_ROOT = ASSETS_ROOT / "oos"

#!/usr/bin/env python3
"""
Constants module for NFT Generator
Centralized location for all constants used throughout the application.
"""

from typing import Final


# Cache settings
DEFAULT_IMAGE_CACHE_SIZE: Final[int] = 128

# File paths
OUTPUT_DIR: Final[str] = "output"
IMAGE_DIR: Final[str] = "image"
METADATA_DIR: Final[str] = "metadata"

# Generation settings
DEFAULT_MAX_ATTEMPTS: Final[int] = 1000
DEFAULT_MAX_TRAIT_ATTEMPTS: Final[int] = 100

# Animation settings
DEFAULT_GIF_DURATION_MS: Final[int] = 120
DEFAULT_GIF_LOOP: Final[int] = 0

# Resume functionality
SEEN_HASHES_FILE: Final[str] = "seen_hashes.json"
TRACKER_STATE_FILE: Final[str] = "tracker_state.json"
RNG_STATE_FILE: Final[str] = "rng_state.json"

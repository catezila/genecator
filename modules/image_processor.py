#!/usr/bin/env python3
"""
Image processor module for NFT Generator
Handles image loading, caching, and composition with enhanced error handling.
"""

import logging
import time
from collections import OrderedDict
from pathlib import Path
from PIL import Image
from typing import Dict, List, Tuple, Optional, Union

from modules.constants import (
    DEFAULT_IMAGE_CACHE_SIZE,
    DEFAULT_GIF_DURATION_MS,
    DEFAULT_GIF_LOOP,
)


class ImageProcessor:
    """Handles image loading, caching, and composition with memory-aware LRU cache optimization."""

    def __init__(self, cache_size: int = DEFAULT_IMAGE_CACHE_SIZE, max_memory_mb: int = 512):
        """
        Initialize image processor with memory-aware LRU cache.

        Args:
            cache_size: Maximum number of images to cache (default: 128)
            max_memory_mb: Maximum memory usage in MB for cached images (default: 512MB)
        """
        self.cache_size = cache_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_bytes = 0
        self._image_cache = OrderedDict()  # (path, image, size_bytes, access_time)
        self._cache_hits = 0
        self._cache_misses = 0

    def load_image_cached(self, path: Union[str, Path]) -> Image.Image:
        """
        Load image with memory-aware LRU caching for better performance.

        Args:
            path: Path to the image file

        Returns:
            PIL.Image: Loaded image

        Raises:
            Exception: If there's an error loading the image
        """
        # Sanitize path to prevent path traversal
        safe_path = str(self._sanitize_path(path))

        # Check cache first
        if safe_path in self._image_cache:
            # Update access time and move to end to mark as recently used
            cache_entry = self._image_cache[safe_path]
            cache_entry['access_time'] = time.time()
            self._image_cache.move_to_end(safe_path)
            self._cache_hits += 1
            return cache_entry['image']

        # Load image if not in cache
        try:
            with Image.open(safe_path) as im:
                image = im.convert("RGBA").copy()

            # Calculate approximate memory usage (RGBA: 4 bytes per pixel)
            image_memory_bytes = image.size[0] * image.size[1] * 4

            # Make space if needed
            self._ensure_cache_space(image_memory_bytes)

            # Add to cache with metadata
            cache_entry = {
                'image': image,
                'size_bytes': image_memory_bytes,
                'access_time': time.time()
            }
            self._image_cache[safe_path] = cache_entry
            self.current_memory_bytes += image_memory_bytes
            self._cache_misses += 1

            logging.debug(f"Cache stats - Hits: {self._cache_hits}, Misses: {self._cache_misses}, "
                         f"Memory: {self.current_memory_bytes / 1024 / 1024:.1f}MB")
            return image
        except Exception as e:
            logging.error(f"Error loading image {safe_path}: {str(e)}")
            raise

    def _ensure_cache_space(self, required_bytes: int) -> None:
        """
        Ensure there's enough space in cache for new image, evicting old entries if needed.

        Args:
            required_bytes: Memory space needed for new image
        """
        # First, evict based on count limit
        while len(self._image_cache) >= self.cache_size:
            self._evict_lru_item()

        # Then, evict based on memory limit
        while self.current_memory_bytes + required_bytes > self.max_memory_bytes and self._image_cache:
            self._evict_lru_item()

    def _evict_lru_item(self) -> None:
        """Evict the least recently used cache item."""
        if not self._image_cache:
            return

        # Find the least recently used item
        lru_path = min(self._image_cache.keys(),
                      key=lambda k: self._image_cache[k]['access_time'])

        cache_entry = self._image_cache[lru_path]
        self.current_memory_bytes -= cache_entry['size_bytes']

        del self._image_cache[lru_path]

        logging.debug(f"Evicted from cache: {lru_path} "
                     f"(freed {cache_entry['size_bytes'] / 1024:.0f}KB, "
                     f"memory now: {self.current_memory_bytes / 1024 / 1024:.1f}MB)")

    def get_cache_stats(self) -> Dict[str, float]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'cache_size': len(self._image_cache),
            'memory_usage_mb': self.current_memory_bytes / 1024 / 1024,
            'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': hit_rate,
            'memory_utilization_percent': (self.current_memory_bytes / self.max_memory_bytes * 100)
        }

    def _sanitize_path(self, path: Union[str, Path]) -> Path:
        """
        Sanitize file path to prevent path traversal vulnerabilities.

        Args:
            path: Path to sanitize

        Returns:
            Path: Sanitized path

        Raises:
            ValueError: If path is invalid
        """
        # Convert to Path object
        path_obj = Path(path)

        # Check for path traversal attempts before resolving
        if ".." in str(path_obj):
            raise ValueError(f"Invalid path: {path}")

        # Resolve to absolute path
        resolved_path = path_obj.resolve()

        return resolved_path

    def compose_static_nft(
        self,
        trait_layers: Dict[str, str],
        trait_order: List[str],
        traits: Dict[str, str],
        image_size: Tuple[int, int],
    ) -> Image.Image:
        """
        Compose a static NFT image from trait layers.

        Args:
            trait_layers: Dictionary mapping trait types to their file paths
            trait_order: List of trait types in composition order
            traits: Dictionary of selected traits
            image_size: Tuple of (width, height) for the image

        Returns:
            PIL.Image: Composed NFT image
        """
        # Create base image
        base_image = Image.new("RGBA", image_size, (255, 255, 255, 0))
        base_size = base_image.size

        # Composite trait layers in order
        for trait_type in trait_order:
            if trait_type in traits:
                layer_path = trait_layers[trait_type]
                try:
                    layer_image = self.load_image_cached(layer_path)
                    # Check if layer image size matches base image size
                    if layer_image.size != base_size:
                        raise ValueError(
                            f"Image size mismatch: expected {base_size}, got {layer_image.size} for {layer_path}"
                        )
                    base_image = Image.alpha_composite(base_image, layer_image)
                except Exception as e:
                    logging.error(f"Error loading image {layer_path}: {str(e)}")
                    raise

        return base_image

    def compose_animated_nft(
        self,
        gif_layers: List[str],
        static_layers: List[str],
        image_size: Tuple[int, int],
        gif_duration_ms: int = DEFAULT_GIF_DURATION_MS,
        gif_loop: int = DEFAULT_GIF_LOOP,
    ) -> Tuple[List[Image.Image], Optional[int], Optional[int]]:
        """
        Compose an animated NFT from GIF and static layers with optimized processing.

        Args:
            gif_layers: List of paths to animated GIF trait files
            static_layers: List of paths to static PNG trait files
            image_size: Tuple of (width, height) for the image
            gif_duration_ms: Frame duration in milliseconds
            gif_loop: Loop count (0 for infinite)

        Returns:
            tuple: (frames, duration, loop) for saving as GIF
        """
        frames = []
        frame_count = None
        dur = None
        lp = None

        # Pre-open GIF files to avoid repeated file operations
        opened_gifs = []

        try:
            # Validate GIF consistency
            for idx, layer in enumerate(gif_layers):
                # Sanitize path
                safe_layer = self._sanitize_path(layer)

                # Open GIF file once and keep reference
                gif_file = Image.open(safe_layer)
                opened_gifs.append(gif_file)

                if not getattr(gif_file, "is_animated", False):
                    raise ValueError(f"GIF trait is not animated: {layer}")
                if frame_count is None:
                    frame_count = gif_file.n_frames
                    dur = gif_file.info.get("duration", gif_duration_ms)
                    lp = gif_file.info.get("loop", gif_loop)
                else:
                    if gif_file.n_frames != frame_count:
                        raise ValueError("All GIF traits must have same frame count")
                    if gif_file.info.get("duration", gif_duration_ms) != dur:
                        raise ValueError("All GIF traits must have same frame duration")
                    if gif_file.info.get("loop", gif_loop) != lp:
                        raise ValueError("All GIF traits must have same loop count")

            # Generate frames
            for f in range(frame_count or 1):
                frame = Image.new("RGBA", image_size, (255, 255, 255, 0))
                # Composite static layers first
                for sp in static_layers:
                    li = self.load_image_cached(sp)
                    # Check if layer image size matches frame size
                    if li.size != image_size:
                        raise ValueError(
                            f"Image size mismatch: expected {image_size}, got {li.size} for {sp}"
                        )
                    frame = Image.alpha_composite(frame, li)
                # Then composite GIF frame
                for gif_file in opened_gifs:
                    gif_file.seek(f)
                    gif_frame = gif_file.convert("RGBA")
                    # Check if GIF frame size matches expected size
                    if gif_frame.size != image_size:
                        raise ValueError(
                            f"Image size mismatch: expected {image_size}, got {gif_frame.size} for animated frame"
                        )
                    frame = Image.alpha_composite(frame, gif_frame)
                frames.append(frame)

            return frames, dur, lp
        finally:
            # Ensure all opened GIF files are closed
            for gif_file in opened_gifs:
                try:
                    gif_file.close()
                except Exception as e:
                    logging.warning(f"Failed to close GIF file: {e}")

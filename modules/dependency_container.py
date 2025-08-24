#!/usr/bin/env python3
"""
Dependency injection container for NFT Generator
Provides centralized dependency management and injection.
"""

import logging
from typing import Dict, Type, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class GeneratorDependencies:
    """Container for all NFT generator dependencies."""
    config_manager: Any  # ConfigManager
    image_processor: Any  # ImageProcessor
    trait_tracker: Any    # TraitTracker
    metadata_manager: Any # MetadataManager
    resource_manager: Any # ResourceManager


class DependencyContainer:
    """Centralized dependency injection container."""

    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._instances: Dict[str, Any] = {}

    def register_singleton(self, interface: Type, implementation: Any):
        """Register a singleton instance."""
        self._singletons[interface] = implementation
        logging.debug(f"Registered singleton: {interface.__name__}")

    def register_factory(self, interface: Type, factory: Callable):
        """Register a factory function for creating instances."""
        self._factories[interface] = factory
        logging.debug(f"Registered factory: {interface.__name__}")

    def register_instance(self, name: str, instance: Any):
        """Register a named instance."""
        self._instances[name] = instance
        logging.debug(f"Registered instance: {name}")

    def get(self, interface: Type, name: Optional[str] = None) -> Any:
        """Get an instance of the requested type."""
        # Check named instances first
        if name and name in self._instances:
            return self._instances[name]

        # Check singletons
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factories
        if interface in self._factories:
            instance = self._factories[interface]()
            # Cache as singleton after first creation
            self._singletons[interface] = instance
            return instance

        raise ValueError(f"No registration found for {interface.__name__}")

    def create_generator_dependencies(self, **kwargs) -> GeneratorDependencies:
        """
        Create a complete set of dependencies for NFTGenerator.

        Args:
            **kwargs: Override default dependency creation parameters

        Returns:
            GeneratorDependencies: Complete dependency set
        """
        from modules.config_manager import ConfigManager
        from modules.image_processor import ImageProcessor
        from modules.trait_tracker import TraitTracker
        from modules.metadata_manager import MetadataManager
        from modules.resource_manager import resource_manager

        # Extract configuration parameters
        cache_size = kwargs.get('cache_size', 128)
        max_memory_mb = kwargs.get('max_memory_mb', 512)
        max_similar = kwargs.get('max_similar', 1)

        # Create dependencies
        config_manager = self.get(ConfigManager) if ConfigManager in self._singletons else ConfigManager(
            kwargs.get('config_file', 'config.json'),
            kwargs.get('ruler_file', 'ruler.json')
        )

        image_processor = self.get(ImageProcessor) if ImageProcessor in self._singletons else ImageProcessor(
            cache_size=cache_size,
            max_memory_mb=max_memory_mb
        )

        trait_tracker = self.get(TraitTracker) if TraitTracker in self._singletons else TraitTracker(
            max_similar
        )

        metadata_manager = self.get(MetadataManager) if MetadataManager in self._singletons else MetadataManager()

        return GeneratorDependencies(
            config_manager=config_manager,
            image_processor=image_processor,
            trait_tracker=trait_tracker,
            metadata_manager=metadata_manager,
            resource_manager=resource_manager
        )

    def reset(self):
        """Reset all cached instances for testing."""
        self._singletons.clear()
        self._instances.clear()
        logging.debug("Dependency container reset")


# Global dependency container instance
container = DependencyContainer()


def get_dependencies(**kwargs) -> GeneratorDependencies:
    """Convenience function to get generator dependencies."""
    return container.create_generator_dependencies(**kwargs)


def configure_dependencies_for_testing():
    """Configure dependencies for unit testing."""
    from unittest.mock import MagicMock

    # Register mock dependencies for testing
    container.register_instance('mock_config_manager', MagicMock())
    container.register_instance('mock_image_processor', MagicMock())
    container.register_instance('mock_trait_tracker', MagicMock())
    container.register_instance('mock_metadata_manager', MagicMock())

    logging.info("Dependencies configured for testing")
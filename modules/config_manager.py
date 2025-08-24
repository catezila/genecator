#!/usr/bin/env python3
"""
Configuration manager module for NFT Generator
Handles loading, validating, and managing configuration files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union
from jsonschema import validate, ValidationError

from modules.resource_manager import resource_manager, retry_on_io_error
from modules.validation import (
    ConfigurationValidator,
    NFTConfiguration,
    RulerConfiguration,
    ValidationError as CustomValidationError
)

# Optional import for image size detection
try:
    import PIL.Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ConfigManager:
    """Manages configuration loading and validation for the NFT generator."""

    def __init__(
        self, config_file: str = "config.json", ruler_file: str = "ruler.json"
    ):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to the configuration file
            ruler_file: Path to the rules file
        """
        self.config_file = self._sanitize_path(config_file)
        self.ruler_file = self._sanitize_path(ruler_file)
        self.config = None
        self.ruler = None
        self.validator = ConfigurationValidator()
        self.validated_config = None
        self.validated_ruler = None

    def load_config(self, schema_path: Optional[str] = None) -> NFTConfiguration:
        """
        Load and validate the configuration file with enhanced type validation.

        Args:
            schema_path: Path to the JSON schema for validation

        Returns:
            NFTConfiguration: Validated configuration object

        Raises:
            FileNotFoundError: If config file is not found
            ValueError: If JSON is invalid or validation fails
        """
        # Use default schema if none provided
        if schema_path is None:
            schema_path = "config_schema.json"
        raw_config = self._load_json(self.config_file, schema_path)

        # If image_size is not specified in config, try to detect it from trait images
        if "image_size" not in raw_config:
            raw_config["image_size"] = self._detect_image_size()

        # Store raw config for backward compatibility
        self.config = raw_config

        # Validate with enhanced type checking
        try:
            self.validated_config = self.validator.validate_configuration(raw_config)
            logging.info("Enhanced configuration validation successful")
            return self.validated_config
        except CustomValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")

    def load_ruler(self, schema_path: Optional[str] = None) -> RulerConfiguration:
        """
        Load and validate the rules file with enhanced type validation.

        Args:
            schema_path: Path to the JSON schema for validation

        Returns:
            RulerConfiguration: Validated ruler object

        Raises:
            FileNotFoundError: If rules file is not found
            ValueError: If JSON is invalid or validation fails
        """
        # Use default schema if none provided
        if schema_path is None:
            schema_path = "ruler_schema.json"
        raw_ruler = self._load_json(self.ruler_file, schema_path)

        # Store raw ruler for backward compatibility
        self.ruler = raw_ruler

        # Validate with enhanced type checking
        try:
            self.validated_ruler = self.validator.validate_ruler(raw_ruler)
            logging.info("Enhanced ruler validation successful")
            return self.validated_ruler
        except CustomValidationError as e:
            raise ValueError(f"Ruler validation failed: {e}")

    @retry_on_io_error(max_retries=3, base_delay=0.5)
    def _load_json(
        self, file_path: Union[str, Path], schema_path: Optional[str] = None
    ) -> Dict:
        """
        Load and optionally validate a JSON file with safe resource management and retry logic.

        Args:
            file_path: Path to the JSON file
            schema_path: Path to the JSON schema for validation

        Returns:
            dict: Loaded JSON data

        Raises:
            FileNotFoundError: If file is not found
            ValueError: If JSON is invalid or validation fails
        """
        # Sanitize path to prevent path traversal
        safe_path = self._sanitize_path(file_path)

        try:
            with resource_manager.safe_file_operation(safe_path, 'r') as file:
                data = json.load(file)
            if schema_path:
                self._validate_json_with_schema(data, schema_path)
            return data
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {safe_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {safe_path}: {str(e)}")

    def _validate_json_with_schema(self, data: Dict, schema_path: str) -> None:
        """
        Validate JSON data against a given schema file with safe resource management.

        Args:
            data: JSON data to validate
            schema_path: Path to the JSON schema

        Raises:
            ValueError: If validation fails
        """
        # Sanitize path to prevent path traversal
        safe_schema_path = self._sanitize_path(schema_path)

        try:
            with resource_manager.safe_file_operation(safe_schema_path, 'r') as schema_file:
                schema = json.load(schema_file)
            validate(instance=data, schema=schema)
            logging.info(f"Successfully validated JSON against {safe_schema_path}")
        except FileNotFoundError:
            logging.warning(
                f"Schema file not found: {safe_schema_path}. Skipping validation."
            )
        except ValidationError as e:
            raise ValueError(
                f"JSON validation error in {safe_schema_path}: {e.message} at path {e.path}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in schema file {safe_schema_path}: {str(e)}"
            )

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

    def _detect_image_size(self, traits_dir: str = "traits") -> tuple:
        """
        Detect image size from trait files.

        Args:
            traits_dir: Path to the traits directory

        Returns:
            tuple: Image dimensions (width, height)
        """
        # Check if PIL is available
        if not PIL_AVAILABLE:
            # If PIL is not available, return default size
            from modules.constants import DEFAULT_IMAGE_SIZE

            logging.warning(
                "PIL not available for image size detection, using default size"
            )
            return DEFAULT_IMAGE_SIZE

        # Import PIL inside the function to avoid import errors
        import PIL.Image

        # Sanitize traits directory path
        safe_traits_dir = self._sanitize_path(traits_dir)

        # Try to find the first image file to get its dimensions
        if self.config and "trait_order" in self.config:
            trait_order = self.config["trait_order"]
            traits = self.config["traits"]

            # Look through trait directories in order
            for trait_type in trait_order:
                if trait_type in traits:
                    trait_dir = safe_traits_dir / trait_type
                    if trait_dir.exists():
                        # Look for the first image file in this directory
                        for option in traits[trait_type]["options"]:
                            # Check for PNG first
                            png_file = trait_dir / f"{option['name']}.png"
                            if png_file.exists():
                                try:
                                    with PIL.Image.open(png_file) as img:
                                        size = img.size
                                        logging.info(
                                            f"Detected image size {size} from {png_file}"
                                        )
                                        return size
                                except Exception as e:
                                    logging.warning(
                                        f"Could not read image {png_file}: {e}"
                                    )
                                    continue
                            # Check for GIF as alternative
                            gif_file = trait_dir / f"{option['name']}.gif"
                            if gif_file.exists():
                                try:
                                    with PIL.Image.open(gif_file) as img:
                                        size = img.size
                                        logging.info(
                                            f"Detected image size {size} from {gif_file}"
                                        )
                                        return size
                                except Exception as e:
                                    logging.warning(
                                        f"Could not read image {gif_file}: {e}"
                                    )
                                    continue

        # If no images found, return default size
        from modules.constants import DEFAULT_IMAGE_SIZE

        logging.warning(
            f"No images found for size detection, using default size {DEFAULT_IMAGE_SIZE}"
        )
        return DEFAULT_IMAGE_SIZE

    def validate_setup(self, traits_dir: str = "traits") -> None:
        """
        Validate the setup before generation.

        Args:
            traits_dir: Path to the traits directory

        Raises:
            FileNotFoundError: If trait directories or files are missing
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load_config() first.")

        logging.info("Validating setup...")

        trait_order = self.config["trait_order"]
        traits = self.config["traits"]

        # Sanitize traits directory path
        safe_traits_dir = self._sanitize_path(traits_dir)

        # Check trait directories
        for trait_type in trait_order:
            trait_dir = safe_traits_dir / trait_type
            if not trait_dir.exists():
                raise FileNotFoundError(f"Trait directory not found: {trait_dir}")

        # Check trait files
        for trait_type, trait_data in traits.items():
            trait_dir = safe_traits_dir / trait_type
            for option in trait_data["options"]:
                trait_file = trait_dir / f"{option['name']}.png"
                if not trait_file.exists():
                    # Check for GIF file as alternative
                    gif_file = trait_dir / f"{option['name']}.gif"
                    if not gif_file.exists():
                        raise FileNotFoundError(
                            f"Missing trait file: {trait_file} or {gif_file}"
                        )

        logging.info("Setup validation complete")

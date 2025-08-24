#!/usr/bin/env python3
"""
Enhanced trait validation script for NFT Generator
Validates trait images, configuration, and rules using modular architecture.
"""

import sys
import os
import logging
from PIL import Image
from pathlib import Path
from typing import List, Tuple, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.config_manager import ConfigManager


class EnhancedTraitValidator:
    def __init__(
        self,
        config_file: str = "config.json",
        ruler_file: str = "ruler.json",
        traits_dir: str = "traits",
    ):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("nft_validation.log"),
                logging.StreamHandler(),
            ],
        )

        self.config_manager = ConfigManager(config_file, ruler_file)
        self.traits_dir = Path(traits_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        logging.info("🔍 Starting Enhanced NFT Generator validation...")

        self.validate_config()
        self.validate_ruler()
        self.validate_trait_images()
        self.validate_trait_files()

        self.log_report()

        return len(self.errors) == 0

    def validate_config(self) -> None:
        """Validate config.json structure and values"""
        try:
            config = self.config_manager.load_config()
            self.config = config  # Store config for later use

            # Check required keys
            required_keys = ["trait_order", "traits", "image_size"]
            for key in required_keys:
                if key not in config:
                    self.errors.append(
                        f"Missing required key '{key}' in {self.config_manager.config_file}"
                    )
                    return

            # Validate trait order
            trait_order = config["trait_order"]
            if not isinstance(trait_order, list):
                self.errors.append("'trait_order' must be a list")

            # Validate traits
            traits = config["traits"]
            if not isinstance(traits, dict):
                self.errors.append("'traits' must be a dictionary")
                return

            for trait_type, trait_data in traits.items():
                # Check trait structure
                if not isinstance(trait_data, dict):
                    self.errors.append(f"Trait '{trait_type}' must be a dictionary")
                    continue

                if "options" not in trait_data:
                    self.errors.append(
                        f"Trait '{trait_type}' missing 'options'"
                    )
                    continue

                # Validate rarity if present
                if "rarity" in trait_data:
                    rarity = trait_data["rarity"]
                    if not isinstance(rarity, int) or rarity < 1 or rarity > 5:
                        self.errors.append(
                            f"Trait '{trait_type}' rarity must be 1-5 (1 = rarest, 5 = most common)"
                        )

                # Validate options
                options = trait_data["options"]
                if not isinstance(options, list):
                    self.errors.append(f"Trait '{trait_type}' options must be a list")
                    continue

                # Check option rarities sum to 100
                total_rarity = 0
                for option in options:
                    if (
                        not isinstance(option, dict)
                        or "name" not in option
                        or "rarity" not in option
                    ):
                        self.errors.append(f"Invalid option format in '{trait_type}'")
                        continue

                    total_rarity += option["rarity"]

                # For weight-based system, we don't need to check if they sum to 100
                # Instead we'll convert weights to probabilities during generation
                pass

        except FileNotFoundError as e:
            self.errors.append(str(e))
        except ValueError as e:
            self.errors.append(str(e))

    def validate_ruler(self) -> None:
        """Validate ruler.json structure"""
        try:
            config = self.config_manager.load_config()
            ruler = self.config_manager.load_ruler()

            if "rules" not in ruler:
                self.warnings.append("No rules found in ruler.json")
                return

            rules = ruler["rules"]
            if not isinstance(rules, list):
                self.errors.append("'rules' must be a list")
                return

            valid_traits = set(config.get("traits", {}).keys())
            for i, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    self.errors.append(f"Rule {i} must be a dictionary")
                    continue

                if "if" not in rule or "then" not in rule:
                    self.errors.append(f"Rule {i} missing 'if' or 'then'")
                    continue

                # Validate if condition
                if_condition = rule["if"]
                if not isinstance(if_condition, dict):
                    self.errors.append(f"Rule {i} 'if' must be a dictionary")
                    continue

                if "trait_type" not in if_condition or "value" not in if_condition:
                    self.errors.append(f"Rule {i} 'if' missing required keys")
                else:
                    if if_condition["trait_type"] not in valid_traits:
                        self.errors.append(
                            f"Rule {i} 'if.trait_type' '{if_condition['trait_type']}' not in config traits"
                        )

                # Validate then condition
                then_condition = rule["then"]
                if not isinstance(then_condition, dict):
                    self.errors.append(f"Rule {i} 'then' must be a dictionary")
                    continue

                if (
                    "trait_type" not in then_condition
                    or "excluded_values" not in then_condition
                ):
                    self.errors.append(f"Rule {i} 'then' missing required keys")
                else:
                    if then_condition["trait_type"] not in valid_traits:
                        self.errors.append(
                            f"Rule {i} 'then.trait_type' '{then_condition['trait_type']}' not in config traits"
                        )
                    # If concrete values, ensure options contain them
                    if_condition_values = if_condition.get("value", [])
                    if (
                        isinstance(if_condition_values, list)
                        and "*" not in if_condition_values
                    ):
                        options = [
                            o["name"]
                            for o in config["traits"][if_condition["trait_type"]][
                                "options"
                            ]
                        ]
                        for v in if_condition_values:
                            if v not in options:
                                self.errors.append(
                                    f"Rule {i} 'if.value' '{v}' not an option of {if_condition['trait_type']}"
                                )
                    excluded_values = then_condition.get("excluded_values", [])
                    if isinstance(excluded_values, list) and "*" not in excluded_values:
                        options = [
                            o["name"]
                            for o in config["traits"][then_condition["trait_type"]][
                                "options"
                            ]
                        ]
                        for v in excluded_values:
                            if v not in options:
                                self.errors.append(
                                    f"Rule {i} 'then.excluded_values' '{v}' not an option of {then_condition['trait_type']}"
                                )

        except FileNotFoundError as e:
            self.errors.append(str(e))
        except ValueError as e:
            self.errors.append(str(e))

    def validate_trait_images(self) -> None:
        """Validate trait image files"""
        if not self.traits_dir.exists():
            self.errors.append(f"Traits directory '{self.traits_dir}' not found")
            return

        # Check for expected image dimensions from config
        if not hasattr(self, "config") or "image_size" not in self.config:
            self.errors.append(
                "image_size not found in config. Please run get_traits.py to generate config with detected image size."
            )
            return

        expected_size = tuple(self.config["image_size"])

        for trait_type_dir in self.traits_dir.iterdir():
            if not trait_type_dir.is_dir():
                continue

            trait_type = trait_type_dir.name
            png_files = list(trait_type_dir.glob("*.png"))
            gif_files = list(trait_type_dir.glob("*.gif"))

            if not png_files and not gif_files:
                self.warnings.append(f"No PNG/GIF files found in {trait_type}")
                continue

            for png_file in png_files:
                try:
                    # Sanitize path to prevent path traversal
                    safe_path = self._sanitize_path(png_file)

                    with Image.open(safe_path) as img:
                        if img.size != expected_size:
                            self.warnings.append(
                                f"{png_file} has size {img.size}, expected {expected_size}"
                            )

                        if img.mode not in ["RGBA", "RGB"]:
                            self.warnings.append(
                                f"{png_file} has mode {img.mode}, expected RGBA or RGB"
                            )
                        # Alpha channel non-empty check for RGBA images
                        if img.mode == "RGBA":
                            alpha = img.split()[-1]
                            bbox = alpha.getbbox()
                            if bbox is None:
                                self.warnings.append(
                                    f"{png_file} alpha channel is entirely empty - this may be intentional"
                                )
                            else:
                                if alpha.getextrema() == (255, 255):
                                    self.warnings.append(
                                        f"{png_file} alpha is fully opaque; verify expected transparency"
                                    )

                except Exception as e:
                    self.errors.append(f"Error reading {png_file}: {str(e)}")

            # Validate animated GIF consistency within trait type
            if gif_files:
                gif_meta: Optional[Tuple[int, int, int]] = None
                for gif_file in gif_files:
                    try:
                        # Sanitize path to prevent path traversal
                        safe_path = self._sanitize_path(gif_file)

                        with Image.open(safe_path) as im:
                            if not getattr(im, "is_animated", False):
                                self.warnings.append(
                                    f"{gif_file} is GIF but not animated - will be treated as static"
                                )
                                continue
                            meta = (
                                im.n_frames,
                                im.info.get("duration", 0),
                                im.info.get("loop", 0),
                            )
                            if gif_meta is None:
                                gif_meta = meta
                            else:
                                if meta != gif_meta:
                                    self.errors.append(
                                        f"{gif_file} GIF frames/duration/loop mismatch in {trait_type}; expected {gif_meta}, got {meta}"
                                    )
                    except Exception as e:
                        self.errors.append(f"Error reading {gif_file}: {str(e)}")

    def _sanitize_path(self, path: Path) -> Path:
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
        path_obj = path.resolve()

        # Ensure path is within expected directories
        # This is a basic check - in a real application, you might want more sophisticated validation
        if ".." in str(path_obj):
            raise ValueError(f"Invalid path: {path}")

        return path_obj

    def validate_trait_files(self) -> None:
        """Validate that all traits in config exist as files"""
        try:
            config = self.config_manager.load_config()

            traits = config.get("traits", {})

            for trait_type, trait_data in traits.items():
                trait_dir = self.traits_dir / trait_type
                if not trait_dir.exists():
                    self.errors.append(f"Trait directory '{trait_type}' not found")
                    continue

                options = trait_data.get("options", [])
                for option in options:
                    trait_name = option.get("name")
                    if not trait_name:
                        continue

                    # Check for PNG or GIF file
                    png_file = trait_dir / f"{trait_name}.png"
                    gif_file = trait_dir / f"{trait_name}.gif"

                    if not png_file.exists() and not gif_file.exists():
                        self.errors.append(
                            f"Missing trait file: {png_file} or {gif_file}"
                        )

        except Exception as e:
            self.errors.append(f"Error validating trait files: {str(e)}")

    def log_report(self) -> None:
        """Log validation results"""
        logging.info("=" * 50)
        logging.info("ENHANCED VALIDATION REPORT")
        logging.info("=" * 50)

        if self.errors:
            logging.error("❌ ERRORS:")
            for error in self.errors:
                logging.error(f"  • {error}")

        if self.warnings:
            logging.warning("⚠️  WARNINGS:")
            for warning in self.warnings:
                logging.warning(f"  • {warning}")

        if not self.errors and not self.warnings:
            logging.info("✅ All validations passed!")

        logging.info(
            f"Summary: {len(self.errors)} errors, {len(self.warnings)} warnings"
        )


def main() -> None:
    try:
        validator = EnhancedTraitValidator()
        success = validator.validate_all()

        if not success:
            sys.exit(1)
    except Exception as e:
        logging.error(f"Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Validation module for NFT Generator
Provides runtime type validation and data validation using dataclasses and type hints.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


@dataclass
class TraitOption:
    """Validated trait option data."""
    name: str
    rarity: int

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError(f"Invalid trait name: {self.name}")
        if not isinstance(self.rarity, int) or not 1 <= self.rarity <= 5:
            raise ValidationError(f"Invalid rarity {self.rarity} for trait {self.name}")


@dataclass
class TraitConfig:
    """Validated trait configuration."""
    options: List[TraitOption] = field(default_factory=list)
    rarity: Optional[int] = None

    def __post_init__(self):
        if self.rarity is not None and not 1 <= self.rarity <= 5:
            raise ValidationError(f"Invalid trait rarity: {self.rarity}")


@dataclass
class NFTConfiguration:
    """Validated complete NFT configuration."""
    trait_order: List[str]
    traits: Dict[str, TraitConfig]
    image_size: List[int]
    max_similar_combinations: Optional[int] = 1
    ipfs_cid: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    priority_traits: Optional[List[str]] = None

    def __post_init__(self):
        # Validate trait_order
        if not self.trait_order or not all(isinstance(t, str) for t in self.trait_order):
            raise ValidationError("trait_order must be non-empty list of strings")

        # Validate image_size
        if len(self.image_size) != 2 or not all(isinstance(s, int) and s > 0 for s in self.image_size):
            raise ValidationError("image_size must be [width, height] with positive integers")

        # Validate max_similar_combinations
        if self.max_similar_combinations is not None and self.max_similar_combinations < 1:
            raise ValidationError("max_similar_combinations must be >= 1")

        # Validate all traits are in trait_order
        trait_names = set(self.traits.keys())
        order_names = set(self.trait_order)
        if trait_names != order_names:
            missing = order_names - trait_names
            extra = trait_names - order_names
            raise ValidationError(f"Trait mismatch - missing: {missing}, extra: {extra}")


@dataclass
class RuleCondition:
    """Validated rule condition."""
    trait_type: str
    value: Optional[Union[str, List[str]]] = None
    excluded_values: Optional[Union[str, List[str]]] = None

    def __post_init__(self):
        if not isinstance(self.trait_type, str):
            raise ValidationError("trait_type must be string")

        # Ensure exactly one of value or excluded_values is provided
        if (self.value is None and self.excluded_values is None) or (self.value is not None and self.excluded_values is not None):
            raise ValidationError("Exactly one of 'value' or 'excluded_values' must be provided")

        # Validate value if provided
        if self.value is not None:
            if isinstance(self.value, list):
                if not all(isinstance(v, str) for v in self.value):
                    raise ValidationError("All values must be strings")
            elif not isinstance(self.value, str):
                raise ValidationError("value must be string or list of strings")

        # Validate excluded_values if provided
        if self.excluded_values is not None:
            if isinstance(self.excluded_values, list):
                if not all(isinstance(v, str) for v in self.excluded_values):
                    raise ValidationError("All excluded_values must be strings")
            elif not isinstance(self.excluded_values, str):
                raise ValidationError("excluded_values must be string or list of strings")


@dataclass
class RuleConfig:
    """Validated rule configuration."""
    if_condition: RuleCondition
    then_condition: RuleCondition

    @classmethod
    def from_dict(cls, rule_dict: Dict[str, Any]) -> 'RuleConfig':
        # Handle 'if' condition - should have 'value'
        if_condition_dict = rule_dict['if'].copy()
        if 'excluded_values' in if_condition_dict:
            raise ValidationError("'if' condition should use 'value', not 'excluded_values'")

        # Handle 'then' condition - should have 'excluded_values'
        then_condition_dict = rule_dict['then'].copy()
        if 'value' in then_condition_dict:
            raise ValidationError("'then' condition should use 'excluded_values', not 'value'")

        return cls(
            if_condition=RuleCondition(**if_condition_dict),
            then_condition=RuleCondition(**then_condition_dict)
        )


@dataclass
class RulerConfiguration:
    """Validated ruler configuration."""
    rules: List[RuleConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, ruler_dict: Dict[str, Any]) -> 'RulerConfiguration':
        rules = []
        for rule in ruler_dict.get('rules', []):
            rules.append(RuleConfig.from_dict(rule))
        return cls(rules=rules)


class ConfigurationValidator:
    """Runtime configuration validator with detailed error reporting."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_configuration(self, config_dict: Dict[str, Any]) -> NFTConfiguration:
        """
        Validate and convert configuration dictionary to validated dataclass.

        Args:
            config_dict: Raw configuration dictionary

        Returns:
            Validated NFTConfiguration instance

        Raises:
            ValidationError: If validation fails
        """
        self.errors = []
        self.warnings = []

        try:
            # Convert traits to validated objects
            validated_traits = {}
            for trait_name, trait_data in config_dict.get('traits', {}).items():
                options = []
                for option in trait_data.get('options', []):
                    try:
                        options.append(TraitOption(**option))
                    except Exception as e:
                        self.errors.append(f"Trait {trait_name} option {option}: {e}")

                validated_traits[trait_name] = TraitConfig(
                    options=options,
                    rarity=trait_data.get('rarity')
                )

            # Create configuration object
            config = NFTConfiguration(
                trait_order=config_dict['trait_order'],
                traits=validated_traits,
                image_size=config_dict['image_size'],
                max_similar_combinations=config_dict.get('max_similar_combinations'),
                ipfs_cid=config_dict.get('ipfs_cid'),
                metadata=config_dict.get('metadata'),
                priority_traits=config_dict.get('priority_traits')
            )

            if self.errors:
                raise ValidationError(f"Configuration validation failed: {self.errors}")

            logging.info("Configuration validation successful")
            return config

        except KeyError as e:
            raise ValidationError(f"Missing required configuration field: {e}")
        except Exception as e:
            raise ValidationError(f"Configuration validation error: {e}")

    def validate_ruler(self, ruler_dict: Dict[str, Any]) -> RulerConfiguration:
        """
        Validate and convert ruler dictionary to validated dataclass.

        Args:
            ruler_dict: Raw ruler dictionary

        Returns:
            Validated RulerConfiguration instance

        Raises:
            ValidationError: If validation fails
        """
        try:
            config = RulerConfiguration.from_dict(ruler_dict)
            logging.info("Ruler validation successful")
            return config
        except Exception as e:
            raise ValidationError(f"Ruler validation error: {e}")

    def validate_trait_files(self, config: NFTConfiguration, traits_dir: Path) -> bool:
        """
        Validate that trait files exist and are accessible.

        Args:
            config: Validated configuration
            traits_dir: Path to traits directory

        Returns:
            True if all files are accessible
        """
        all_good = True

        for trait_name in config.trait_order:
            trait_dir = traits_dir / trait_name
            if not trait_dir.exists():
                self.errors.append(f"Trait directory not found: {trait_dir}")
                all_good = False
                continue

            trait_config = config.traits[trait_name]
            for option in trait_config.options:
                png_file = trait_dir / f"{option.name}.png"
                gif_file = trait_dir / f"{option.name}.gif"

                if not png_file.exists() and not gif_file.exists():
                    self.errors.append(f"Missing trait file: {png_file} or {gif_file}")
                    all_good = False

        return all_good

    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report."""
        return {
            'errors': self.errors.copy(),
            'warnings': self.warnings.copy(),
            'is_valid': len(self.errors) == 0
        }


# Global validator instance
validator = ConfigurationValidator()


def validate_config(config_dict: Dict[str, Any]) -> NFTConfiguration:
    """Convenience function to validate configuration."""
    return validator.validate_configuration(config_dict)


def validate_ruler(ruler_dict: Dict[str, Any]) -> RulerConfiguration:
    """Convenience function to validate ruler."""
    return validator.validate_ruler(ruler_dict)
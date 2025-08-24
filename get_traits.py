#!/usr/bin/env python3
"""
Enhanced trait discovery script for NFT Generator
Auto-generate config from trait files with improved detection and validation.
"""

import json
from pathlib import Path
from PIL import Image


def analyze_trait_rarities(trait_files):
    """
    Analyze trait rarities based on filename patterns or metadata.

    Args:
        trait_files: List of trait filenames

    Returns:
        list: Trait options with calculated weights (1-5 where 1 is rarest)
    """
    options = []
    total_files = len(trait_files)

    if total_files == 0:
        return options

    # Default weight (middle value)
    default_weight = 3

    # Track which traits had their weights extracted from filenames
    traits_with_extracted_weights = []

    for trait_file in trait_files:
        # Remove extension to get trait name
        trait_name = Path(trait_file).stem

        # Try to extract weight from filename using various patterns
        weight = default_weight
        weight_extracted = False

        # Pattern 1: "TraitName_1" or "TraitName_5" (weight directly)
        if "_" in trait_name:
            parts = trait_name.split("_")
            try:
                # Check if last part is a number between 1-5
                potential_weight = int(parts[-1])
                if 1 <= potential_weight <= 5:
                    weight = potential_weight
                    weight_extracted = True
            except ValueError:
                pass

        # Pattern 2: "1_TraitName" or "5_TraitName" (weight directly)
        if not weight_extracted and "_" in trait_name:
            parts = trait_name.split("_")
            try:
                # Check if first part is a number between 1-5
                potential_weight = int(parts[0])
                if 1 <= potential_weight <= 5:
                    weight = potential_weight
                    weight_extracted = True
            except ValueError:
                pass

        # Pattern 3: "TraitName_Rare" or "TraitName_Common" (keyword-based)
        if not weight_extracted:
            rare_keywords = ["rare", "legendary", "epic", "ultra"]
            common_keywords = ["common", "basic", "normal", "standard"]
            trait_name_lower = trait_name.lower()

            if any(keyword in trait_name_lower for keyword in rare_keywords):
                weight = 1  # Rarest
                weight_extracted = True
            elif any(keyword in trait_name_lower for keyword in common_keywords):
                weight = 5  # Most common
                weight_extracted = True

        options.append({"name": trait_name, "rarity": weight})

        if weight_extracted:
            traits_with_extracted_weights.append(len(options) - 1)  # Store index

    # If we extracted some weights from filenames, use them directly
    # Otherwise, use the default weight for all
    if not traits_with_extracted_weights:
        # No weights extracted from filenames, use default weight for all
        for opt in options:
            opt["rarity"] = default_weight

    return options


def get_image_size_from_first_trait(traits_folder, trait_order):
    """
    Get image size from the first trait image found.

    Args:
        traits_folder: Path to traits directory
        trait_order: List of trait types in order

    Returns:
        tuple: (width, height) or (640, 640) as default
    """
    traits_path = Path(traits_folder)

    # Look for the first image file in trait directories
    # This ensures all generated NFTs will have consistent dimensions
    for trait_type in trait_order:
        trait_dir = traits_path / trait_type
        if not trait_dir.exists():
            continue

        # Check for PNG or GIF files
        for ext in ["*.png", "*.gif"]:
            for img_file in trait_dir.glob(ext):
                try:
                    with Image.open(img_file) as img:
                        width, height = img.size
                        print(f"Detected image size from {img_file}: {width}x{height}")
                        return (width, height)
                except Exception as e:
                    print(f"Warning: Could not read image {img_file}: {e}")
                    continue

    # Fallback to default size
    print("Using default image size: 640x640")
    return (640, 640)


def get_traits_enhanced(traits_folder):
    """
    Enhanced version of get_traits with better organization and rarity analysis.

    Args:
        traits_folder: Path to traits directory

    Returns:
        tuple: (trait_order, traits, image_size)
    """
    traits = {}
    trait_order = []

    traits_path = Path(traits_folder)
    if not traits_path.exists():
        print(f"Traits directory '{traits_folder}' not found.")
        return trait_order, traits, (640, 640)

    # Check if traits_path is actually a directory
    if not traits_path.is_dir():
        print(f"Traits path '{traits_folder}' is not a directory.")
        return trait_order, traits, (640, 640)

    # Get all trait type directories
    try:
        trait_type_dirs = [d for d in traits_path.iterdir() if d.is_dir()]
    except PermissionError:
        print(f"Permission denied accessing traits directory '{traits_folder}'.")
        return trait_order, traits, (640, 640)
    except Exception as e:
        print(f"Error reading traits directory '{traits_folder}': {e}")
        return trait_order, traits, (640, 640)

    # Sort by name for consistent ordering
    trait_type_dirs.sort(key=lambda x: x.name)

    # Separate Background directory if it exists
    background_dir = None
    other_trait_dirs = []
    for trait_type_dir in trait_type_dirs:
        if trait_type_dir.name == "Background":
            background_dir = trait_type_dir
        else:
            other_trait_dirs.append(trait_type_dir)

    # Add Background first if it exists, then other traits
    if background_dir:
        trait_type_dirs = [background_dir] + other_trait_dirs
    else:
        trait_type_dirs = other_trait_dirs

    for trait_type_dir in trait_type_dirs:
        trait_type = trait_type_dir.name
        trait_order.append(trait_type)

        # Get all PNG and GIF files
        trait_files = []
        try:
            for ext in ["*.png", "*.gif"]:
                trait_files.extend([f.name for f in trait_type_dir.glob(ext)])
        except PermissionError:
            print(f"Permission denied accessing trait directory '{trait_type_dir}'.")
            traits[trait_type] = {"options": []}
            continue
        except Exception as e:
            print(f"Error reading trait directory '{trait_type_dir}': {e}")
            traits[trait_type] = {"options": []}
            continue

        # Sort files for consistent ordering
        trait_files.sort()

        if not trait_files:
            print(f"Warning: No trait files found in {trait_type_dir}")
            traits[trait_type] = {"options": []}
            continue

        # Analyze rarities
        options = analyze_trait_rarities(trait_files)

        traits[trait_type] = {"options": options}

        print(f"Found {len(options)} options for {trait_type}")

    # Get image size from first trait
    image_size = get_image_size_from_first_trait(traits_folder, trait_order)
    print(f"Detected image size: {image_size[0]}x{image_size[1]}")

    return trait_order, traits, image_size


def save_config_enhanced(trait_order, traits, image_size, output_file):
    """
    Save enhanced configuration with additional metadata.

    Args:
        trait_order: List of trait types in order
        traits: Dictionary of traits with options
        image_size: Tuple of (width, height) for images
        output_file: Output filename
    """
    # Determine priority traits (first 3 traits or all traits if less than 3)
    # In the future, this could be made configurable
    priority_traits = trait_order[:3] if len(trait_order) >= 3 else trait_order

    config = {
        "trait_order": trait_order,
        "priority_traits": priority_traits,
        "image_size": list(image_size),  # Convert tuple to list for JSON serialization
        "traits": traits,
        "max_similar_combinations": 1,
        "ipfs_cid": "your-ipfs-cid-here",
    }

    try:
        with open(output_file, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Enhanced traits configuration saved to {output_file}")
    except Exception as e:
        print(f"Error saving configuration to {output_file}: {e}")
        raise


def validate_trait_files(traits_folder, trait_order, traits):
    """
    Validate that all trait files exist and have correct format.

    Args:
        traits_folder: Path to traits directory
        trait_order: List of trait types in order
        traits: Dictionary of traits with options
    """
    print("\n🔍 Validating trait files...")
    traits_path = Path(traits_folder)
    issues = []

    try:
        for trait_type in trait_order:
            if trait_type not in traits:
                issues.append(f"Trait type '{trait_type}' not found in configuration")
                continue

            trait_dir = traits_path / trait_type
            if not trait_dir.exists():
                issues.append(f"Trait directory '{trait_dir}' not found")
                continue

            options = traits[trait_type].get("options", [])
            for option in options:
                trait_name = option.get("name")
                if not trait_name:
                    continue

                # Check for PNG or GIF file
                png_file = trait_dir / f"{trait_name}.png"
                gif_file = trait_dir / f"{trait_name}.gif"

                if not png_file.exists() and not gif_file.exists():
                    issues.append(f"Missing trait file: {png_file} or {gif_file}")
    except Exception as e:
        print(f"Error during validation: {e}")
        return False

    if issues:
        print("Validation issues found:")
        for issue in issues:
            print(f"  ❌ {issue}")
        return False
    else:
        print("✅ All trait files validated successfully")
        return True


def main():
    """Enhanced trait discovery and configuration generation."""
    print("🔍 Enhanced Trait Discovery")
    print("=" * 50)

    traits_folder = "traits"
    output_file = "config.json"

    try:
        # Discover traits
        trait_order, traits, image_size = get_traits_enhanced(traits_folder)

        if not trait_order:
            print("No traits found. Please add trait images to the 'traits' directory.")
            return

        # Save configuration
        save_config_enhanced(trait_order, traits, image_size, output_file)

        # Validate files
        validate_trait_files(traits_folder, trait_order, traits)

        # Show summary
        print("\n📊 Summary:")
        print(f"  Trait Types: {len(trait_order)}")
        print(f"  Total Options: {sum(len(traits[t]['options']) for t in trait_order)}")
        print(f"  Image Size: {image_size[0]}x{image_size[1]}")

        for trait_type in trait_order:
            options_count = len(traits[trait_type]["options"])
            print(
                f"  - {trait_type}: {options_count} options"
            )
    except Exception as e:
        print(f"Error running trait discovery: {e}")
        raise


if __name__ == "__main__":
    main()

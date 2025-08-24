#!/usr/bin/env python3
"""
Enhanced NFT Generator with improved error handling and validation
Refactored version using modular architecture.
"""

import logging
import argparse
import sys
import os
from typing import Dict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.nft_generator import NFTGenerator
from modules.constants import DEFAULT_GIF_DURATION_MS, DEFAULT_GIF_LOOP


def main() -> None:
    """Main entry point with argument parsing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("nft_generation.log"), logging.StreamHandler()],
    )

    parser = argparse.ArgumentParser(
        description="Generate NFT collection",
        epilog="Example: python main.py -n 1000 --resume",
    )
    parser.add_argument(
        "-n",
        "--num-nfts",
        type=int,
        default=2000,
        help="Number of NFTs to generate (default: 2000)",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Configuration file (default: config.json)",
    )
    parser.add_argument(
        "-r", "--ruler", default="ruler.json", help="Rules file (default: ruler.json)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume generation by skipping existing outputs and loading state",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducible runs")
    parser.add_argument(
        "--workers", type=int, help="Number of worker processes for trait generation"
    )
    parser.add_argument(
        "--compact-metadata",
        action="store_true",
        help="Write compact JSON metadata without whitespace",
    )
    parser.add_argument(
        "--max-similar", type=int, help="Override max_similar_combinations"
    )
    parser.add_argument(
        "--include-override",
        action="append",
        metavar="TRAIT=PROB",
        help="Override include probability (0-100) per trait; repeatable",
    )
    parser.add_argument("--max-attempts", type=int, help="Max attempts per NFT")
    parser.add_argument(
        "--max-trait-attempts", type=int, help="Max attempts per trait selection"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write images/metadata; just simulate",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
        help="Checkpoint resume state every N IDs",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip startup validation (use with caution)",
    )
    parser.add_argument(
        "--bg",
        help="DEPRECATED: Path to JSON file with list of background hex colors (use Background trait instead)",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg", "jpeg", "webp"],
        help="Output image format",
    )
    parser.add_argument(
        "--quality", type=int, help="Quality for lossy formats (jpg/webp)"
    )
    parser.add_argument(
        "--gif-duration",
        type=int,
        default=DEFAULT_GIF_DURATION_MS,
        help="Frame duration (ms) for GIF output",
    )
    parser.add_argument(
        "--gif-loop",
        type=int,
        default=DEFAULT_GIF_LOOP,
        help="Loop count for GIF output",
    )
    parser.add_argument(
        "--image-size",
        nargs=2,
        type=int,
        metavar=("WIDTH", "HEIGHT"),
        help="Custom image dimensions (width height)",
    )

    args = parser.parse_args()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    try:
        logging.info("🚀 Initializing Enhanced NFT Generator...")
        # Parse include overrides
        include_overrides: Dict[str, float] = {}
        if args.include_override:
            for item in args.include_override:
                if "=" in item:
                    k, v = item.split("=", 1)
                    try:
                        include_overrides[k] = float(v)
                    except ValueError:
                        logging.warning(f"Invalid include override value for {k}: {v}")

        # Warn if deprecated --bg argument is used
        if args.bg:
            logging.warning(
                "⚠️  The --bg argument is deprecated. Please use Background trait instead."
            )

        generator = NFTGenerator(
            args.config,
            args.ruler,
            seed=args.seed,
            max_similar=args.max_similar,
            include_overrides=include_overrides or None,
            max_attempts=args.max_attempts,
            max_trait_attempts=args.max_trait_attempts,
            validate_skip=args.skip_validate,
            image_size=tuple(args.image_size) if args.image_size else None,
        )

        if args.resume:
            logging.info(
                "Resuming generation: existing outputs will be skipped and state updated"
            )

        logging.info(
            f"📊 Configuration loaded: {len(generator.trait_order)} trait types"
        )
        logging.info(
            f"🎨 Rules loaded: {len(generator.ruler.rules)} compatibility rules"
        )

        # Define progress callback
        def progress_callback(current: int, total: int) -> None:
            if current % 100 == 0:
                logging.info(
                    f"Progress: {current}/{total} NFTs generated ({current/total*100:.1f}%)"
                )

        generator.generate_collection(
            args.num_nfts,
            workers=args.workers,
            compact_metadata=args.compact_metadata,
            dry_run=args.dry_run,
            checkpoint_every=args.checkpoint_every,
            img_format=args.format,
            quality=args.quality,
            progress_callback=progress_callback,
        )

        logging.info("✅ NFT generation completed successfully!")

    except Exception as e:
        logging.error(f"❌ Generation failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()

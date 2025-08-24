#!/usr/bin/env python3
"""
Main NFT Generator module
Core generation logic with improved error handling and validation.
"""

import json
import random
import os
import hashlib
import logging
import multiprocessing as mp
import threading
from collections import Counter, OrderedDict, defaultdict
from typing import Dict, List, Tuple, Optional, Any, Callable
from pathlib import Path
from tqdm import tqdm

from modules.resource_manager import resource_manager

from modules.trait_tracker import TraitTracker
from modules.image_processor import ImageProcessor
from modules.config_manager import ConfigManager
from modules.metadata_manager import MetadataManager
from modules.validation import NFTConfiguration, RulerConfiguration
from modules.dependency_container import GeneratorDependencies
from modules.constants import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_MAX_TRAIT_ATTEMPTS,
    DEFAULT_GIF_DURATION_MS,
    DEFAULT_GIF_LOOP,
    OUTPUT_DIR,
    IMAGE_DIR,
    METADATA_DIR,
    SEEN_HASHES_FILE,
    TRACKER_STATE_FILE,
    RNG_STATE_FILE,
)


class NFTGenerator:
    """Enhanced NFT Generator with improved error handling and validation."""

    def __init__(
        self,
        config_file: str,
        ruler_file: str,
        seed: Optional[int] = None,
        max_similar: Optional[int] = None,
        include_overrides: Optional[Dict[str, float]] = None,
        max_attempts: Optional[int] = None,
        max_trait_attempts: Optional[int] = None,
        validate_skip: bool = False,
        image_size: Optional[tuple] = None,
        dependencies: Optional[GeneratorDependencies] = None,
    ):
        """
        Initialize NFT Generator.

        Args:
            config_file: Path to configuration file
            ruler_file: Path to rules file
            seed: Random seed for reproducible runs
            max_similar: Override max_similar_combinations
            include_overrides: Override include probability per trait
            max_attempts: Max attempts per NFT
            max_trait_attempts: Max attempts per trait selection
            validate_skip: Skip startup validation
            image_size: Custom image dimensions (width, height)
            dependencies: Optional injected dependencies for testing
        """
        # Initialize managers (use injected dependencies if provided)
        if dependencies:
            self.config_manager = dependencies.config_manager
            self.image_processor = dependencies.image_processor
            self.trait_tracker = dependencies.trait_tracker
            self.metadata_manager = dependencies.metadata_manager
        else:
            self.config_manager = ConfigManager(config_file, ruler_file)
            self.image_processor = ImageProcessor(cache_size=128, max_memory_mb=512)
            self.metadata_manager = MetadataManager()

        # Load configuration with enhanced validation
        self.config = self.config_manager.load_config()
        self.ruler = self.config_manager.load_ruler()
        self.trait_order = self.config.trait_order
        self.traits = {name: {"options": [{"name": opt.name, "rarity": opt.rarity} for opt in trait.options],
                             "rarity": trait.rarity} for name, trait in self.config.traits.items()}

        # Set image size (command line argument takes precedence over config)
        if image_size is not None:
            self.config.image_size = image_size
        self.setup_directories()

        # Initialize TraitTracker with configurable MAX_SIMILAR_COMBINATIONS
        max_similar_combinations = self.config.max_similar_combinations or 1
        if max_similar is not None:
            max_similar_combinations = max_similar

        # Use injected trait tracker if provided, otherwise create new one
        if not hasattr(self, 'trait_tracker') or not self.trait_tracker:
            self.trait_tracker = TraitTracker(max_similar_combinations)

        self.generated_hashes = set()
        self.failed_attempts = Counter()

        # Apply include overrides
        if include_overrides:
            for tt, prob in include_overrides.items():
                if tt in self.traits:
                    self.traits[tt]["rarity"] = prob
        # Override attempts if provided
        self.MAX_ATTEMPTS = (
            max_attempts if max_attempts is not None else DEFAULT_MAX_ATTEMPTS
        )
        self.MAX_TRAIT_ATTEMPTS = (
            max_trait_attempts
            if max_trait_attempts is not None
            else DEFAULT_MAX_TRAIT_ATTEMPTS
        )

        # Precompute weights per trait for fast sampling
        # Convert rarity (1-5) to weights where 1 = rarest (lowest weight), 5 = most common (highest weight)
        self._option_cache = {}
        for trait_type, trait_data in self.traits.items():
            options = trait_data["options"]
            names = [o["name"] for o in options]
            # Use rarity value directly as weight: 1->1, 2->2, 3->3, 4->4, 5->5 (1 is rarest)
            weights = [o["rarity"] if o["rarity"] is not None else 3 for o in options]
            self._option_cache[trait_type] = (options, names, weights)

        # Index rules by involved trait types for quicker checks
        self._rules_by_then = defaultdict(list)
        self._rules_by_if = defaultdict(list)
        for rule in self.ruler.rules:
            self._rules_by_then[rule.then_condition.trait_type].append(rule)
            self._rules_by_if[rule.if_condition.trait_type].append(rule)

        if not validate_skip:
            self.config_manager.validate_setup()

        # Thread lock for resume functionality to prevent race conditions
        self._resume_lock = threading.Lock()

        # Seed RNG if provided
        if seed is not None:
            random.seed(seed)

        # Resume state
        self._resume_load_existing()

    def setup_directories(self) -> None:
        """Set up output directories."""
        self.output_dir = OUTPUT_DIR
        self.image_dir = os.path.join(self.output_dir, IMAGE_DIR)
        self.metadata_dir = os.path.join(self.output_dir, METADATA_DIR)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
        # Paths for resume state
        self._seen_hashes_path = os.path.join(self.output_dir, SEEN_HASHES_FILE)
        self._tracker_state_path = os.path.join(self.output_dir, TRACKER_STATE_FILE)
        self._rng_state_path = os.path.join(self.output_dir, RNG_STATE_FILE)

    def should_include_trait(self, trait_type: str) -> bool:
        """Determine if a trait should be included based on rarity weight."""
        # Get weight from config, defaulting to 1 (rarest) if not specified
        weight = self.traits[trait_type].get("rarity", 1)
        # Handle None weight
        if weight is None:
            weight = 1
        # Convert weight (1-5) to probability (1 = 20% rarest, 5 = 100% most common)
        probability = weight * 20  # 1->20%, 2->40%, 3->60%, 4->80%, 5->100%
        return random.random() * 100 < probability

    def select_trait(self, trait_type: str) -> Dict[str, Any]:
        """Select a trait option based on weighted randomness."""
        options, _names, weights = self._option_cache[trait_type]
        idx = random.choices(range(len(options)), weights=weights, k=1)[0]
        return options[idx]

    def is_valid_trait(
        self, selected_traits: Dict[str, str], new_trait_type: str, new_trait_value: str
    ) -> bool:
        """Check if a new trait value is valid according to the rules."""
        # Rules where then.trait_type == new_trait_type
        for rule in self._rules_by_then.get(new_trait_type, []):
            if_condition = rule.if_condition
            then_condition = rule.then_condition
            condition_trait_type = if_condition.trait_type
            if condition_trait_type in selected_traits:
                condition_value = selected_traits[condition_trait_type]
                condition_values = if_condition.value
                if "*" in condition_values or condition_value in condition_values:
                    excluded_values = then_condition.excluded_values
                    if "*" in excluded_values or new_trait_value in excluded_values:
                        return False

        # Rules where if.trait_type == new_trait_type
        for rule in self._rules_by_if.get(new_trait_type, []):
            if_condition = rule.if_condition
            then_condition = rule.then_condition
            condition_values = if_condition.value
            if "*" in condition_values or new_trait_value in condition_values:
                affected_trait = then_condition.trait_type
                if affected_trait in selected_traits:
                    existing_value = selected_traits[affected_trait]
                    excluded_values = then_condition.excluded_values
                    if "*" in excluded_values or existing_value in excluded_values:
                        return False

        return True

    def generate_nft(self, nft_id: int) -> Tuple[Dict[str, str], str]:
        """Generate a single NFT with detailed error reporting."""
        for attempt in range(self.MAX_ATTEMPTS):
            traits = OrderedDict()
            valid_combination = True

            # Priority traits for uniqueness (use first 3 traits in order if not specified)
            priority_traits = self.config.priority_traits or (
                self.trait_order[:3]
                if len(self.trait_order) >= 3
                else self.trait_order
            )
            remaining_traits = [t for t in self.trait_order if t not in priority_traits]
            generation_order = priority_traits + remaining_traits

            for trait_type in generation_order:
                if self.should_include_trait(trait_type):
                    valid_trait = False
                    trait_attempts = 0

                    for _ in range(self.MAX_TRAIT_ATTEMPTS):
                        trait = self.select_trait(trait_type)
                        if self.is_valid_trait(traits, trait_type, trait["name"]):
                            traits[trait_type] = trait["name"]
                            valid_trait = True
                            break
                        trait_attempts += 1

                    if not valid_trait:
                        valid_combination = False
                        self.failed_attempts["trait_validation"] += 1
                        logging.debug(
                            f"Failed to find valid trait for {trait_type} in NFT {nft_id}"
                        )
                        break

            if valid_combination and self.trait_tracker.is_unique_enough(traits):
                nft_hash = hashlib.sha256(
                    json.dumps(traits, sort_keys=True).encode()
                ).hexdigest()
                if nft_hash not in self.generated_hashes:
                    self.generated_hashes.add(nft_hash)
                    self.trait_tracker.update_patterns(traits)
                    return traits, nft_hash
            else:
                self.failed_attempts["uniqueness"] += 1

        raise Exception(
            f"Failed to generate unique NFT #{nft_id} after {self.MAX_ATTEMPTS} attempts"
        )

    def save_nft(
        self,
        traits: Dict[str, str],
        nft_id: int,
        nft_hash: str,
        compact_metadata: bool = False,
        img_format: str = "png",
        quality: Optional[int] = None,
        gif_duration_ms: int = DEFAULT_GIF_DURATION_MS,
        gif_loop: int = DEFAULT_GIF_LOOP,
    ) -> Optional[str]:
        """
        Save NFT image and metadata with enhanced error handling.

        Args:
            traits: Dictionary of trait types and values
            nft_id: ID of the NFT
            nft_hash: Hash of the NFT traits
            compact_metadata: Whether to write compact JSON metadata
            img_format: Output image format
            quality: Quality for lossy formats
            gif_duration_ms: Frame duration for GIF output
            gif_loop: Loop count for GIF output

        Returns:
            str: Background color used
        """
        try:
            # Determine trait file paths
            trait_layers = {}
            is_animated = False
            gif_layers = []
            static_layers = []

            for trait_type in self.trait_order:
                if trait_type in traits:
                    base_path = f"traits/{trait_type}/{traits[trait_type]}"
                    gif_path = base_path + ".gif"
                    png_path = base_path + ".png"
                    if os.path.exists(gif_path):
                        is_animated = True
                        gif_layers.append(gif_path)
                        trait_layers[trait_type] = gif_path
                    elif os.path.exists(png_path):
                        static_layers.append(png_path)
                        trait_layers[trait_type] = png_path
                    else:
                        raise FileNotFoundError(
                            f"Missing trait file: {gif_path} or {png_path}"
                        )

            # Ensure image_size is in config
            if not self.config.image_size:
                raise ValueError(
                    "image_size is required in config.json. Please run 'python get_traits.py' to generate config with detected image size."
                )

            if is_animated:
                # Get image size from config (required field)
                image_size = tuple(self.config.image_size)

                # Compose animated NFT
                frames, dur, lp = self.image_processor.compose_animated_nft(
                    gif_layers, static_layers, image_size, gif_duration_ms, gif_loop
                )
                ext = "gif"
                image_path = f"{self.image_dir}/{nft_id}.{ext}"
                frames[0].save(
                    image_path,
                    save_all=True,
                    append_images=frames[1:],
                    loop=lp if lp is not None else gif_loop,
                    duration=dur if dur is not None else gif_duration_ms,
                    disposal=2,
                )
            else:
                # Get image size from config (required field)
                image_size = tuple(self.config.image_size)

                # Compose static NFT
                base_image = self.image_processor.compose_static_nft(
                    trait_layers, self.trait_order, traits, image_size
                )

                # Save image
                ext = img_format.lower()
                if ext == "jpeg":
                    ext = "jpg"
                image_path = f"{self.image_dir}/{nft_id}.{ext}"
                save_kwargs = {}
                if ext in ("jpg", "jpeg", "webp") and quality is not None:
                    save_kwargs["quality"] = int(quality)
                if ext in ("jpg", "jpeg"):
                    save_kwargs["optimize"] = True
                    # convert to RGB for JPEG
                    base_to_save = base_image.convert("RGB")
                else:
                    base_to_save = base_image
                base_to_save.save(
                    image_path, format=None if ext != "webp" else "WEBP", **save_kwargs
                )

            logging.info(f"Saved NFT image: {image_path}")

            # Create and save metadata
            metadata = self.metadata_manager.create_nft_metadata(
                nft_id,
                traits,
                nft_hash,
                ipfs_cid=self.config.ipfs_cid or "<your-ipfs-cid>",
                image_ext=ext,
                metadata_config=self.config.metadata or {},
            )

            self.metadata_manager.save_nft_metadata(nft_id, metadata, compact_metadata)
            logging.info(f"Saved NFT metadata: {self.metadata_dir}/{nft_id}.json")

            return None

        except Exception as e:
            logging.error(f"Error saving NFT {nft_id}: {str(e)}")
            raise

    def _resume_load_existing(self) -> None:
        """Load existing state for resume functionality with thread safety."""
        with self._resume_lock:
            try:
                # Load generated hashes
                if os.path.exists(self._seen_hashes_path):
                    with open(self._seen_hashes_path, "r") as f:
                        self.generated_hashes = set(json.load(f))
                # Load tracker
                if os.path.exists(self._tracker_state_path):
                    with open(self._tracker_state_path, "r") as f:
                        state = json.load(f)
                    self.trait_tracker.bsh_combinations = set(
                        tuple(x) for x in state.get("bsh", [])
                    )
                    self.trait_tracker.trait_patterns = defaultdict(
                        int,
                        {
                            tuple(map(tuple, k.split("||"))): v
                            for k, v in state.get("patterns", {}).items()
                        },
                    )
            except Exception as e:
                logging.warning(f"Failed to load resume state: {e}")
            # Load RNG state if present
            try:
                if os.path.exists(self._rng_state_path):
                    with open(self._rng_state_path, "r") as f:
                        state = json.load(f)
                    random.setstate(tuple(state))
            except Exception as e:
                logging.warning(f"Failed to load RNG state: {e}")

    def _resume_save_state(self) -> None:
        """Save current state for resume functionality with thread safety and atomic writes."""
        with self._resume_lock:
            try:
                # Write seen hashes atomically
                with resource_manager.atomic_file_write(Path(self._seen_hashes_path)) as f:
                    json.dump(sorted(list(self.generated_hashes)), f)

                # Serialize tracker patterns
                patterns_serialized = {
                    "||".join([f"{a}:{b}" for (a, b) in pattern]): count
                    for pattern, count in self.trait_tracker.trait_patterns.items()
                }
                tracker_data = {
                    "bsh": sorted(list(self.trait_tracker.bsh_combinations)),
                    "patterns": patterns_serialized,
                }

                # Write tracker state atomically
                with resource_manager.atomic_file_write(Path(self._tracker_state_path)) as f:
                    json.dump(tracker_data, f)

            except Exception as e:
                logging.warning(f"Failed to save resume state: {e}")

            # Save RNG state atomically
            try:
                state = random.getstate()
                with resource_manager.atomic_file_write(Path(self._rng_state_path)) as f:
                    json.dump(list(state), f)
            except Exception as e:
                logging.warning(f"Failed to save RNG state: {e}")

    def _generate_single_nft_worker(
        self,
        nft_id: int,
        compact_metadata: bool,
        img_format: str,
        quality: Optional[int],
        gif_duration_ms: int,
        gif_loop: int,
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Worker function for generating a single NFT in multiprocessing.

        Args:
            nft_id: ID of the NFT to generate
            compact_metadata: Whether to write compact JSON metadata
            img_format: Output image format
            quality: Quality for lossy formats
            gif_duration_ms: Frame duration for GIF output
            gif_loop: Loop count for GIF output
            dry_run: Whether to simulate without writing files

        Returns:
            Dictionary with NFT data or None if failed
        """
        try:
            nft_traits, nft_hash = self.generate_nft(nft_id)
            if not dry_run:
                self.save_nft(
                    nft_traits,
                    nft_id,
                    nft_hash,
                    compact_metadata=compact_metadata,
                    img_format=img_format,
                    quality=quality,
                    gif_duration_ms=gif_duration_ms,
                    gif_loop=gif_loop,
                )
            return {
                "id": nft_id,
                "image_name": f"{nft_id}",
                "traits": nft_traits,
                "hash": nft_hash,
            }
        except Exception as e:
            logging.error(f"Failed to generate NFT {nft_id}: {str(e)}")
            return None

    def generate_collection(
        self,
        num_nfts: int,
        workers: Optional[int] = None,
        compact_metadata: bool = False,
        dry_run: bool = False,
        checkpoint_every: int = 25,
        img_format: str = "png",
        quality: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """
        Generate collection with enhanced progress tracking and error handling.

        Args:
            num_nfts: Number of NFTs to generate
            workers: Number of worker processes for multiprocessing
            compact_metadata: Whether to write compact JSON metadata
            dry_run: Whether to simulate without writing files
            checkpoint_every: Checkpoint interval
            img_format: Output image format
            quality: Quality for lossy formats
            progress_callback: Optional callback function to report progress
        """
        collection = []
        logging.info(f"Starting generation of {num_nfts} NFTs...")

        # Track statistics

        pending_ids = [
            i
            for i in range(1, num_nfts + 1)
            if not (
                os.path.exists(os.path.join(self.output_dir, f"{i}.{img_format}"))
                and os.path.exists(os.path.join(self.metadata_dir, f"{i}.json"))
            )
        ]
        # Deterministic shuffle of IDs based on current RNG state
        try:
            rng = random.Random()
            rng.setstate(random.getstate())
            rng.shuffle(pending_ids)
        except Exception:
            pass

        # If workers specified and > 1, use multiprocessing
        if workers is not None and workers > 1:
            logging.info(f"Using multiprocessing with {workers} workers")
            self._generate_collection_multiprocess(
                pending_ids,
                workers,
                compact_metadata,
                dry_run,
                checkpoint_every,
                img_format,
                quality,
                collection,
                num_nfts,
                progress_callback,
            )
        else:
            # Single process generation
            self._generate_collection_single_process(
                pending_ids,
                compact_metadata,
                dry_run,
                checkpoint_every,
                img_format,
                quality,
                collection,
                num_nfts,
                progress_callback,
            )

        # Save comprehensive collection data
        if not dry_run:
            stats = self.metadata_manager.generate_collection_stats(
                collection, self.trait_tracker, self.failed_attempts
            )
            self.metadata_manager.save_collection_data(collection, stats, self.traits)
            # Final resume save
            self._resume_save_state()

        # Print final statistics
        success_rate = (len(collection) / num_nfts) * 100
        logging.info(f"Generation complete. Success rate: {success_rate:.2f}%")
        logging.info(f"Failed attempts: {dict(self.failed_attempts)}")

        # Log cache performance statistics
        cache_stats = self.image_processor.get_cache_stats()
        logging.info(f"Image cache performance: {cache_stats['hit_rate_percent']:.1f}% hit rate, "
                    f"{cache_stats['memory_usage_mb']:.1f}MB used of {cache_stats['max_memory_mb']:.1f}MB limit")

        # Emit summary of rarest trait options
        distribution = self.metadata_manager.calculate_trait_distribution(collection)
        rare_list = []
        total = len(collection) or 1
        for trait_type, counts in distribution.items():
            for name, cnt in counts.items():
                pct = (cnt / total) * 100
                rare_list.append((pct, trait_type, name, cnt))
        for pct, trait_type, name, cnt in sorted(rare_list)[:10]:
            print(f"  Rare: {trait_type}={name} -> {cnt} ({pct:.2f}%)")

    def _generate_collection_single_process(
        self,
        pending_ids: List[int],
        compact_metadata: bool,
        dry_run: bool,
        checkpoint_every: int,
        img_format: str,
        quality: Optional[int],
        collection: List[Dict[str, Any]],
        num_nfts: int,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Generate collection using single process."""
        with tqdm(total=num_nfts, desc="Generating NFTs", unit="NFT") as pbar:
            # Pre-advance for already existing
            pbar.update(num_nfts - len(pending_ids))

            for i in pending_ids:
                try:
                    result = self._generate_single_nft_worker(
                        i,
                        compact_metadata,
                        img_format,
                        quality,
                        DEFAULT_GIF_DURATION_MS,
                        DEFAULT_GIF_LOOP,
                        dry_run,
                    )
                    if result:
                        collection.append(result)
                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(len(collection), num_nfts)
                except Exception as e:
                    logging.error(f"Failed to generate NFT {i}: {str(e)}")
                finally:
                    pbar.update(1)
                    if not dry_run and i % checkpoint_every == 0:
                        self._resume_save_state()
                    if i % 100 == 0:
                        logging.info(f"Generated {i}/{num_nfts} NFTs")

    def _generate_collection_multiprocess(
        self,
        pending_ids: List[int],
        workers: int,
        compact_metadata: bool,
        dry_run: bool,
        checkpoint_every: int,
        img_format: str,
        quality: Optional[int],
        collection: List[Dict[str, Any]],
        num_nfts: int,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Generate collection using multiprocessing."""
        # Split pending IDs into chunks for each worker
        chunk_size = max(1, len(pending_ids) // workers)
        chunks = [
            pending_ids[i : i + chunk_size]
            for i in range(0, len(pending_ids), chunk_size)
        ]

        with tqdm(total=num_nfts, desc="Generating NFTs", unit="NFT") as pbar:
            # Pre-advance for already existing
            pbar.update(num_nfts - len(pending_ids))

            # Process chunks with multiprocessing
            with mp.Pool(processes=workers) as pool:
                # Create tasks for each NFT
                tasks = []
                for chunk in chunks:
                    for nft_id in chunk:
                        task = pool.apply_async(
                            self._generate_single_nft_worker,
                            args=(
                                nft_id,
                                compact_metadata,
                                img_format,
                                quality,
                                DEFAULT_GIF_DURATION_MS,
                                DEFAULT_GIF_LOOP,
                                dry_run,
                            ),
                        )
                        tasks.append((nft_id, task))

                # Collect results
                for nft_id, task in tasks:
                    try:
                        result = task.get(timeout=300)  # 5 minute timeout
                        if result:
                            collection.append(result)
                    except Exception as e:
                        logging.error(f"Failed to generate NFT {nft_id}: {str(e)}")
                    finally:
                        pbar.update(1)
                        # Checkpointing in multiprocessing context is complex
                        # For simplicity, we'll do it periodically based on index
                        if not dry_run and nft_id % checkpoint_every == 0:
                            self._resume_save_state()
                        if nft_id % 100 == 0:
                            logging.info(f"Generated {nft_id}/{num_nfts} NFTs")

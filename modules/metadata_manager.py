#!/usr/bin/env python3
"""
Metadata manager module for NFT Generator
Handles metadata creation and management with support for multiple standards.
"""

import json
import time
import hashlib
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from modules.constants import OUTPUT_DIR, METADATA_DIR


class MetadataManager:
    """Manages metadata creation and statistics for the NFT collection."""

    def __init__(self, output_dir: str = OUTPUT_DIR, metadata_dir: str = METADATA_DIR):
        """
        Initialize metadata manager.

        Args:
            output_dir: Path to the output directory
            metadata_dir: Name of the metadata subdirectory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.metadata_dir = self.output_dir / metadata_dir
        self.metadata_dir.mkdir(exist_ok=True)

    def create_nft_metadata(
        self,
        nft_id: int,
        traits: Dict[str, str],
        nft_hash: str,
        ipfs_cid: Optional[str] = None,
        image_ext: str = "png",
        metadata_config: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create metadata for a single NFT following OpenSea standard.

        Args:
            nft_id: ID of the NFT
            traits: Dictionary of trait types and values
            nft_hash: Hash of the NFT traits
            ipfs_cid: IPFS CID for the image hosting
            image_ext: Image file extension
            metadata_config: Configuration for metadata fields

        Returns:
            dict: NFT metadata
        """
        # Set default metadata configuration
        if metadata_config is None:
            metadata_config = {}

        name_template = metadata_config.get("name_template", "CataPix #{id}")
        description = metadata_config.get(
            "description",
            "the 32bit pixel Cat in XRP world. Come with fun and will be live here forever as you pet.",
        )
        external_url = metadata_config.get("external_url", "https://Catezila.fun")
        collection_name = metadata_config.get("collection_name", "CataPix")

        # Enhanced metadata structure following OpenSea standard
        metadata = {
            "name": name_template.replace("{id}", str(nft_id)),
            "description": description,
            "image": f"ipfs://{ipfs_cid or '<your-ipfs-cid>'}/{nft_id}.{image_ext}",
            "external_url": external_url,
            "attributes": [
                {"trait_type": trait_type, "value": traits.get(trait_type, "None")}
                for trait_type in traits.keys()
                if traits.get(trait_type) is not None
            ],
            "properties": {
                "nft_id": nft_id,
                "hash": nft_hash,
                "generation_timestamp": str(int(time.time())),
                "collection": collection_name,
            },
        }

        return metadata

    def save_nft_metadata(
        self, nft_id: int, metadata: Dict[str, Any], compact: bool = False
    ) -> None:
        """
        Save NFT metadata to file.

        Args:
            nft_id: ID of the NFT
            metadata: Metadata dictionary
            compact: Whether to save as compact JSON
        """
        metadata_path = self.metadata_dir / f"{nft_id}.json"
        with open(metadata_path, "w") as f:
            if compact:
                json.dump(metadata, f, separators=(",", ":"), ensure_ascii=False)
            else:
                json.dump(metadata, f, indent=2)

    def calculate_trait_distribution(
        self, collection: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, int]]:
        """
        Calculate trait distribution across the collection.

        Args:
            collection: List of NFT data dictionaries

        Returns:
            dict: Trait distribution statistics
        """
        distribution = defaultdict(lambda: defaultdict(int))

        for nft in collection:
            for trait_type, value in nft["traits"].items():
                distribution[trait_type][value] += 1

        # Convert to regular dict for JSON serialization
        return {k: dict(v) for k, v in distribution.items()}

    def generate_collection_stats(
        self,
        collection: List[Dict[str, Any]],
        tracker: Any,
        failed_attempts: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Generate comprehensive collection statistics.

        Args:
            collection: List of NFT data dictionaries
            tracker: TraitTracker instance
            failed_attempts: Counter of failed generation attempts

        Returns:
            dict: Collection statistics
        """
        distribution = self.calculate_trait_distribution(collection)

        stats_data = {
            "total_nfts": len(collection),
            "unique_bsh_combinations": len(tracker.bsh_combinations),
            "unique_4trait_patterns": len(tracker.trait_patterns),
            "generation_failures": dict(failed_attempts),
            "trait_distribution": distribution,
            "timestamp": str(int(time.time())),
        }

        return stats_data

    def save_collection_data(
        self,
        collection: List[Dict[str, Any]],
        stats: Dict[str, Any],
        config_traits: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save comprehensive collection data.

        Args:
            collection: List of NFT data dictionaries
            stats: Collection statistics
            config_traits: Configuration traits data for rarity report
        """
        # Save collection metadata
        collection_path = self.output_dir / "collection_metadata.json"
        with open(collection_path, "w") as f:
            json.dump(collection, f, indent=2)

        # Save detailed statistics
        stats_path = self.output_dir / "collection_stats.json"
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        # Write rarity report CSV if config_traits provided
        if config_traits:
            self._write_rarity_report(stats, config_traits)

        # Write manifest with hashes
        self._write_manifest(collection)

    def _write_rarity_report(
        self, stats: Dict[str, Any], config_traits: Dict[str, Any]
    ) -> None:
        """
        Write rarity report CSV.

        Args:
            stats: Collection statistics
            config_traits: Configuration traits data
        """
        try:
            report_path = self.output_dir / "rarity_report.csv"
            counts = stats["trait_distribution"]
            total = stats["total_nfts"] or 1

            with open(report_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    ["trait_type", "option", "expected_pct", "actual_pct", "count"]
                )

                for trait_type in config_traits:
                    if trait_type not in counts:
                        continue
                    options = config_traits[trait_type]["options"]
                    for opt in options:
                        name = opt["name"]
                        # Calculate expected percentage based on weights (1-5 where 1 is rarest)
                        # Convert weights to probabilities: 1->5, 2->4, 3->3, 4->2, 5->1
                        total_weight = sum(6 - o["rarity"] for o in options)
                        expected_weight = 6 - opt["rarity"]
                        expected_pct = (
                            (expected_weight / max(1, total_weight)) * 100
                            if total_weight > 0
                            else 0
                        )
                        count = counts.get(trait_type, {}).get(name, 0)
                        actual_pct = (count / total) * 100
                        writer.writerow(
                            [
                                trait_type,
                                name,
                                f"{expected_pct:.2f}",
                                f"{actual_pct:.2f}",
                                count,
                            ]
                        )
        except Exception as e:
            print(f"Warning: Failed to write rarity report: {e}")

    def _write_manifest(self, collection: List[Dict[str, Any]]) -> None:
        """
        Write manifest with file hashes.

        Args:
            collection: List of NFT data dictionaries
        """
        try:
            manifest = []
            for item in collection:
                img_path = self.output_dir / f"{item['image_name']}"
                meta_path = self.metadata_dir / f"{item['id']}.json"

                def _sha256(p: Union[str, Path]) -> str:
                    h = hashlib.sha256()
                    with open(p, "rb") as fh:
                        for chunk in iter(lambda: fh.read(8192), b""):
                            h.update(chunk)
                    return h.hexdigest()

                manifest.append(
                    {
                        "id": item["id"],
                        "image": str(img_path),
                        "image_sha256": (
                            _sha256(img_path) if img_path.exists() else None
                        ),
                        "metadata": str(meta_path),
                        "metadata_sha256": (
                            _sha256(meta_path) if meta_path.exists() else None
                        ),
                    }
                )

            manifest_path = self.output_dir / "manifest.json"
            with open(manifest_path, "w") as mf:
                json.dump(manifest, mf, indent=2)
        except Exception as e:
            print(f"Warning: Failed to write manifest: {e}")

#!/usr/bin/env python3
"""
Trait tracker module for NFT Generator
Tracks trait patterns and combinations to ensure uniqueness in generated NFTs.
"""

from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from itertools import combinations


class TraitTracker:
    """
    Tracks trait patterns and combinations to ensure uniqueness in generated NFTs.
    MAX_SIMILAR_COMBINATIONS controls how many times a specific 4-trait pattern
    can appear in the collection. A value of 1 means each 4-trait pattern must be unique.
    """

    def __init__(self, max_similar_combinations: int = 1):
        self.trait_patterns = defaultdict(int)
        self.bsh_combinations = set()
        self.MAX_SIMILAR_COMBINATIONS = max_similar_combinations

    def get_trait_pattern(
        self, traits: Dict[str, str]
    ) -> List[Tuple[Tuple[str, str], ...]]:
        """
        Generate trait patterns for uniqueness checking with optimized algorithm.

        Args:
            traits: Dictionary of trait types and values

        Returns:
            List of trait patterns (4-trait combinations)
        """
        patterns = []
        trait_items = list(traits.items())

        if len(trait_items) >= 4:
            # Use itertools.combinations for better performance
            for combo in combinations(trait_items, 4):
                pattern = tuple(sorted(combo))
                patterns.append(pattern)
        return patterns

    def get_bsh_combination(
        self, traits: Dict[str, str]
    ) -> Optional[Tuple[str, str, str]]:
        """
        Get BSH (Body, Eyewear, Head) combination for additional uniqueness check.

        Args:
            traits: Dictionary of trait types and values

        Returns:
            Tuple of (Body, Eyewear, Head) values or None if any are missing
        """
        if all(t in traits for t in ["Body", "Eyewear", "Head"]):
            return (traits["Body"], traits["Eyewear"], traits["Head"])
        return None

    def is_unique_enough(self, traits: Dict[str, str]) -> bool:
        """
        Check if the trait combination is unique enough based on configured constraints.

        Args:
            traits: Dictionary of trait types and values

        Returns:
            True if the combination is unique enough, False otherwise
        """
        bsh_combo = self.get_bsh_combination(traits)
        if bsh_combo and bsh_combo in self.bsh_combinations:
            return False

        patterns = self.get_trait_pattern(traits)
        return all(
            self.trait_patterns[pattern] < self.MAX_SIMILAR_COMBINATIONS
            for pattern in patterns
        )

    def update_patterns(self, traits: Dict[str, str]) -> None:
        """
        Update pattern tracking with new trait combination.

        Args:
            traits: Dictionary of trait types and values
        """
        patterns = self.get_trait_pattern(traits)
        for pattern in patterns:
            self.trait_patterns[pattern] += 1

        bsh_combo = self.get_bsh_combination(traits)
        if bsh_combo:
            self.bsh_combinations.add(bsh_combo)

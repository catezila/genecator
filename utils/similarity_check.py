#!/usr/bin/env python3
"""
Similarity Check Utility for NFT Generator
Find NFTs that share a specified number of identical trait values.
"""

import json
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm
import argparse


def load_metadata(file_path):
    """Load and validate metadata file"""
    try:
        with open(file_path, "r") as file:
            metadata = json.load(file)

        if not isinstance(metadata, list):
            raise ValueError("Metadata file should contain an array of NFT metadata")

        return metadata
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in {file_path}")
    except Exception as e:
        raise Exception(f"Error loading metadata: {str(e)}")


def get_trait_combinations(nft, similarity_threshold):
    """Extract trait combinations of specified size from an NFT"""
    traits = [(attr["trait_type"], attr["value"]) for attr in nft["attributes"]]
    
    # For simplicity in this implementation, we'll just use the whole trait set
    # In a more complex implementation, we could generate all combinations of size similarity_threshold
    return [tuple(sorted(traits))]


def find_similar_nfts(metadata, similarity_threshold):
    """
    Find NFTs that share a specified number of identical trait values.
    
    Args:
        metadata: List of NFT metadata
        similarity_threshold: Number of identical traits to consider NFTs similar
        
    Returns:
        Dictionary mapping trait combinations to lists of NFT indices
    """
    # Dictionary to store trait combinations and the NFTs that have them
    trait_combinations = defaultdict(list)
    
    print(f"Analyzing {len(metadata)} NFTs for similarities...")
    
    # Extract traits from each NFT
    nft_traits = []
    for index, nft in enumerate(metadata):
        traits = [(attr["trait_type"], attr["value"]) for attr in nft["attributes"]]
        nft_traits.append(traits)
    
    # Compare each NFT with every other NFT
    similar_pairs = defaultdict(list)
    
    for i in tqdm(range(len(nft_traits)), desc="Finding similarities"):
        for j in range(i + 1, len(nft_traits)):
            # Count common traits
            traits_i = set(nft_traits[i])
            traits_j = set(nft_traits[j])
            common_traits = traits_i.intersection(traits_j)
            
            # If they share enough traits, consider them similar
            if len(common_traits) >= similarity_threshold:
                similar_pairs[(i, j)] = list(common_traits)
    
    return similar_pairs


def find_similar_nfts_optimized(metadata, similarity_threshold):
    """
    Optimized version that groups NFTs by trait combinations.
    
    Args:
        metadata: List of NFT metadata
        similarity_threshold: Number of identical traits to consider NFTs similar
        
    Returns:
        Dictionary mapping trait combinations to lists of NFT indices
    """
    # Dictionary to store which NFTs have each trait
    trait_to_nfts = defaultdict(list)
    
    print(f"Indexing {len(metadata)} NFTs by traits...")
    
    # Index NFTs by their traits
    for index, nft in enumerate(tqdm(metadata, desc="Indexing")):
        for attr in nft["attributes"]:
            trait_key = (attr["trait_type"], attr["value"])
            trait_to_nfts[trait_key].append(index)
    
    # Find NFTs that share traits
    similar_groups = defaultdict(set)
    
    print("Finding similar groups...")
    for trait_key, nft_indices in tqdm(trait_to_nfts.items(), desc="Grouping"):
        # For each trait, add all NFTs with that trait to each other's similar groups
        for i in range(len(nft_indices)):
            for j in range(i + 1, len(nft_indices)):
                idx1, idx2 = nft_indices[i], nft_indices[j]
                similar_groups[(idx1, idx2)].add(trait_key)
    
    # Filter groups that meet the similarity threshold
    result = {pair: list(traits) for pair, traits in similar_groups.items() 
              if len(traits) >= similarity_threshold}
    
    return result


def print_similarity_report(similar_nfts, metadata, similarity_threshold):
    """Print a detailed report of similar NFTs"""
    if not similar_nfts:
        print(f"\n✅ No NFTs found with {similarity_threshold} or more identical traits!")
        return
    
    print(f"\n=== Similarity Report (≥{similarity_threshold} identical traits) ===")
    print(f"Found {len(similar_nfts)} pairs of similar NFTs\n")
    
    # Sort by number of common traits (descending)
    sorted_similar = sorted(similar_nfts.items(), key=lambda x: len(x[1]), reverse=True)
    
    for i, ((nft1_idx, nft2_idx), common_traits) in enumerate(sorted_similar[:20]):  # Show top 20
        nft1 = metadata[nft1_idx]
        nft2 = metadata[nft2_idx]
        
        print(f"Pair {i+1}: NFT #{nft1['id']} and NFT #{nft2['id']} share {len(common_traits)} traits:")
        for trait_type, trait_value in common_traits:
            print(f"  • {trait_type}: {trait_value}")
        
        print()
    
    if len(sorted_similar) > 20:
        print(f"... and {len(sorted_similar) - 20} more pairs")


def save_similarity_report(similar_nfts, metadata, output_file):
    """Save detailed similarity report to JSON file"""
    report = {
        "total_similar_pairs": len(similar_nfts),
        "similar_pairs": []
    }
    
    for (nft1_idx, nft2_idx), common_traits in similar_nfts.items():
        nft1 = metadata[nft1_idx]
        nft2 = metadata[nft2_idx]
        
        pair_info = {
            "nft1_id": nft1["id"],
            "nft2_id": nft2["id"],
            "common_traits": [
                {"trait_type": trait_type, "trait_value": trait_value}
                for trait_type, trait_value in common_traits
            ],
            "similarity_count": len(common_traits)
        }
        report["similar_pairs"].append(pair_info)
    
    # Sort by similarity count
    report["similar_pairs"].sort(key=lambda x: x["similarity_count"], reverse=True)
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Find similar NFTs based on shared traits")
    parser.add_argument(
        "-t", "--threshold", 
        type=int, 
        default=3, 
        help="Minimum number of identical traits to consider NFTs similar (default: 3)"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Metadata file to analyze (default: looks for combined_metadata.json or scans metadata directory)"
    )
    
    args = parser.parse_args()
    
    try:
        # Determine which metadata file to use
        if args.file:
            file_path = args.file
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Specified file not found: {file_path}")
        else:
            # Support multiple file locations
            file_paths = [
                "./output/metadata/combined_metadata.json",
                "./output/combined_metadata.json",
                "collection_metadata.json"
            ]
            file_path = next((p for p in file_paths if Path(p).exists()), None)
            
            if not file_path:
                # If no combined file found, try to load individual files
                metadata_dir = Path("./output/metadata/")
                if metadata_dir.exists():
                    print("Loading individual metadata files...")
                    metadata_files = list(metadata_dir.glob("*.json"))
                    metadata_files = [f for f in metadata_files if f.name != "combined_metadata.json"]
                    
                    if metadata_files:
                        print(f"Found {len(metadata_files)} metadata files. Loading...")
                        metadata = []
                        for meta_file in tqdm(metadata_files[:100], desc="Loading"):  # Limit to 100 for demo
                            try:
                                with open(meta_file, "r") as f:
                                    metadata.append(json.load(f))
                            except Exception as e:
                                print(f"Warning: Could not load {meta_file}: {e}")
                        
                        # Save combined version for future use
                        combined_path = "./output/metadata/combined_metadata.json"
                        with open(combined_path, "w") as f:
                            json.dump(metadata, f, indent=2)
                        file_path = combined_path
                        print(f"Created combined metadata file at {combined_path}")
                    else:
                        raise FileNotFoundError(
                            "No metadata files found. Please ensure metadata exists in output/metadata/"
                        )
                else:
                    raise FileNotFoundError(
                        "Metadata directory not found. Please run generation first."
                    )
            else:
                print(f"Found metadata file: {file_path}")
        
        print(f"Loading metadata from {file_path}...")
        metadata = load_metadata(file_path)
        
        print(f"Checking {len(metadata)} NFTs for similarities (threshold: {args.threshold})...")
        similar_nfts = find_similar_nfts_optimized(metadata, args.threshold)
        
        print_similarity_report(similar_nfts, metadata, args.threshold)
        
        # Save detailed report
        report_file = f"similarity_report_threshold_{args.threshold}.json"
        save_similarity_report(similar_nfts, metadata, report_file)
        
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()

import json
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm


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


def analyze_traits(metadata):
    """Analyze trait distributions"""
    trait_counts = defaultdict(lambda: defaultdict(int))
    for nft in metadata:
        for attr in nft["attributes"]:
            trait_type = attr["trait_type"]
            value = attr["value"]
            trait_counts[trait_type][value] += 1
    return trait_counts


def check_duplicates(metadata):
    hash_dict = defaultdict(list)
    traits_dict = defaultdict(list)

    # Track counts for statistics
    total_nfts = len(metadata)
    stats = {
        "total_nfts": total_nfts,
        "unique_hashes": 0,
        "unique_trait_combinations": 0,
    }

    print("Analyzing NFTs...")
    for index, nft in enumerate(tqdm(metadata), 1):
        # Check hash duplicates
        if "hash" in nft:
            nft_hash = nft["hash"]
            hash_dict[nft_hash].append(index)

        # Check trait combination duplicates
        nft_traits = tuple(
            sorted((attr["trait_type"], attr["value"]) for attr in nft["attributes"])
        )
        traits_dict[nft_traits].append(index)

    # Find duplicates
    duplicate_hashes = {
        hash_: indices for hash_, indices in hash_dict.items() if len(indices) > 1
    }
    duplicate_traits = {
        traits: indices for traits, indices in traits_dict.items() if len(indices) > 1
    }

    # Update statistics
    stats["unique_hashes"] = len(hash_dict)
    stats["unique_trait_combinations"] = len(traits_dict)

    # Generate report
    print("\n=== Duplicate Analysis Report ===")

    if duplicate_hashes:
        print("\nDuplicate hashes found:")
        for hash_, indices in duplicate_hashes.items():
            print(f"\nHash: {hash_}")
            print(f"Found in NFTs: {', '.join(map(str, indices))}")
            # Show traits for these NFTs
            for idx in indices:
                nft = metadata[idx - 1]
                print(f"\nNFT #{idx} traits:")
                for attr in nft["attributes"]:
                    print(f"  {attr['trait_type']}: {attr['value']}")

    if duplicate_traits:
        print("\nDuplicate trait combinations found:")
        for traits, indices in duplicate_traits.items():
            print("\nTrait combination:")
            for trait_type, value in traits:
                print(f"  {trait_type}: {value}")
            print(f"Found in NFTs: {', '.join(map(str, indices))}")

    if not duplicate_hashes and not duplicate_traits:
        print("\nNo duplicates found!")

    # Print statistics
    print("\n=== Collection Statistics ===")
    print(f"Total NFTs: {stats['total_nfts']}")
    print(f"Unique hashes: {stats['unique_hashes']}")
    print(f"Unique trait combinations: {stats['unique_trait_combinations']}")

    return duplicate_hashes, duplicate_traits, stats


def main():
    try:
        # Support both file names
        file_paths = [
            "collection_metadata.json", 
            "./output/combined_metadata.json"
        ]
        file_path = next((p for p in file_paths if Path(p).exists()), None)

        if not file_path:
            raise FileNotFoundError(
                "Metadata file not found. Please ensure either 'collection_metadata.json' or 'combine_metadata.json' exists."
            )

        print(f"Loading metadata from {file_path}...")
        metadata = load_metadata(file_path)

        print(f"\nChecking {len(metadata)} NFTs for duplicates...")
        duplicate_hashes, duplicate_traits, stats = check_duplicates(metadata)

        # Save detailed report
        report = {
            "statistics": stats,
            "duplicate_hashes": {str(k): v for k, v in duplicate_hashes.items()},
            "duplicate_traits": {str(k): v for k, v in duplicate_traits.items()},
        }

        with open("duplicate_check_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print("\nDetailed report saved to duplicate_check_report.json")

    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()

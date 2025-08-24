import json
from collections import defaultdict
import csv
from itertools import combinations
from pathlib import Path


def load_metadata(file_path):
    """Load metadata file"""
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"Error loading metadata: {str(e)}")


def find_similar_nfts(metadata, min_common_traits=3):
    """Find NFTs with similar trait combinations, including 'None' values"""
    trait_combinations = defaultdict(list)

    for nft in metadata:
        # Include all traits, including 'None' values
        traits = sorted(
            (attr["trait_type"], attr["value"]) for attr in nft["attributes"]
        )

        # Generate combinations of the specified size
        for combo in combinations(traits, min_common_traits):
            # Use the NFT's ID instead of image_name
            trait_combinations[combo].append(str(nft["id"]))

    # Return only combinations that appear in multiple NFTs
    return {
        combo: images
        for combo, images in sorted(trait_combinations.items())
        if len(images) > 1
    }


def save_to_csv(similar_nfts, output_file):
    """Save results to CSV"""
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Common Traits", "Image Names", "Count"])

        for traits, images in similar_nfts.items():
            trait_str = "\n".join([f"{trait}: {value}" for trait, value in traits])
            image_str = "\n".join(sorted(images))
            count = len(images)
            writer.writerow([trait_str, image_str, count])


def main():
    try:
        # Support both file names
        file_paths = ["collection_metadata.json", "combine_metadata.json"]
        file_path = next((p for p in file_paths if Path(p).exists()), None)

        if not file_path:
            raise FileNotFoundError(
                "Metadata file not found. Please ensure either 'collection_metadata.json' or 'combine_metadata.json' exists."
            )

        output_file = "similar_traits.csv"
        min_common_traits = 4

        print(f"Loading metadata from {file_path}...")
        metadata = load_metadata(file_path)

        print(f"Scanning for NFTs with {min_common_traits} or more traits in common...")
        similar_nfts = find_similar_nfts(metadata, min_common_traits)

        print(f"Saving results to {output_file}...")
        save_to_csv(similar_nfts, output_file)

        print(f"Found {len(similar_nfts)} trait combinations with similar NFTs.")
        print(f"Results have been saved to {output_file}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()

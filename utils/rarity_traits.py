import json
from collections import defaultdict
import csv
from pathlib import Path


def load_metadata(file_path):
    """Load metadata file"""
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"Error loading metadata: {str(e)}")


def calculate_trait_rarity(metadata):
    """Calculate rarity for each trait and value"""
    total_nfts = len(metadata)
    trait_counts = defaultdict(lambda: defaultdict(int))
    nft_rarity_scores = []

    # Count occurrences of each trait value
    print("Counting trait occurrences...")
    for nft in metadata:
        for trait in nft["attributes"]:
            trait_type = trait["trait_type"]
            trait_value = trait["value"]
            trait_counts[trait_type][trait_value] += 1

    # Calculate rarity scores
    trait_rarity = {}
    for trait_type, values in trait_counts.items():
        trait_rarity[trait_type] = {}
        for value, count in values.items():
            rarity_score = 1 / (count / total_nfts)
            trait_rarity[trait_type][value] = {
                "count": count,
                "percentage": (count / total_nfts) * 100,
                "rarity_score": rarity_score,
            }

    # Calculate rarity score for each NFT
    print("\nCalculating NFT rarity scores...")
    for nft in metadata:
        nft_score = 0
        traits_info = []

        for trait in nft["attributes"]:
            trait_type = trait["trait_type"]
            trait_value = trait["value"]
            rarity_info = trait_rarity[trait_type][trait_value]

            nft_score += rarity_info["rarity_score"]
            traits_info.append(
                {
                    "trait_type": trait_type,
                    "value": trait_value,
                    "count": rarity_info["count"],
                    "percentage": rarity_info["percentage"],
                    "rarity_score": rarity_info["rarity_score"],
                }
            )

        nft_rarity_scores.append(
            {"id": nft["id"], "traits": traits_info, "total_score": nft_score}
        )

    return trait_rarity, sorted(
        nft_rarity_scores, key=lambda x: x["total_score"], reverse=True
    )


def save_trait_rarity(trait_rarity, output_file):
    """Save trait rarity analysis to CSV"""
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Trait Type", "Value", "Count", "Percentage", "Rarity Score"])

        for trait_type, values in trait_rarity.items():
            # Sort values by rarity score in descending order
            sorted_values = sorted(
                values.items(), key=lambda x: x[1]["rarity_score"], reverse=True
            )

            for value, stats in sorted_values:
                writer.writerow(
                    [
                        trait_type,
                        value,
                        stats["count"],
                        f"{stats['percentage']:.2f}%",
                        f"{stats['rarity_score']:.2f}",
                    ]
                )


def save_nft_rarity(nft_rarity_scores, output_file):
    """Save NFT rarity rankings to CSV"""
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "NFT ID", "Total Rarity Score", "Trait Breakdown"])

        for rank, nft in enumerate(nft_rarity_scores, 1):
            trait_breakdown = "\n".join(
                [
                    f"{t['trait_type']}: {t['value']} ({t['percentage']:.2f}%)"
                    for t in nft["traits"]
                ]
            )

            writer.writerow(
                [rank, nft["id"], f"{nft['total_score']:.2f}", trait_breakdown]
            )


def main():
    try:
        # Support both file names
        file_paths = ["collection_metadata.json", "combine_metadata.json"]
        file_path = next((p for p in file_paths if Path(p).exists()), None)

        if not file_path:
            raise FileNotFoundError(
                "Metadata file not found. Please ensure either 'collection_metadata.json' or 'combine_metadata.json' exists."
            )

        print(f"Loading metadata from {file_path}...")
        metadata = load_metadata(file_path)
        total_nfts = len(metadata)

        print(f"\nAnalyzing rarity for {total_nfts} NFTs...")
        trait_rarity, nft_rarity_scores = calculate_trait_rarity(metadata)

        # Save trait rarity analysis
        trait_output = "trait_rarity.csv"
        print(f"\nSaving trait rarity analysis to {trait_output}...")
        save_trait_rarity(trait_rarity, trait_output)

        # Save NFT rarity rankings
        nft_output = "nft_rarity_ranking.csv"
        print(f"Saving NFT rarity rankings to {nft_output}...")
        save_nft_rarity(nft_rarity_scores, nft_output)

        # Print summary statistics
        print("\n=== Rarity Analysis Summary ===")
        print(f"Total NFTs analyzed: {total_nfts}")
        print(f"Number of trait types: {len(trait_rarity)}")

        print("\nRarest trait per category:")
        for trait_type, values in trait_rarity.items():
            rarest = max(values.items(), key=lambda x: x[1]["rarity_score"])
            print(f"{trait_type}: {rarest[0]} ({rarest[1]['percentage']:.2f}%)")

        print("\nTop 5 rarest NFTs:")
        for i, nft in enumerate(nft_rarity_scores[:5], 1):
            print(f"{i}. NFT #{nft['id']} - Score: {nft['total_score']:.2f}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()

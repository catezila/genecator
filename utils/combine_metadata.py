import json
from tqdm import tqdm
from pathlib import Path


def verify_metadata(metadata):
    """Verify that metadata has all required fields"""
    required_fields = [
        "name",
        "description",
        "image",
        "attributes",
    ]  # Updated required fields for OpenSea
    missing_fields = [field for field in required_fields if field not in metadata]
    return len(missing_fields) == 0, missing_fields


def combine_metadata(input_folder, output_file):
    combined_metadata = []
    input_path = Path(input_folder)

    if not input_path.exists():
        raise Exception(f"Input folder {input_folder} not found!")

    # Get all JSON files in the input folder
    json_files = list(input_path.glob("*.json"))

    if not json_files:
        raise Exception(f"No JSON files found in {input_folder}")

    # Sort the files numerically
    json_files.sort(key=lambda x: int(x.stem))

    print(f"Combining {len(json_files)} metadata files...")

    # Track any files with issues
    problematic_files = []

    # Track trait statistics
    trait_stats = {}
    total_nfts = len(json_files)

    # Iterate through each JSON file
    for file_path in tqdm(json_files, desc="Processing"):
        try:
            with open(file_path, "r") as file:
                metadata = json.load(file)

            # Verify metadata structure
            is_valid, missing_fields = verify_metadata(metadata)
            if not is_valid:
                problematic_files.append(
                    f"{file_path.name} (Missing fields: {', '.join(missing_fields)})"
                )
                continue

            # Update trait statistics
            for trait in metadata.get("attributes", []):
                trait_type = trait["trait_type"]
                trait_value = trait["value"]

                if trait_type not in trait_stats:
                    trait_stats[trait_type] = {}

                if trait_value not in trait_stats[trait_type]:
                    trait_stats[trait_type][trait_value] = 0

                trait_stats[trait_type][trait_value] += 1

            combined_metadata.append(metadata)

        except json.JSONDecodeError:
            problematic_files.append(f"{file_path.name} (Invalid JSON)")
        except Exception as e:
            problematic_files.append(f"{file_path.name} (Error: {str(e)})")

    if problematic_files:
        print("\nWarning: Issues found in some files:")
        for file in problematic_files:
            print(f"- {file}")

    if not combined_metadata:
        raise Exception("No valid metadata files to combine!")

    # Create output directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the combined metadata to the output file
    with open(output_path, "w") as outfile:
        json.dump(combined_metadata, outfile, indent=2)

    # Save trait statistics
    stats_output = output_path.with_name("collection_stats.json")
    collection_stats = {"total_items": total_nfts, "trait_counts": trait_stats}

    with open(stats_output, "w") as statsfile:
        json.dump(collection_stats, statsfile, indent=2)

    print(f"\nSuccessfully combined {len(combined_metadata)} metadata files")
    print(f"Combined metadata saved to {output_file}")
    print(f"Collection statistics saved to {stats_output}")

    # Print trait statistics
    print("\nTrait Statistics:")
    for trait_type, values in trait_stats.items():
        print(f"\n{trait_type}:")
        for value, count in values.items():
            percentage = (count / total_nfts) * 100
            print(f"  {value}: {count} ({percentage:.2f}%)")


def main():
    try:
        input_folder = "output/metadata"
        output_file = "output/combined_metadata.json"
        combine_metadata(input_folder, output_file)
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()

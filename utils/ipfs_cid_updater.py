import json
import os
from pathlib import Path
from tqdm import tqdm


def update_ipfs_cid(metadata_dir, output_dir, ipfs_cid):
    """
    Update all metadata files in the directory with the actual IPFS CID
    """
    metadata_path = Path(metadata_dir)
    output_path = Path(output_dir)

    if not metadata_path.exists():
        raise Exception(f"Directory {metadata_dir} not found!")

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Get all JSON files
    json_files = list(metadata_path.glob("*.json"))
    total_files = len(json_files)

    print(f"Found {total_files} metadata files to update")

    # Update each file
    for json_file in tqdm(json_files, desc="Updating metadata files"):
        # Read the metadata file
        with open(json_file, "r") as f:
            metadata = json.load(f)

        # Update the IPFS CID in the image URL
        # Extract the actual image filename from the current image URL
        current_image = metadata.get("image", "")
        image_filename = current_image.split("/")[-1] if "/" in current_image else f"{json_file.stem}.png"
        metadata["image"] = f"{ipfs_cid}/{image_filename}"

        # Define the output file path
        output_file = output_path / json_file.name

        # Save the updated metadata
        with open(output_file, "w") as f:
            json.dump(metadata, f, indent=2)


def main():
    # Directory containing your metadata JSON files
    metadata_dir = "output/metadata"
    output_dir = "upload/metadata"

    # Get IPFS CID from user
    print("\nPlease enter your IPFS CID for the images folder:")
    ipfs_cid = input().strip()

    try:
        update_ipfs_cid(metadata_dir, output_dir, ipfs_cid)
        print(
            f"\nSuccess! All metadata files have been updated and saved to {output_dir}."
        )

        # Show sample of updated metadata
        print(f"\nChecking a sample metadata file (1.json) in {output_dir}:")
        sample_file_path = os.path.join(output_dir, "1.json")
        if os.path.exists(sample_file_path):
            with open(sample_file_path, "r") as f:
                sample = json.load(f)
                print(f"Sample image URL: {sample['image']}")
        else:
            print(f"Sample file {sample_file_path} not found.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()

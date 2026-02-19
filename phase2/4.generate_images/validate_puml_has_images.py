#!/usr/bin/env python3
"""
Script to validate that PlantUML files have corresponding PNG images.

This script checks if each .puml file has at least one corresponding PNG image.
The matching logic handles:
1. Exact match: diagram.puml -> diagram.png
2. Multi-page match: diagram.puml -> diagram_001.png, diagram_002.png, etc. (@newpage split)

Usage:
    python validate_puml_has_images.py <puml_dir> <images_dir>

Output:
    Creates puml_validated/ directory with:
    - valid/: PUML files with corresponding .png images
    - invalid/: PUML files without corresponding .png images
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Set, Tuple


def get_image_stems(images_dir: Path) -> Set[str]:
    """
    Get all image filename stems from the directory.

    Args:
        images_dir: Path to directory containing image files

    Returns:
        Set of base filenames without extension
    """
    if not images_dir.exists():
        print(f"Error: Directory '{images_dir}' not found", file=sys.stderr)
        sys.exit(1)

    image_extensions = {'.png', '.jpg', '.jpeg', '.svg', '.gif', '.bmp'}
    image_stems = set()

    for ext in image_extensions:
        for img_file in images_dir.glob(f"*{ext}"):
            image_stems.add(img_file.stem)

    return image_stems


def check_puml_has_image(puml_stem: str, image_stems: Set[str]) -> bool:
    """
    Check if a PUML file has at least one corresponding image.

    Matching logic:
    1. Exact match: diagram.puml -> diagram.png
    2. Multi-page pattern: diagram.puml -> diagram_001.png, diagram_002.png, etc.

    Args:
        puml_stem: PUML filename without extension (e.g., "diagram")
        image_stems: Set of all image file stems

    Returns:
        True if at least one corresponding image exists, False otherwise
    """
    # Check exact match first
    if puml_stem in image_stems:
        return True

    # Check for multi-page pattern: {puml_name}_001, {puml_name}_002, etc.
    # We only need to find at least ONE matching image
    for img_stem in image_stems:
        # Check if image starts with puml_stem followed by _XXX
        if img_stem.startswith(puml_stem + "_"):
            # Extract suffix after puml_stem_
            suffix = img_stem[len(puml_stem) + 1:]
            # Check if suffix is exactly 3 digits
            if suffix.isdigit() and len(suffix) == 3:
                return True

    return False


def validate_puml_files(puml_dir: Path, images_dir: Path, output_dir: Path) -> Tuple[int, int]:
    """
    Validate PUML files and organize them into valid/invalid directories.

    Args:
        puml_dir: Directory containing .puml files
        images_dir: Directory containing image files
        output_dir: Output directory for organized files

    Returns:
        Tuple of (valid_count, invalid_count)
    """
    if not puml_dir.exists():
        print(f"Error: Directory '{puml_dir}' not found", file=sys.stderr)
        sys.exit(1)

    # Create output directories
    valid_dir = output_dir / "valid"
    invalid_dir = output_dir / "invalid"
    valid_dir.mkdir(parents=True, exist_ok=True)
    invalid_dir.mkdir(parents=True, exist_ok=True)

    # Get all image stems
    print("Loading image filenames...", file=sys.stderr)
    image_stems = get_image_stems(images_dir)
    print(f"Found {len(image_stems)} image files", file=sys.stderr)

    # Get all .puml files
    puml_files = list(puml_dir.glob("*.puml"))
    total_puml = len(puml_files)
    print(f"Found {total_puml} .puml files", file=sys.stderr)
    print("Validating PUML files...", file=sys.stderr)
    print("-" * 60, file=sys.stderr)

    valid_count = 0
    invalid_count = 0

    for idx, puml_file in enumerate(puml_files, 1):
        puml_stem = puml_file.stem

        # Check if corresponding image(s) exist
        has_image = check_puml_has_image(puml_stem, image_stems)

        # Copy to appropriate directory
        if has_image:
            dest = valid_dir / puml_file.name
            shutil.copy2(puml_file, dest)
            valid_count += 1
        else:
            dest = invalid_dir / puml_file.name
            shutil.copy2(puml_file, dest)
            invalid_count += 1

        # Print progress every 1000 files
        if idx % 1000 == 0:
            percentage = (idx / total_puml) * 100
            print(f"Processed {idx:,}/{total_puml:,} ({percentage:.1f}%) - "
                  f"Valid: {valid_count:,}, Invalid: {invalid_count:,}",
                  file=sys.stderr)

    return valid_count, invalid_count


def main():
    parser = argparse.ArgumentParser(
        description="Validate that PlantUML files have corresponding PNG images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_puml_has_images.py ./puml ./images
  python validate_puml_has_images.py /path/to/puml /path/to/images

Output Structure:
  puml_validated/
    ├── valid/      # PUML files with corresponding images
    └── invalid/    # PUML files without corresponding images
        """
    )

    parser.add_argument(
        "puml_dir",
        help="Directory containing .puml files"
    )

    parser.add_argument(
        "images_dir",
        help="Directory containing image files"
    )

    parser.add_argument(
        "-o", "--output",
        default="puml_validated",
        help="Output directory (default: puml_validated)"
    )

    args = parser.parse_args()

    # Convert to Path objects
    puml_dir = Path(args.puml_dir).resolve()
    images_dir = Path(args.images_dir).resolve()
    output_dir = Path(args.output).resolve()

    print("=" * 60, file=sys.stderr)
    print("PlantUML-to-Image Validation", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"PUML directory: {puml_dir}", file=sys.stderr)
    print(f"Images directory: {images_dir}", file=sys.stderr)
    print(f"Output directory: {output_dir}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Validate PUML files
    valid_count, invalid_count = validate_puml_files(puml_dir, images_dir, output_dir)

    # Print summary
    total = valid_count + invalid_count
    valid_percentage = (valid_count / total * 100) if total > 0 else 0
    invalid_percentage = (invalid_count / total * 100) if total > 0 else 0

    print("\n" + "=" * 60, file=sys.stderr)
    print("Validation Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total PUML files processed: {total:,}", file=sys.stderr)
    print(f"Valid PUML files:   {valid_count:,} ({valid_percentage:.2f}%)", file=sys.stderr)
    print(f"Invalid PUML files: {invalid_count:,} ({invalid_percentage:.2f}%)", file=sys.stderr)
    print(f"\nValid files saved to:   {output_dir / 'valid'}", file=sys.stderr)
    print(f"Invalid files saved to: {output_dir / 'invalid'}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()

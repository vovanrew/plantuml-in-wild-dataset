#!/usr/bin/env python3
"""
PlantUML Validation File Preparation Script
Decodes base64-encoded PlantUML content and creates .puml files for validation

Part of Phase 3: Dataset Building and Validation
Author: Generated for WoC PlantUML Dataset
Date: 2025-10-30
"""

import argparse
import base64
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not installed. Install with: pip install tqdm")
    tqdm = None


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_INPUT = "../phase2/filtered_plantuml_content.txt"
DEFAULT_OUTPUT_DIR = Path("./puml")
DEFAULT_METADATA_FILE = Path("./metadata/blob_metadata.json")
DEFAULT_BATCH_SIZE = 10000  # Files per batch directory

# =============================================================================
# Core Functions
# =============================================================================

def parse_line(line: str, line_num: int) -> Tuple[bool, str, str, str, str]:
    """
    Parse a single line from the input file.

    Args:
        line: Input line in format: blob_id;file_path;base64_content
        line_num: Line number for error reporting

    Returns:
        Tuple of (success, blob_id, file_path, content, error_msg)
    """
    try:
        parts = line.strip().split(';', 2)
        if len(parts) != 3:
            return (False, "", "", "", f"Line {line_num}: Malformed line (expected 3 parts, got {len(parts)})")

        blob_id, file_path, b64_content = parts

        # Validate blob_id (should be 40 hex characters)
        if len(blob_id) != 40 or not all(c in '0123456789abcdef' for c in blob_id.lower()):
            return (False, blob_id, file_path, "", f"Line {line_num}: Invalid blob_id format")

        # Decode base64 content
        try:
            content_bytes = base64.b64decode(b64_content)
            content = content_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            return (False, blob_id, file_path, "", f"Line {line_num}: Base64 decode error: {str(e)}")

        # Basic validation: check for PlantUML markers
        if '@startuml' not in content.lower() or '@enduml' not in content.lower():
            return (False, blob_id, file_path, "", f"Line {line_num}: Missing PlantUML markers")

        return (True, blob_id, file_path, content, "")

    except Exception as e:
        return (False, "", "", "", f"Line {line_num}: Unexpected error: {str(e)}")


def create_puml_file(output_dir: Path, blob_id: str, content: str, file_path: str) -> bool:
    """
    Create a .puml file with the given content.

    Args:
        output_dir: Directory to write the file
        blob_id: Blob ID (used as filename)
        content: PlantUML content
        file_path: Original file path (added as comment)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create file path
        file_out = output_dir / f"{blob_id}.puml"

        # Write content with metadata comment
        with open(file_out, 'w', encoding='utf-8') as f:
            # Add metadata as comment at the top
            f.write(f"' Blob ID: {blob_id}\n")
            f.write(f"' Original Path: {file_path}\n")
            f.write(f"' Source: World of Code\n")
            f.write("\n")
            f.write(content)

            # Ensure file ends with newline
            if not content.endswith('\n'):
                f.write('\n')

        return True

    except Exception as e:
        logging.error(f"Failed to write file for blob {blob_id}: {e}")
        return False


# =============================================================================
# Main Processing Function
# =============================================================================

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Prepare PlantUML files for validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default settings
  python3 generate_puml_from_base64.py

  # Custom input and batch size
  python3 generate_puml_from_base64.py -i input.txt -b 5000

  # Process all files without batching (single directory)
  python3 generate_puml_from_base64.py --no-batch

  # Verbose output
  python3 generate_puml_from_base64.py -v
        """
    )
    parser.add_argument(
        "-i", "--input",
        default=DEFAULT_INPUT,
        help=f"Input file with PlantUML content (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for validation files (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "-m", "--metadata-file",
        type=Path,
        default=DEFAULT_METADATA_FILE,
        help=f"Metadata output file (default: {DEFAULT_METADATA_FILE})"
    )
    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of files per batch directory (default: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--no-batch",
        action="store_true",
        help="Process all files into a single directory without batching"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse input without creating files (for testing)"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info("=" * 60)
    logging.info("PlantUML Validation File Preparation")
    logging.info("=" * 60)
    logging.info(f"Input file: {args.input}")
    logging.info(f"Output directory: {args.output_dir}")
    if args.no_batch:
        logging.info("Batch mode: DISABLED (all files in single directory)")
    else:
        logging.info(f"Batch size: {args.batch_size} files/directory")
    logging.info(f"Metadata file: {args.metadata_file}")
    logging.info(f"Dry run: {args.dry_run}")
    logging.info("=" * 60)

    start_time = time.time()

    # Count total lines
    logging.info("Counting total lines...")
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
        logging.info(f"Total lines to process: {total_lines:,}")
    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input}")
        return 1
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        return 1

    # Statistics
    stats = {
        "total_lines": total_lines,
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "batches_created": 0,
        "errors": []
    }

    # Metadata storage
    metadata: Dict[str, Dict] = {}

    # Create output directories
    if not args.dry_run:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        args.metadata_file.parent.mkdir(parents=True, exist_ok=True)

    # Process lines
    logging.info("Processing lines and creating .puml files...")

    current_batch = 0
    files_in_batch = 0

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            # Initialize progress bar
            iterator = enumerate(f, start=1)
            if tqdm:
                iterator = tqdm(iterator, total=total_lines, desc="Processing", unit="line")

            for line_num, line in iterator:
                if not line.strip():
                    continue

                # Parse line
                success, blob_id, file_path, content, error_msg = parse_line(line, line_num)

                stats["processed"] += 1

                if not success:
                    stats["failed"] += 1
                    if args.verbose and error_msg:
                        logging.debug(error_msg)
                    # Store first 100 errors
                    if len(stats["errors"]) < 100:
                        stats["errors"].append(error_msg)
                    continue

                # Determine batch directory
                if args.no_batch:
                    # No batching: use output directory directly
                    batch_dir = args.output_dir
                    current_batch = 1  # Single "batch"
                else:
                    # Batching enabled
                    if files_in_batch == 0 or files_in_batch >= args.batch_size:
                        current_batch += 1
                        files_in_batch = 0
                    batch_dir = args.output_dir / f"batch_{current_batch:04d}"

                # Create .puml file
                if not args.dry_run:
                    if create_puml_file(batch_dir, blob_id, content, file_path):
                        stats["successful"] += 1
                        files_in_batch += 1

                        # Store metadata
                        metadata[blob_id] = {
                            "file_path": file_path,
                            "batch": current_batch if not args.no_batch else None,
                            "puml_file": str(batch_dir / f"{blob_id}.puml")
                        }
                    else:
                        stats["failed"] += 1
                else:
                    # Dry run: just count
                    stats["successful"] += 1
                    files_in_batch += 1

                # Update progress bar or print periodic updates
                if tqdm and hasattr(iterator, 'set_postfix'):
                    postfix = {
                        "success": stats["successful"],
                        "failed": stats["failed"]
                    }
                    if not args.no_batch:
                        postfix["batch"] = current_batch
                    iterator.set_postfix(postfix)
                elif not tqdm and stats["successful"] % 1000 == 0:
                    # Fallback: print progress every 1000 successful files
                    progress_pct = (stats["processed"] / total_lines * 100) if total_lines > 0 else 0
                    logging.info(f"Progress: {stats['successful']:,} files created ({stats['processed']:,}/{total_lines:,} lines, {progress_pct:.1f}%)")

            if tqdm and hasattr(iterator, 'close'):
                iterator.close()

    except KeyboardInterrupt:
        logging.warning("Interrupted by user. Partial results saved.")
        return 1
    except Exception as e:
        logging.error(f"Error during processing: {e}")
        return 1

    stats["batches_created"] = current_batch

    # Save metadata
    if not args.dry_run:
        logging.info("Saving metadata...")
        try:
            with open(args.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logging.info(f"Metadata saved to: {args.metadata_file}")
        except Exception as e:
            logging.error(f"Failed to save metadata: {e}")

    # Calculate timing
    end_time = time.time()
    duration = end_time - start_time

    # Print summary
    logging.info("=" * 60)
    logging.info("Processing Complete!")
    logging.info("=" * 60)
    logging.info(f"Total time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logging.info(f"Processing speed: {stats['processed']/duration:.1f} lines/second")
    logging.info("")
    logging.info("Results:")
    logging.info(f"  Total lines:        {stats['total_lines']:,}")
    logging.info(f"  Processed:          {stats['processed']:,}")
    logging.info(f"  Successful:         {stats['successful']:,} ({stats['successful']/stats['processed']*100:.1f}%)")
    logging.info(f"  Failed:             {stats['failed']:,} ({stats['failed']/stats['processed']*100:.1f}%)")
    if not args.no_batch:
        logging.info(f"  Batches created:    {stats['batches_created']}")
        logging.info(f"  Avg files/batch:    {stats['successful']/stats['batches_created']:.0f}" if stats['batches_created'] > 0 else "  Avg files/batch:    N/A")
    logging.info("")

    if not args.dry_run:
        logging.info("Output structure:")
        logging.info(f"  Validation files:   {args.output_dir}/")
        logging.info(f"  Metadata:           {args.metadata_file}")
        logging.info("")
        logging.info("Next step:")
        logging.info("  Run: ./validate_syntax.sh")

    logging.info("=" * 60)

    # Show error samples if any
    if stats["errors"]:
        logging.info("")
        logging.info(f"Sample errors (first 10 of {len(stats['errors'])}):")
        logging.info("-" * 60)
        for error in stats["errors"][:10]:
            logging.info(f"  {error}")
        logging.info("-" * 60)

    return 0


if __name__ == "__main__":
    exit(main())

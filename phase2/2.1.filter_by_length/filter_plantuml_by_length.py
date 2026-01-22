#!/usr/bin/env python3
"""
PlantUML Content Filter Script
Filters out PlantUML files with fewer than N non-empty lines

This script is part of Phase 2, Step 6 of the PlantUML Dataset creation roadmap:
performing preliminary cleaning and basic filtering.

Author: Generated for WoC PlantUML Dataset
Date: 2025-10-27
"""

import argparse
import base64
import gzip
import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Tuple, Optional

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not installed. Install with: pip install tqdm")
    tqdm = None


# =============================================================================
# Configuration
# =============================================================================

# Default paths relative to current directory
INPUT_FILE = "valid_plantuml_content.gz"
OUTPUT_FILE = Path("filtered_plantuml_content.txt")
STATS_FILE = Path("filter_stats.json")
MIN_LINES = 5


# =============================================================================
# Core Functions
# =============================================================================

def count_non_empty_lines(content: str) -> int:
    """
    Count non-empty lines in content.

    A line is considered non-empty if it contains at least one non-whitespace character.

    Args:
        content: The text content to analyze

    Returns:
        Number of non-empty lines
    """
    lines = content.split('\n')
    non_empty_count = sum(1 for line in lines if line.strip())
    return non_empty_count


def process_entry(line: str, min_lines: int) -> Tuple[bool, str, Optional[int], Optional[str]]:
    """
    Process a single entry and determine if it should be kept.

    Args:
        line: Input line in format: blob_id;file_path;base64_content
        min_lines: Minimum number of non-empty lines required

    Returns:
        Tuple of (should_keep, original_line, line_count, error_message)
        - should_keep: True if entry meets criteria
        - original_line: The original input line
        - line_count: Number of non-empty lines (None if error)
        - error_message: Error description if processing failed (None if success)
    """
    try:
        # Parse the line
        parts = line.strip().split(';', 2)
        if len(parts) != 3:
            return (False, line, None, f"Malformed line: expected 3 parts, got {len(parts)}")

        blob_id, file_path, b64_content = parts

        # Decode base64 content
        try:
            content_bytes = base64.b64decode(b64_content)
            content = content_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            return (False, line, None, f"Base64 decode error: {str(e)}")

        # Count non-empty lines
        line_count = count_non_empty_lines(content)

        # Determine if we should keep this entry
        should_keep = line_count >= min_lines

        return (should_keep, line, line_count, None)

    except Exception as e:
        return (False, line, None, f"Unexpected error: {str(e)}")


# =============================================================================
# Main Processing Function
# =============================================================================

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Filter PlantUML files by minimum number of non-empty lines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default settings
  python3 filter_plantuml_by_length.py

  # Custom input/output and minimum lines
  python3 filter_plantuml_by_length.py -i input.gz -o output.txt -m 10

  # Verbose output
  python3 filter_plantuml_by_length.py -v
        """
    )
    parser.add_argument(
        "-i", "--input",
        default=INPUT_FILE,
        help=f"Input file with PlantUML content (default: {INPUT_FILE})"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=OUTPUT_FILE,
        help=f"Output file for filtered content (default: {OUTPUT_FILE})"
    )
    parser.add_argument(
        "-m", "--min-lines",
        type=int,
        default=MIN_LINES,
        help=f"Minimum number of non-empty lines (default: {MIN_LINES})"
    )
    parser.add_argument(
        "-s", "--stats",
        type=Path,
        default=STATS_FILE,
        help=f"Output file for statistics (default: {STATS_FILE})"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create output directory if it doesn't exist
    args.output.parent.mkdir(parents=True, exist_ok=True)

    logging.info("=" * 60)
    logging.info("PlantUML Content Filtering")
    logging.info("=" * 60)
    logging.info(f"Input file: {args.input}")
    logging.info(f"Output file: {args.output}")
    logging.info(f"Minimum lines: {args.min_lines}")
    logging.info(f"Statistics file: {args.stats}")
    logging.info("=" * 60)

    start_time = time.time()

    # Count total entries
    logging.info("Counting total entries...")
    try:
        with gzip.open(args.input, 'rt', encoding='utf-8') as f:
            total_entries = sum(1 for _ in f)
        logging.info(f"Total entries to process: {total_entries:,}")
    except Exception as e:
        logging.error(f"Failed to read input file: {e}")
        return 1

    # Statistics tracking
    stats = {
        "total_entries": total_entries,
        "kept_entries": 0,
        "filtered_entries": 0,
        "error_entries": 0,
        "min_lines_threshold": args.min_lines,
        "line_count_distribution": Counter(),
        "errors": []
    }

    # Process entries
    logging.info("Processing entries...")

    try:
        with gzip.open(args.input, 'rt', encoding='utf-8') as f_in, \
             open(args.output, 'w', encoding='utf-8') as f_out:

            # Initialize progress bar
            iterator = f_in
            if tqdm:
                iterator = tqdm(f_in, total=total_entries, desc="Filtering", unit="entry")

            for line in iterator:
                if not line.strip():
                    continue

                # Process the entry
                should_keep, original_line, line_count, error_msg = process_entry(
                    line, args.min_lines
                )

                if error_msg:
                    # Error occurred
                    stats["error_entries"] += 1
                    if args.verbose:
                        logging.debug(f"Error: {error_msg}")
                    # Keep track of first 10 errors for the report
                    if len(stats["errors"]) < 10:
                        stats["errors"].append(error_msg)
                elif should_keep:
                    # Keep this entry
                    stats["kept_entries"] += 1
                    f_out.write(original_line)
                    if line_count is not None:
                        stats["line_count_distribution"][line_count] += 1
                else:
                    # Filter out this entry
                    stats["filtered_entries"] += 1
                    if line_count is not None:
                        stats["line_count_distribution"][line_count] += 1

                # Update progress bar
                if tqdm and hasattr(iterator, 'set_postfix'):
                    iterator.set_postfix({
                        "kept": stats["kept_entries"],
                        "filtered": stats["filtered_entries"],
                        "errors": stats["error_entries"]
                    })

            if tqdm and hasattr(iterator, 'close'):
                iterator.close()

    except KeyboardInterrupt:
        logging.warning("Interrupted by user. Partial results saved.")
        return 1
    except Exception as e:
        logging.error(f"Error during processing: {e}")
        return 1

    # Calculate timing
    end_time = time.time()
    duration = end_time - start_time

    # Prepare final statistics
    stats["duration_seconds"] = duration
    stats["duration_minutes"] = duration / 60
    stats["entries_per_second"] = total_entries / duration if duration > 0 else 0
    stats["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Calculate percentages
    stats["kept_percentage"] = (stats["kept_entries"] / total_entries * 100) if total_entries > 0 else 0
    stats["filtered_percentage"] = (stats["filtered_entries"] / total_entries * 100) if total_entries > 0 else 0
    stats["error_percentage"] = (stats["error_entries"] / total_entries * 100) if total_entries > 0 else 0

    # Convert Counter to regular dict for JSON serialization
    stats["line_count_distribution"] = dict(stats["line_count_distribution"])

    # Calculate distribution statistics
    if stats["line_count_distribution"]:
        line_counts = []
        for count, freq in stats["line_count_distribution"].items():
            line_counts.extend([count] * freq)

        if line_counts:
            stats["line_count_stats"] = {
                "min": min(line_counts),
                "max": max(line_counts),
                "mean": sum(line_counts) / len(line_counts),
                "median": sorted(line_counts)[len(line_counts) // 2]
            }

    # Write statistics to file
    with open(args.stats, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, sort_keys=True)

    # Print summary
    logging.info("=" * 60)
    logging.info("Processing Complete!")
    logging.info("=" * 60)
    logging.info(f"Total time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logging.info(f"Processing speed: {stats['entries_per_second']:.1f} entries/second")
    logging.info("")
    logging.info("Results:")
    logging.info(f"  Total entries:          {total_entries:,}")
    logging.info(f"  Kept (>={args.min_lines} lines):     {stats['kept_entries']:,} ({stats['kept_percentage']:.1f}%)")
    logging.info(f"  Filtered (<{args.min_lines} lines):  {stats['filtered_entries']:,} ({stats['filtered_percentage']:.1f}%)")
    logging.info(f"  Errors:                 {stats['error_entries']:,} ({stats['error_percentage']:.1f}%)")
    logging.info("")

    if "line_count_stats" in stats:
        logging.info("Line count statistics (for processed entries):")
        logging.info(f"  Minimum:  {stats['line_count_stats']['min']}")
        logging.info(f"  Maximum:  {stats['line_count_stats']['max']}")
        logging.info(f"  Mean:     {stats['line_count_stats']['mean']:.1f}")
        logging.info(f"  Median:   {stats['line_count_stats']['median']}")
        logging.info("")

    logging.info("Output files:")
    logging.info(f"  Filtered content: {args.output}")
    logging.info(f"  Statistics:       {args.stats}")
    logging.info("=" * 60)

    # Show line count distribution (top 20)
    if stats["line_count_distribution"]:
        logging.info("")
        logging.info("Line count distribution (top 20):")
        logging.info("-" * 60)
        sorted_dist = sorted(
            stats["line_count_distribution"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]
        for line_count, freq in sorted_dist:
            bar = "█" * min(50, int(freq / max(stats["line_count_distribution"].values()) * 50))
            logging.info(f"  {line_count:3d} lines: {freq:6,} {bar}")
        logging.info("-" * 60)

    return 0


if __name__ == "__main__":
    exit(main())

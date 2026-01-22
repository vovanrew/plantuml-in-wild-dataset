#!/usr/bin/env python3
"""
PlantUML Content Extraction Script
Extracts and validates PlantUML content from WoC blobs using python-woc

Date: 2025-10-17
"""

import argparse
import base64
import gzip
import json
import logging
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

try:
    from tqdm import tqdm
except ImportError:
    print("Warning: tqdm not installed. Install with: pip install tqdm")
    tqdm = None

try:
    from woc.local import WocMapsLocal
except ImportError:
    print("Error: Could not import python-woc. Make sure python-woc is installed.")
    print("Try: pip install python-woc")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

INPUT_FILE = "/data/play/vopolva/plantuml_extraction/unique_plantuml_blobs_with_files.gz"
OUTPUT_DIR = Path("/data/play/vopolva/plantuml_extraction")
OUTPUT_FILE = OUTPUT_DIR / "valid_plantuml_content.gz"
STATS_FILE = OUTPUT_DIR / "plantuml_stats.json"
INVALID_FILE = OUTPUT_DIR / "invalid_blobs.txt"
ERROR_FILE = OUTPUT_DIR / "error_blobs.txt"

# Number of worker processes
NUM_WORKERS = mp.cpu_count() // 2  # Use half of available cores

# Batch size for reading input
BATCH_SIZE = 1000


# =============================================================================
# Worker Process Functions
# =============================================================================

def process_blob(blob_id: str, file_path: str, woc: WocMapsLocal) -> Tuple[str, str, str, str]:
    """
    Process a single blob and validate PlantUML content.

    Args:
        blob_id: The blob SHA1 hash
        file_path: The file path in the project
        woc: WocMapsLocal instance

    Returns:
        Tuple of (status, blob_id, file_path, result)
        status: 'valid', 'invalid', or 'error'
        result: base64 content if valid, error message otherwise
    """
    try:
        # Get blob content using python-woc
        content = woc.show_content("blob", blob_id)

        if content is None or len(content) == 0:
            return ("error", blob_id, file_path, "Empty content")

        # Check for PlantUML markers
        has_start = "@startuml" in content.lower()
        has_end = "@enduml" in content.lower()

        if has_start and has_end:
            # Valid PlantUML - encode to base64
            content_bytes = content.encode('utf-8', errors='ignore')
            b64_content = base64.b64encode(content_bytes).decode('ascii')
            return ("valid", blob_id, file_path, b64_content)
        else:
            reason = []
            if not has_start:
                reason.append("missing @startuml")
            if not has_end:
                reason.append("missing @enduml")
            return ("invalid", blob_id, file_path, ", ".join(reason))

    except KeyError:
        return ("error", blob_id, file_path, "Blob not found in WoC")
    except Exception as e:
        return ("error", blob_id, file_path, f"Exception: {str(e)}")


def worker_process(input_queue: mp.Queue, output_queue: mp.Queue, worker_id: int):
    """
    Worker process that processes blobs from input_queue and sends results to output_queue.

    Args:
        input_queue: Queue containing (blob_id, file_path) tuples
        output_queue: Queue for sending results
        worker_id: Unique identifier for this worker
    """
    # Each worker creates its own WocMapsLocal instance
    try:
        woc = WocMapsLocal()
    except Exception as e:
        logging.error(f"Worker {worker_id}: Failed to initialize WocMapsLocal: {e}")
        return

    processed = 0
    while True:
        try:
            item = input_queue.get(timeout=1)
            if item is None:  # Poison pill
                break

            blob_id, file_path = item
            result = process_blob(blob_id, file_path, woc)
            output_queue.put(result)
            processed += 1

        except mp.queues.Empty:
            continue
        except Exception as e:
            logging.error(f"Worker {worker_id}: Unexpected error: {e}")
            continue

    logging.info(f"Worker {worker_id}: Processed {processed} blobs")


# =============================================================================
# Writer Process
# =============================================================================

def writer_process(output_queue: mp.Queue, total_blobs: int, output_file: Path,
                   invalid_file: Path, error_file: Path):
    """
    Writer process that reads results from output_queue and writes to files.

    Args:
        output_queue: Queue containing processing results
        total_blobs: Total number of blobs to process
        output_file: Path to valid content output file
        invalid_file: Path to invalid blobs log
        error_file: Path to error blobs log
    """
    stats = {
        "valid": 0,
        "invalid": 0,
        "error": 0,
        "processed": 0
    }

    # Open all output files
    with gzip.open(output_file, 'wt', encoding='utf-8') as f_valid, \
         open(invalid_file, 'w', encoding='utf-8') as f_invalid, \
         open(error_file, 'w', encoding='utf-8') as f_error:

        # Initialize progress bar if tqdm is available
        pbar = None
        if tqdm:
            pbar = tqdm(total=total_blobs, desc="Processing blobs", unit="blob")

        while True:
            try:
                result = output_queue.get(timeout=1)
                if result is None:  # Poison pill
                    break

                status, blob_id, file_path, data = result
                stats[status] += 1
                stats["processed"] += 1

                if status == "valid":
                    # Write: blob_id;file_path;base64_content
                    f_valid.write(f"{blob_id};{file_path};{data}\n")
                elif status == "invalid":
                    # Write: blob_id;file_path;reason
                    f_invalid.write(f"{blob_id};{file_path};{data}\n")
                elif status == "error":
                    # Write: blob_id;file_path;error
                    f_error.write(f"{blob_id};{file_path};{data}\n")

                # Update progress bar
                if pbar:
                    pbar.update(1)
                    pbar.set_postfix({
                        "valid": stats["valid"],
                        "invalid": stats["invalid"],
                        "error": stats["error"]
                    })

            except mp.queues.Empty:
                continue
            except Exception as e:
                logging.error(f"Writer: Unexpected error: {e}")
                continue

        if pbar:
            pbar.close()

    return stats


# =============================================================================
# Main Function
# =============================================================================

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Extract and validate PlantUML content from WoC blobs"
    )
    parser.add_argument(
        "-i", "--input",
        default=INPUT_FILE,
        help=f"Input file with blob_id;file_path pairs (default: {INPUT_FILE})"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=NUM_WORKERS,
        help=f"Number of worker processes (default: {NUM_WORKERS})"
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

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Define output files
    output_file = args.output_dir / "valid_plantuml_content.gz"
    invalid_file = args.output_dir / "invalid_blobs.txt"
    error_file = args.output_dir / "error_blobs.txt"
    stats_file = args.output_dir / "plantuml_stats.json"

    logging.info("=" * 60)
    logging.info("PlantUML Content Extraction")
    logging.info("=" * 60)
    logging.info(f"Input file: {args.input}")
    logging.info(f"Output directory: {args.output_dir}")
    logging.info(f"Workers: {args.workers}")
    logging.info("=" * 60)

    start_time = time.time()

    # Count total blobs
    logging.info("Counting total blobs...")
    with gzip.open(args.input, 'rt', encoding='utf-8') as f:
        total_blobs = sum(1 for _ in f)
    logging.info(f"Total blobs to process: {total_blobs:,}")

    # Create queues
    input_queue = mp.Queue(maxsize=args.workers * 2)
    output_queue = mp.Queue(maxsize=args.workers * 2)

    # Start worker processes
    logging.info(f"Starting {args.workers} worker processes...")
    workers = []
    for i in range(args.workers):
        p = mp.Process(
            target=worker_process,
            args=(input_queue, output_queue, i)
        )
        p.start()
        workers.append(p)

    # Start writer process
    logging.info("Starting writer process...")
    writer = mp.Process(
        target=writer_process,
        args=(output_queue, total_blobs, output_file, invalid_file, error_file)
    )
    writer.start()

    # Feed input queue
    logging.info("Reading input and feeding workers...")
    try:
        with gzip.open(args.input, 'rt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(';', 1)
                if len(parts) != 2:
                    logging.warning(f"Skipping malformed line: {line[:100]}")
                    continue

                blob_id, file_path = parts
                input_queue.put((blob_id, file_path))

        # Send poison pills to workers
        for _ in range(args.workers):
            input_queue.put(None)

    except KeyboardInterrupt:
        logging.warning("Interrupted by user. Cleaning up...")

    # Wait for workers to finish
    logging.info("Waiting for workers to finish...")
    for p in workers:
        p.join()

    # Send poison pill to writer and wait
    output_queue.put(None)
    writer.join()

    # Calculate timing
    end_time = time.time()
    duration = end_time - start_time

    # Read final stats from writer (this is a simplified approach)
    # In a real scenario, you'd use a shared counter or return value
    # For now, we'll count the output files
    valid_count = 0
    invalid_count = 0
    error_count = 0

    try:
        with gzip.open(output_file, 'rt', encoding='utf-8') as f:
            valid_count = sum(1 for _ in f)
    except:
        pass

    try:
        with open(invalid_file, 'r', encoding='utf-8') as f:
            invalid_count = sum(1 for _ in f)
    except:
        pass

    try:
        with open(error_file, 'r', encoding='utf-8') as f:
            error_count = sum(1 for _ in f)
    except:
        pass

    # Create statistics
    stats = {
        "total_blobs": total_blobs,
        "valid_blobs": valid_count,
        "invalid_blobs": invalid_count,
        "error_blobs": error_count,
        "duration_seconds": duration,
        "duration_minutes": duration / 60,
        "blobs_per_second": total_blobs / duration if duration > 0 else 0,
        "workers": args.workers,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Write statistics
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    # Print summary
    logging.info("=" * 60)
    logging.info("Processing Complete!")
    logging.info("=" * 60)
    logging.info(f"Total time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logging.info(f"Processing speed: {stats['blobs_per_second']:.1f} blobs/second")
    logging.info("")
    logging.info("Results:")
    logging.info(f"  Valid PlantUML blobs:   {valid_count:,} ({valid_count/total_blobs*100:.1f}%)")
    logging.info(f"  Invalid blobs:          {invalid_count:,} ({invalid_count/total_blobs*100:.1f}%)")
    logging.info(f"  Error blobs:            {error_count:,} ({error_count/total_blobs*100:.1f}%)")
    logging.info("")
    logging.info("Output files:")
    logging.info(f"  Valid content:  {output_file}")
    logging.info(f"  Invalid blobs:  {invalid_file}")
    logging.info(f"  Error blobs:    {error_file}")
    logging.info(f"  Statistics:     {stats_file}")
    logging.info("=" * 60)

    # Preview valid content
    if valid_count > 0:
        logging.info("")
        logging.info("Preview of valid PlantUML content (first 3 entries):")
        logging.info("-" * 60)
        try:
            with gzip.open(output_file, 'rt', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 3:
                        break
                    parts = line.strip().split(';', 2)
                    if len(parts) == 3:
                        blob_id, file_path, b64 = parts
                        content_preview = base64.b64decode(b64).decode('utf-8', errors='ignore')[:100]
                        logging.info(f"{blob_id} | {file_path}")
                        logging.info(f"  Content preview: {content_preview}...")
        except Exception as e:
            logging.warning(f"Could not read preview: {e}")
        logging.info("-" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Local decoder script to convert base64-encoded PlantUML content to individual files.
Run this on your local machine after downloading the valid_plantuml_content.gz file.

Usage:
    python3 decode_plantuml_content.py valid_plantuml_content.gz -o plantuml_files/
"""

import argparse
import base64
import gzip
import json
import logging
from pathlib import Path
from typing import Dict


def sanitize_filename(filename: str) -> str:
    """
    Convert file path to safe filename by replacing slashes and special chars.

    Example:
        /docs/frames/web.uml -> docs_frames_web.uml
    """
    # Remove leading slash
    filename = filename.lstrip('/')
    # Replace slashes with underscores
    filename = filename.replace('/', '_')
    # Replace other problematic characters
    filename = filename.replace('\\', '_').replace(':', '_')
    return filename


def decode_and_save(input_file: Path, output_dir: Path, format_type: str = "files"):
    """
    Decode base64-encoded PlantUML content and save to files.

    Args:
        input_file: Path to valid_plantuml_content.gz
        output_dir: Output directory for decoded files
        format_type: "files" (individual .puml files) or "json" (single JSON file)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"Reading from: {input_file}")
    logging.info(f"Output directory: {output_dir}")
    logging.info(f"Output format: {format_type}")
    logging.info("")

    stats = {
        "total": 0,
        "decoded": 0,
        "errors": 0
    }

    if format_type == "json":
        # Store all content in a single JSON file
        all_content = {}

    try:
        with gzip.open(input_file, 'rt', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                stats["total"] += 1

                # Parse line: blob_id;file_path;base64_content
                parts = line.split(';', 2)
                if len(parts) != 3:
                    logging.warning(f"Line {line_num}: Malformed (expected 3 fields, got {len(parts)})")
                    stats["errors"] += 1
                    continue

                blob_id, file_path, b64_content = parts

                try:
                    # Decode base64
                    content_bytes = base64.b64decode(b64_content)
                    content = content_bytes.decode('utf-8', errors='ignore')

                    if format_type == "files":
                        # Save as individual file: blob_id.puml
                        output_file = output_dir / f"{blob_id}.puml"
                        with open(output_file, 'w', encoding='utf-8') as out:
                            # Add metadata as comments at the top
                            out.write(f"' Blob ID: {blob_id}\n")
                            out.write(f"' File Path: {file_path}\n")
                            out.write(f"' \n")
                            out.write(content)

                        stats["decoded"] += 1

                        if stats["decoded"] % 1000 == 0:
                            logging.info(f"Decoded {stats['decoded']:,} files...")

                    elif format_type == "json":
                        # Store in dictionary
                        all_content[blob_id] = {
                            "file_path": file_path,
                            "content": content
                        }
                        stats["decoded"] += 1

                except Exception as e:
                    logging.error(f"Line {line_num}: Error decoding {blob_id}: {e}")
                    stats["errors"] += 1

    except FileNotFoundError:
        logging.error(f"Input file not found: {input_file}")
        return None

    # If JSON format, save to single file
    if format_type == "json":
        json_file = output_dir / "plantuml_content.json"
        logging.info(f"Writing JSON file: {json_file}")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_content, f, indent=2, ensure_ascii=False)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Decode base64-encoded PlantUML content to files"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file (valid_plantuml_content.gz)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("plantuml_files"),
        help="Output directory (default: plantuml_files/)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["files", "json"],
        default="files",
        help="Output format: 'files' (individual .puml files) or 'json' (single JSON)"
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

    logging.info("="*60)
    logging.info("PlantUML Content Decoder")
    logging.info("="*60)

    stats = decode_and_save(args.input, args.output, args.format)

    if stats:
        logging.info("")
        logging.info("="*60)
        logging.info("Decoding Complete!")
        logging.info("="*60)
        logging.info(f"Total entries:    {stats['total']:,}")
        logging.info(f"Decoded:          {stats['decoded']:,}")
        logging.info(f"Errors:           {stats['errors']:,}")
        logging.info("")
        logging.info(f"Output location:  {args.output}")
        logging.info("="*60)

        # Show sample files
        if args.format == "files":
            sample_files = list(args.output.glob("*.puml"))[:3]
            if sample_files:
                logging.info("")
                logging.info("Sample files created:")
                for f in sample_files:
                    logging.info(f"  {f.name}")


if __name__ == "__main__":
    main()

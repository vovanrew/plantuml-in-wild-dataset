#!/usr/bin/env python3
"""Remove Graphviz DOT passthrough diagrams (PSystemDot) from the dataset.

These are files that use @startuml with raw `digraph`/`graph` DOT syntax,
which PlantUML forwards to Graphviz without building a UML diagram model.
They are identified by extraction_error == "unsupported_type:PSystemDot".

Usage:
    python3 filter_dot.py \
        --classification uml_with_counts.json \
        --puml-dir /path/to/puml/ \
        --png-dir /path/to/png/ \
        --output uml_with_counts_filtered.json

    # Dry run (report what would be deleted, don't touch anything):
    python3 filter_dot.py \
        --classification uml_with_counts.json \
        --puml-dir /path/to/puml/ \
        --png-dir /path/to/png/ \
        --output /dev/null \
        --dry-run
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REMOVAL_ERROR = "unsupported_type:PSystemDot"


def build_file_index(directory: Path, extension: str) -> dict[str, list[Path]]:
    """Build an index mapping blob_id prefix to matching file paths.

    Scans the directory once, then lookups are O(1).
    Handles flat and batch subdirectory layouts, and multi-page suffixes
    like {blob_id}_001.png from the PlantUML `newpage` keyword.
    """
    index = defaultdict(list)
    for p in directory.rglob(f"*{extension}"):
        index[p.stem].append(p)
        parts = p.stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            index[parts[0]].append(p)
    return dict(index)


def main():
    parser = argparse.ArgumentParser(
        description="Filter Graphviz DOT passthrough diagrams (PSystemDot) from the dataset."
    )
    parser.add_argument(
        "--classification", required=True, type=Path,
        help="Input classification JSON with extraction stats (not modified)",
    )
    parser.add_argument(
        "--puml-dir", required=True, type=Path,
        help="Root directory containing .puml files",
    )
    parser.add_argument(
        "--png-dir", required=True, type=Path,
        help="Root directory containing .png files",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Path for the filtered classification JSON",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    # --- Load classification data ---
    print(f"Loading classification from {args.classification}")
    with open(args.classification) as f:
        data = json.load(f)

    classifications = data["classifications"]
    total_before = len(classifications)

    # --- Identify entries to remove ---
    to_remove: dict[str, dict] = {}
    to_keep: dict[str, dict] = {}
    for fname, entry in classifications.items():
        if entry.get("extraction_error") == REMOVAL_ERROR:
            to_remove[fname] = entry
        else:
            to_keep[fname] = entry

    print(f"Total entries: {total_before}")
    print(f"Entries to remove ({REMOVAL_ERROR}): {len(to_remove)}")
    print(f"Entries to keep: {len(to_keep)}")

    if to_remove:
        print(f"\nRemoved entries by primary_type:")
        type_counts: dict[str, int] = {}
        for entry in to_remove.values():
            t = entry.get("primary_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {t:15s} {count:>5,d}")

    # --- Build file indexes (one scan each) ---
    print("\nIndexing .puml files...")
    puml_index = build_file_index(args.puml_dir, ".puml")
    print("Indexing .png files...")
    png_index = build_file_index(args.png_dir, ".png")

    # --- Delete .puml and .png files ---
    deleted_puml = 0
    deleted_png = 0
    missing_puml = 0
    missing_png = 0

    for fname in sorted(to_remove):
        blob_stem = Path(fname).stem

        # Delete .puml
        puml_files = puml_index.get(blob_stem, [])
        if puml_files:
            for p in puml_files:
                if args.dry_run:
                    print(f"  [dry-run] would delete {p}")
                else:
                    p.unlink()
                deleted_puml += 1
        else:
            missing_puml += 1

        # Delete .png (may have newpage suffixes like blob_001.png, blob_002.png)
        png_files = png_index.get(blob_stem, [])
        if png_files:
            for p in png_files:
                if args.dry_run:
                    print(f"  [dry-run] would delete {p}")
                else:
                    p.unlink()
                deleted_png += 1
        else:
            missing_png += 1

    action = "Would delete" if args.dry_run else "Deleted"
    print(f"\n{action}:")
    print(f"  .puml files: {deleted_puml}  (missing: {missing_puml})")
    print(f"  .png  files: {deleted_png}  (missing: {missing_png})")

    # --- Build filtered JSON (preserve all existing statistics keys) ---
    new_type_distribution = {}
    new_mixed_count = 0
    new_truncated = 0
    for entry in to_keep.values():
        t = entry.get("primary_type", "unknown")
        new_type_distribution[t] = new_type_distribution.get(t, 0) + 1
        if entry.get("secondary_types"):
            new_mixed_count += 1
        if entry.get("truncated"):
            new_truncated += 1

    kept_count = len(to_keep)

    # Remove the filtered error key from extraction_error_distribution
    old_stats = data.get("statistics", {})
    error_dist = {k: v for k, v in old_stats.get("extraction_error_distribution", {}).items()
                  if k != REMOVAL_ERROR}

    filtered_data = {
        "metadata": {
            **data["metadata"],
            "total_files": kept_count,
        },
        "statistics": {
            **old_stats,
            "extraction_error_distribution": error_dist,
            "total_files": kept_count,
            "classified": kept_count,
            "uml": kept_count,
            "non_uml": 0,
            "truncated": new_truncated,
            "errored": 0,
            "mixed_type": new_mixed_count,
            "type_distribution": new_type_distribution,
        },
        "classifications": to_keep,
    }

    if args.dry_run:
        print(f"\n[dry-run] Would write filtered JSON to {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(filtered_data, f, indent=2)
        print(f"\nFiltered JSON written to {args.output}")

    # --- Summary ---
    print(f"\nNew type distribution:")
    for t, count in sorted(new_type_distribution.items(), key=lambda x: -x[1]):
        pct = count / kept_count * 100
        print(f"  {t:15s} {count:>7,d}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()

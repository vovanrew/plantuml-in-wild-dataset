#!/usr/bin/env python3
"""Enrich uml_metadata.json with blob_id, repository, and original_path from puml files and b2P mapping."""

import argparse
import json
import os


def load_blob_to_project(filepath):
    """Load blob_id;project mapping into a dict."""
    mapping = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(";", 1)
            if len(parts) == 2:
                mapping[parts[0]] = parts[1]
    return mapping


def extract_header(puml_path):
    """Extract blob_id and original_path from the first 3 header lines."""
    blob_id = None
    original_path = None
    with open(puml_path, "r", errors="replace") as f:
        for _ in range(3):
            line = f.readline().strip()
            if line.startswith("' Blob ID: "):
                blob_id = line[len("' Blob ID: "):]
            elif line.startswith("' Original Path: "):
                original_path = line[len("' Original Path: "):]
    return blob_id, original_path


def main():
    parser = argparse.ArgumentParser(description="Enrich uml_metadata.json with blob/project/path info")
    parser.add_argument("metadata_json", help="Path to uml_metadata.json")
    parser.add_argument("blob_to_project", help="Path to blob_ids_final_to_project.txt")
    parser.add_argument("puml_folder", help="Path to folder containing .puml files")
    parser.add_argument("-o", "--output", default="uml_metadata_enriched.json", help="Output JSON path")
    args = parser.parse_args()

    b2p = load_blob_to_project(args.blob_to_project)
    print(f"Loaded {len(b2p)} blob-to-project mappings")

    with open(args.metadata_json, "r") as f:
        data = json.load(f)

    classifications = data["classifications"]
    missing_count = 0
    enriched_count = 0

    for filename, entry in classifications.items():
        puml_path = os.path.join(args.puml_folder, filename)

        if os.path.exists(puml_path):
            blob_id, original_path = extract_header(puml_path)
        else:
            blob_id = filename.replace(".puml", "")
            original_path = None

        if blob_id is None:
            blob_id = filename.replace(".puml", "")

        repository = b2p.get(blob_id, None)
        if repository is None:
            missing_count += 1

        entry["blob_id"] = blob_id
        entry["original_path"] = original_path
        entry["repository"] = repository
        enriched_count += 1

    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Enriched {enriched_count} entries, {missing_count} missing projects")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()

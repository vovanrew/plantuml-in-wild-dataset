#!/bin/bash
# Extract blob IDs from .puml file headers and write to a text file.
# Usage: ./extract_blob_ids.sh <puml_folder> <output_file>

if [ $# -ne 2 ]; then
    echo "Usage: $0 <puml_folder> <output_file>"
    exit 1
fi

PUML_FOLDER="$1"
OUTPUT_FILE="$2"

if [ ! -d "$PUML_FOLDER" ]; then
    echo "Error: Directory '$PUML_FOLDER' does not exist."
    exit 1
fi

find "$PUML_FOLDER" -name '*.puml' -print0 | xargs -0 grep -h "^' Blob ID: " | sed "s/^' Blob ID: //" > "$OUTPUT_FILE"

echo "Extracted $(wc -l < "$OUTPUT_FILE" | tr -d ' ') blob IDs to $OUTPUT_FILE"

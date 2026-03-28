#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 <uml_metadata.json> [validation_summary.json]" >&2
    exit 1
fi

DATA_FILE="$1"
VALIDATION_FILE="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for script in \
    fig1_type_distribution.py \
    fig2_loc_distribution.py \
    fig3_element_types.py \
    fig4_connection_categories.py
do
    echo "=== $script ==="
    python3 "$SCRIPT_DIR/$script" "$DATA_FILE"
    echo
done

if [ -n "$VALIDATION_FILE" ]; then
    for script in \
        fig5_confusion_matrix.py \
        fig6_validation_accuracy.py
    do
        echo "=== $script ==="
        python3 "$SCRIPT_DIR/$script" "$VALIDATION_FILE"
        echo
    done
fi

echo "All figures generated."

#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <uml_metadata.json>" >&2
    exit 1
fi

DATA_FILE="$1"
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

echo "All figures generated."

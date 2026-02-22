#!/bin/bash

# PlantUML Extraction Script for WoC
# Extracts PlantUML files from lb2fFull basemaps with parallel processing
# Date: 2025-10-15

set -e  # Exit on error

# ============================================
# Configuration
# ============================================
USERNAME="vopolva"
SCRATCH_DIR="/data/play/${USERNAME}/plantuml_extraction"
DATA_PATH="/da8_data/basemaps/gz"

# File extensions to search for PlantUML files
PLANTUML_PATTERN='\.(puml|pu|plantuml|wsd|iuml|uml)$'

# ============================================
# Determine Parallelization
# ============================================
TOTAL_CORES=$(nproc)
# Use half of available cores to avoid overwhelming the system
PARALLEL_JOBS=$((TOTAL_CORES / 2))
[[ $PARALLEL_JOBS -lt 1 ]] && PARALLEL_JOBS=1

echo "============================================"
echo "PlantUML Extraction Script"
echo "============================================"
echo "System has ${TOTAL_CORES} cores"
echo "Using ${PARALLEL_JOBS} parallel jobs"
echo "Working directory: ${SCRATCH_DIR}"
echo "============================================"
echo ""

# ============================================
# Setup
# ============================================
mkdir -p ${SCRATCH_DIR}
cd ${SCRATCH_DIR}

# Function to process a single file with progress tracking
process_file() {
    local i=$1
    local file="lb2fFullV${i}.s"

    echo "[$(date +%T)] Starting ${file}"

    if [[ ! -f ${DATA_PATH}/${file} ]]; then
        echo "[$(date +%T)] ERROR: ${DATA_PATH}/${file} not found"
        return 1
    fi

    zcat ${DATA_PATH}/${file} | \
        grep -iE "${PLANTUML_PATTERN}" | \
        gzip > plantuml_files_${i}.gz

    local count=$(zcat plantuml_files_${i}.gz 2>/dev/null | wc -l)
    echo "[$(date +%T)] Finished ${file} - Found ${count} PlantUML files"
}

# Export function and variables for use in subshells
export -f process_file
export DATA_PATH
export PLANTUML_PATTERN

# ============================================
# Step 1: Extract PlantUML Files in Parallel
# ============================================
echo "Step 1: Extracting PlantUML file paths from 128 lb2fFull files"
echo "============================================"

TOTAL_FILES=128
BATCH_SIZE=${PARALLEL_JOBS}
BATCHES=$(( (TOTAL_FILES + BATCH_SIZE - 1) / BATCH_SIZE ))

START_TIME=$(date +%s)

for batch in $(seq 0 $((BATCHES - 1)))
do
    start=$((batch * BATCH_SIZE))
    end=$((start + BATCH_SIZE - 1))
    [[ $end -ge $TOTAL_FILES ]] && end=$((TOTAL_FILES - 1))

    echo ""
    echo "--- Batch $((batch + 1))/${BATCHES}: Processing files ${start}-${end} ---"

    for i in $(seq ${start} ${end})
    do
        process_file $i &
    done

    # Wait for current batch to complete
    wait
    echo "--- Batch $((batch + 1))/${BATCHES} completed ---"
done

STEP1_TIME=$(date +%s)
STEP1_DURATION=$((STEP1_TIME - START_TIME))

echo ""
echo "============================================"
echo "Step 1 completed in ${STEP1_DURATION} seconds"
echo "============================================"
echo ""

# ============================================
# Step 2: Merge All Results
# ============================================
echo "Step 2: Merging results from all 128 files..."
echo "============================================"

zcat plantuml_files_*.gz | gzip > plantuml_files_all.gz

TOTAL_ENTRIES=$(zcat plantuml_files_all.gz | wc -l)
echo "Total PlantUML file entries: ${TOTAL_ENTRIES}"

STEP2_TIME=$(date +%s)
STEP2_DURATION=$((STEP2_TIME - STEP1_TIME))
echo "Step 2 completed in ${STEP2_DURATION} seconds"
echo ""

# ============================================
# Step 3: Extract Unique Blob IDs with File Paths
# ============================================
echo "Step 3: Extracting unique blob-to-file mappings..."
echo "============================================"

# Sort by blob_id (field 1) and keep unique blob_id;file pairs
# -t\; : use semicolon as delimiter
# -k1,1 : sort by first field only
# -u : keep only unique lines based on the sort key
zcat plantuml_files_all.gz | sort -u -t\; -k1,1 | gzip > unique_plantuml_blobs_with_files.gz

UNIQUE_BLOBS=$(zcat unique_plantuml_blobs_with_files.gz | wc -l)
echo "Unique PlantUML blob-to-file pairs: ${UNIQUE_BLOBS}"

STEP3_TIME=$(date +%s)
STEP3_DURATION=$((STEP3_TIME - STEP2_TIME))
echo "Step 3 completed in ${STEP3_DURATION} seconds"
echo ""

# ============================================
# Summary
# ============================================
TOTAL_TIME=$(date +%s)
TOTAL_DURATION=$((TOTAL_TIME - START_TIME))

echo "============================================"
echo "Processing Complete!"
echo "============================================"
echo "Total time: ${TOTAL_DURATION} seconds ($((TOTAL_DURATION / 60)) minutes)"
echo ""
echo "Statistics:"
echo "  - Total PlantUML file entries: ${TOTAL_ENTRIES}"
echo "  - Unique PlantUML blobs: ${UNIQUE_BLOBS}"
echo ""
echo "Output files (in ${SCRATCH_DIR}):"
echo "  - plantuml_files_all.gz      : All PlantUML file entries (blob;path)"
echo "  - unique_plantuml_blobs.gz   : Unique blob IDs only"
echo "  - plantuml_files_0.gz to plantuml_files_127.gz : Individual file results"
echo ""
echo "Preview of results:"
echo "---"
zcat plantuml_files_all.gz | head -n 10
echo "---"
echo ""
echo "To view full results:"
echo "  zcat ${SCRATCH_DIR}/plantuml_files_all.gz | less"
echo ""
echo "To join with b2P (blob to project mapping):"
echo "  zcat plantuml_files_all.gz | join -t\; -1 1 -2 1 - <(zcat /da?_data/basemaps/gz/b2PFullV0.s)"
echo "============================================"

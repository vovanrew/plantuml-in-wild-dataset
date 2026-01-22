#!/usr/bin/env bash
# PlantUML @startuml Normalization Script
# Removes custom names from @startuml directives
#
# Usage: ./normalize_startuml.sh [puml_directory]
#   puml_directory: Directory containing .puml files (default: ./puml)

set -e  # Exit on error

# ============================================
# Configuration
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Accept directory as first argument, default to ./puml
if [[ -n "$1" ]]; then
    PUML_DIR="$1"
else
    PUML_DIR="${SCRIPT_DIR}/puml"
fi

# ============================================
# Color Output
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# Functions
# ============================================

print_header() {
    echo ""
    echo "============================================"
    echo "$1"
    echo "============================================"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================
# Main
# ============================================

main() {
    print_header "PlantUML @startuml Normalization"

    # Check if validation directory exists
    if [[ ! -d "${PUML_DIR}" ]]; then
        print_error "Validation directory not found: ${PUML_DIR}"
        exit 1
    fi

    print_info "Processing directory: ${PUML_DIR}"
    print_info ""

    # Find all batch directories
    mapfile -t BATCH_DIRS < <(find "${PUML_DIR}" -mindepth 1 -maxdepth 1 -type d -name "batch_*" | sort)

    # Determine if we have batch directories or a single directory
    BATCH_MODE=false
    if [[ ${#BATCH_DIRS[@]} -gt 0 ]]; then
        BATCH_MODE=true
        print_info "Found ${#BATCH_DIRS[@]} batch directories"
        DIRS_TO_PROCESS=("${BATCH_DIRS[@]}")
    else
        print_info "No batch directories found, processing all files in ${PUML_DIR}"
        DIRS_TO_PROCESS=("${PUML_DIR}")
    fi
    print_info ""

    # Start timer
    START_TIME=$(date +%s)

    TOTAL_FILES_MODIFIED=0
    TOTAL_FILES_PROCESSED=0
    TOTAL_FILES=0

    # Count total files first for progress tracking
    for dir in "${DIRS_TO_PROCESS[@]}"; do
        file_count=$(find "${dir}" -name "*.puml" | wc -l | tr -d ' ')
        TOTAL_FILES=$((TOTAL_FILES + file_count))
    done

    print_info "Total files to process: ${TOTAL_FILES}"
    print_info ""

    # Process each directory
    for dir in "${DIRS_TO_PROCESS[@]}"; do
        dir_name=$(basename "${dir}")

        if [[ "${BATCH_MODE}" == true ]]; then
            print_info "Processing ${dir_name}..."
        fi

        # Find all .puml files in this directory
        mapfile -t PUML_FILES < <(find "${dir}" -name "*.puml")
        dir_file_count=${#PUML_FILES[@]}

        # Process files with real-time progress
        local_files_modified=0
        local_files_processed=0

        for file in "${PUML_FILES[@]}"; do
            local_files_processed=$((local_files_processed + 1))
            TOTAL_FILES_PROCESSED=$((TOTAL_FILES_PROCESSED + 1))

            # Check if file needs modification
            # Match either @startuml{...} or @startuml <name> (but not @startuml(...) or @startuml[...])
            if grep -qE "@startuml(\{[^}]*\}|[[:space:]]+[^(\[])" "${file}" 2>/dev/null; then
                # Remove @startuml{...} braces (custom names)
                # Remove @startuml <name> space-separated names
                # Preserve @startuml(...) and @startuml[...] (valid PlantUML parameters)
                sed -i '' -E 's/@startuml\{[^}]*\}/@startuml/g' "${file}"
                sed -i '' -E 's/@startuml[[:space:]]+[^(\[].*/@startuml/' "${file}"
                local_files_modified=$((local_files_modified + 1))
                TOTAL_FILES_MODIFIED=$((TOTAL_FILES_MODIFIED + 1))
            fi

            # Show progress every 100 files in non-batch mode or every 50 in batch mode
            progress_interval=100
            if [[ "${BATCH_MODE}" == true ]]; then
                progress_interval=50
            fi

            if [[ $((local_files_processed % progress_interval)) -eq 0 ]] || [[ ${local_files_processed} -eq ${dir_file_count} ]]; then
                if [[ "${BATCH_MODE}" == true ]]; then
                    echo -ne "\r  ${dir_name}: Processing... [${TOTAL_FILES_PROCESSED}/${TOTAL_FILES}] (${local_files_modified} modified)"
                else
                    echo -ne "\rProcessing... [${TOTAL_FILES_PROCESSED}/${TOTAL_FILES}] (${TOTAL_FILES_MODIFIED} modified)"
                fi
            fi
        done

        # Print final newline and summary for this directory
        echo ""
        if [[ ${local_files_modified} -gt 0 ]]; then
            if [[ "${BATCH_MODE}" == true ]]; then
                print_success "  ${dir_name}: Modified ${local_files_modified} files (${dir_file_count} total)"
            else
                print_success "Modified ${local_files_modified} files (${dir_file_count} total)"
            fi
        else
            if [[ "${BATCH_MODE}" == true ]]; then
                print_info "  ${dir_name}: No files to modify (${dir_file_count} total)"
            else
                print_info "No files to modify (${dir_file_count} total)"
            fi
        fi
    done

    # End timer
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    print_header "Normalization Complete"
    print_info "Total time: ${MINUTES}m ${SECONDS}s"
    print_info ""
    print_info "Results:"
    if [[ "${BATCH_MODE}" == true ]]; then
        print_info "  Batches processed:    ${#DIRS_TO_PROCESS[@]}"
    fi
    print_info "  Files processed:      ${TOTAL_FILES_PROCESSED}"
    print_info "  Files modified:       ${TOTAL_FILES_MODIFIED}"
    print_info "  Files unchanged:      $((TOTAL_FILES_PROCESSED - TOTAL_FILES_MODIFIED))"
    print_info ""

    if [[ ${TOTAL_FILES_MODIFIED} -gt 0 ]]; then
        print_success "Successfully normalized @startuml directives!"
    else
        print_info "No files needed modification"
    fi

    print_header "Done"
}

# ============================================
# Execute Main
# ============================================

main "$@"

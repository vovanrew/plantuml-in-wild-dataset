#!/usr/bin/env bash
# PlantUML High-DPI Image Generation Script
# Regenerates PNG images from PlantUML diagrams at a configurable DPI
# (default 300; PlantUML's built-in default is 96).
#
# This is a sibling of generate_images.sh. The behavioural differences are:
#   1. A small skinparam config file is fed to PlantUML via -config so every
#      diagram is rendered at the chosen DPI. The original .puml sources
#      are not modified.
#   2. PlantUML's per-dimension pixel cap (PLANTUML_LIMIT_SIZE) is raised
#      from the 4096 default to a configurable value (default 16384) so
#      that high-DPI renders are not clipped on the long side.
#   3. The JVM max heap is sized proportionally to the cap to absorb the
#      larger raster buffers.
#
# Usage: ./generate_images_hidpi.sh <input-dir> <output-dir> [dpi] [limit_size]

set -e  # Exit on error

# ============================================
# Configuration
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLANTUML_JAR="${SCRIPT_DIR}/plantuml-1.2025.9.jar"

# Default DPI for rendered PNG output. Overridable via the 3rd CLI argument.
DEFAULT_DPI=300

# Default per-dimension pixel cap (PLANTUML_LIMIT_SIZE). PlantUML's built-in
# default is 4096; 16384 covers roughly 99.9% of typical diagrams at 300 DPI.
# Overridable via the 4th CLI argument.
DEFAULT_LIMIT_SIZE=16384

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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Usage: $0 <input-dir> <output-dir> [dpi] [limit_size]"
    echo ""
    echo "Arguments:"
    echo "  <input-dir>    Directory containing .puml files"
    echo "  <output-dir>   Directory where PNG images will be saved"
    echo "  [dpi]          Optional DPI override (default ${DEFAULT_DPI};"
    echo "                 PlantUML's built-in default is 96)"
    echo "  [limit_size]   Optional PLANTUML_LIMIT_SIZE override in pixels"
    echo "                 (default ${DEFAULT_LIMIT_SIZE}; PlantUML's built-in default is 4096)"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 validation/batch_0001 images/batch_0001"
    echo "  $0 validation/batch_0001 images/batch_0001 384"
    echo "  $0 validation/batch_0001 images/batch_0001 300 32768"
    exit 0
}

check_prerequisites() {
    print_info "Checking prerequisites..."

    if [[ ! -f "${PLANTUML_JAR}" ]]; then
        print_error "PlantUML jar not found: ${PLANTUML_JAR}"
        exit 1
    fi
    print_success "PlantUML jar found: ${PLANTUML_JAR}"

    if ! command -v java &> /dev/null; then
        print_error "Java is not installed or not in PATH"
        exit 1
    fi
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    print_success "Java found: ${JAVA_VERSION}"
}

# ============================================
# Main
# ============================================

main() {
    print_header "PlantUML High-DPI Image Generator"

    if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_help
    fi

    if [[ $# -lt 2 ]] || [[ $# -gt 4 ]]; then
        print_error "Invalid number of arguments"
        echo "Usage: $0 <input-dir> <output-dir> [dpi] [limit_size]"
        echo "Run '$0 --help' for more information"
        exit 1
    fi

    INPUT_DIR="$1"
    OUTPUT_DIR="$2"
    DPI="${3:-${DEFAULT_DPI}}"
    LIMIT_SIZE="${4:-${DEFAULT_LIMIT_SIZE}}"

    if ! [[ "${DPI}" =~ ^[0-9]+$ ]] || [[ "${DPI}" -le 0 ]]; then
        print_error "DPI must be a positive integer (got: ${DPI})"
        exit 1
    fi

    if ! [[ "${LIMIT_SIZE}" =~ ^[0-9]+$ ]] || [[ "${LIMIT_SIZE}" -le 0 ]]; then
        print_error "PLANTUML_LIMIT_SIZE must be a positive integer (got: ${LIMIT_SIZE})"
        exit 1
    fi

    # Size the JVM max heap proportionally to the cap. Worst-case raster
    # buffer is LIMIT_SIZE^2 * 4 bytes; with parallel threads we need
    # several such buffers in flight. Heuristic: LIMIT_SIZE/2 megabytes,
    # floored at 2 GB.
    HEAP_MB=$(( LIMIT_SIZE / 2 ))
    if [[ ${HEAP_MB} -lt 2048 ]]; then
        HEAP_MB=2048
    fi

    if [[ ! -d "${INPUT_DIR}" ]]; then
        print_error "Input directory not found: ${INPUT_DIR}"
        exit 1
    fi
    print_success "Input directory: ${INPUT_DIR}"

    FILE_COUNT=$(find "${INPUT_DIR}" -name "*.puml" | wc -l | tr -d ' ')
    if [[ ${FILE_COUNT} -eq 0 ]]; then
        print_error "No .puml files found in ${INPUT_DIR}"
        exit 1
    fi
    print_success "Found ${FILE_COUNT} .puml files"

    mkdir -p "${OUTPUT_DIR}"
    OUTPUT_DIR="$(cd "${OUTPUT_DIR}" && pwd)"
    print_success "Output directory: ${OUTPUT_DIR}"

    check_prerequisites

    # Write a small skinparam config so every diagram inherits the DPI
    # without mutating the source .puml files.
    CONFIG_FILE="${OUTPUT_DIR}/dpi.cfg"
    echo "skinparam dpi ${DPI}" > "${CONFIG_FILE}"
    print_info "DPI: ${DPI} (config at ${CONFIG_FILE})"
    print_info "PLANTUML_LIMIT_SIZE: ${LIMIT_SIZE} px; JVM max heap: ${HEAP_MB} MB"

    print_header "Generating Images"
    print_info "Processing ${FILE_COUNT} files with parallel threads..."

    ERROR_LOG="${OUTPUT_DIR}/errors.log"

    local plantuml_cmd="java"
    plantuml_cmd="${plantuml_cmd} -DPLANTUML_LIMIT_SIZE=${LIMIT_SIZE}"
    plantuml_cmd="${plantuml_cmd} -Xmx${HEAP_MB}m"
    plantuml_cmd="${plantuml_cmd} -jar ${PLANTUML_JAR}"
    plantuml_cmd="${plantuml_cmd} --threads auto"
    plantuml_cmd="${plantuml_cmd} --output-dir ${OUTPUT_DIR}"
    plantuml_cmd="${plantuml_cmd} -tpng"
    plantuml_cmd="${plantuml_cmd} -stdrpt"
    plantuml_cmd="${plantuml_cmd} --no-error-image"
    plantuml_cmd="${plantuml_cmd} -config \"${CONFIG_FILE}\""
    plantuml_cmd="${plantuml_cmd} \"${INPUT_DIR}/*.puml\""

    START_TIME=$(date +%s)

    local exit_code=0
    if eval "${plantuml_cmd}" > /dev/null 2> "${ERROR_LOG}"; then
        exit_code=0
    else
        exit_code=$?
    fi

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    IMAGE_COUNT=$(find "${OUTPUT_DIR}" -name "*.png" | wc -l | tr -d ' ')

    local ERROR_FILE_COUNT=0
    if [[ -f "${ERROR_LOG}" && -s "${ERROR_LOG}" ]]; then
        ERROR_FILE_COUNT=$(grep "Error line .* in file:" "${ERROR_LOG}" 2>/dev/null | \
            sed 's/^Error line .* in file: //' | \
            sort -u | \
            wc -l | \
            tr -d ' ')

        if [[ ${ERROR_FILE_COUNT} -eq 0 ]]; then
            ERROR_FILE_COUNT=$(grep ":error:" "${ERROR_LOG}" 2>/dev/null | \
                sed 's/:.*$//' | \
                sort -u | \
                wc -l | \
                tr -d ' ')
        fi
    fi

    local VALID_FILE_COUNT=$((FILE_COUNT - ERROR_FILE_COUNT))

    STATS_FILE="${OUTPUT_DIR}/generation_stats.txt"
    {
        echo "PlantUML High-DPI Image Generation Statistics"
        echo "============================================="
        echo ""
        echo "Timestamp: $(date)"
        echo "Input directory: ${INPUT_DIR}"
        echo "Output directory: ${OUTPUT_DIR}"
        echo "DPI: ${DPI}"
        echo "PLANTUML_LIMIT_SIZE: ${LIMIT_SIZE}"
        echo "JVM max heap: ${HEAP_MB} MB"
        echo ""
        echo "Summary:"
        echo "  Total files:       ${FILE_COUNT}"
        echo "  Valid files:       ${VALID_FILE_COUNT}"
        echo "  Failed files:      ${ERROR_FILE_COUNT}"
        echo "  Images generated:  ${IMAGE_COUNT}"
        echo "  Success rate:      $((VALID_FILE_COUNT * 100 / FILE_COUNT))%"
        echo ""
        echo "Processing time: ${MINUTES}m ${SECONDS}s"
        echo ""

        if [[ ${ERROR_FILE_COUNT} -gt 0 ]]; then
            echo "Failed files list:"
            echo "=================="
            grep "Error line .* in file:" "${ERROR_LOG}" 2>/dev/null | \
                sed 's/^Error line .* in file: //' | \
                sort -u
        fi
    } > "${STATS_FILE}"

    print_header "Generation Complete"
    print_info "Total time: ${MINUTES}m ${SECONDS}s"
    print_info ""
    print_info "Results:"
    print_info "  Total files:      ${FILE_COUNT}"
    print_info "  Valid files:      ${VALID_FILE_COUNT}"
    print_info "  Files with errors: ${ERROR_FILE_COUNT}"
    print_info "  Images generated: ${IMAGE_COUNT} (includes error images)"

    if [[ ${ERROR_FILE_COUNT} -eq 0 ]]; then
        print_success "  Success rate:     100% (${VALID_FILE_COUNT}/${FILE_COUNT})"
        print_success ""
        print_success "All files are syntactically valid!"
    else
        local SUCCESS_RATE=$((VALID_FILE_COUNT * 100 / FILE_COUNT))
        print_warning "  Success rate:     ${SUCCESS_RATE}% (${VALID_FILE_COUNT}/${FILE_COUNT})"
        print_warning ""
        print_warning "Some files have syntax errors (see ${ERROR_LOG})"
        print_warning ""
        print_warning "Note: PlantUML generates error images for invalid files,"
        print_warning "      so image count (${IMAGE_COUNT}) may equal file count even with errors."
    fi

    print_info ""
    print_info "Output files:"
    print_info "  Images:     ${OUTPUT_DIR}/*.png"
    print_info "  Stats:      ${STATS_FILE}"
    print_info "  Error log:  ${ERROR_LOG}"
    print_info "  DPI config: ${CONFIG_FILE}"

    print_header "Done"

    if [[ ${ERROR_FILE_COUNT} -ne 0 ]]; then
        exit 1
    fi
}

# ============================================
# Execute Main
# ============================================

main "$@"

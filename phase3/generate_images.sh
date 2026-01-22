#!/usr/bin/env bash
# PlantUML Image Generation Script
# Generates PNG images from PlantUML diagrams in a directory
#
# Usage: ./generate_images.sh <input-dir> <output-dir>

set -e  # Exit on error

# ============================================
# Configuration
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLANTUML_JAR="${SCRIPT_DIR}/plantuml-1.2025.9.jar"

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
    echo "Usage: $0 <input-dir> <output-dir>"
    echo ""
    echo "Arguments:"
    echo "  <input-dir>   Directory containing .puml files"
    echo "  <output-dir>  Directory where PNG images will be saved"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 validation/batch_0001 images/batch_0001"
    echo "  $0 validation/batch_0001 test_output"
    exit 0
}

check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if PlantUML jar exists
    if [[ ! -f "${PLANTUML_JAR}" ]]; then
        print_error "PlantUML jar not found: ${PLANTUML_JAR}"
        exit 1
    fi
    print_success "PlantUML jar found: ${PLANTUML_JAR}"

    # Check if Java is installed
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
    print_header "PlantUML Image Generator"

    # Parse arguments
    if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_help
    fi

    if [[ $# -ne 2 ]]; then
        print_error "Invalid number of arguments"
        echo "Usage: $0 <input-dir> <output-dir>"
        echo "Run '$0 --help' for more information"
        exit 1
    fi

    INPUT_DIR="$1"
    OUTPUT_DIR="$2"

    # Validate input directory
    if [[ ! -d "${INPUT_DIR}" ]]; then
        print_error "Input directory not found: ${INPUT_DIR}"
        exit 1
    fi
    print_success "Input directory: ${INPUT_DIR}"

    # Count .puml files
    FILE_COUNT=$(find "${INPUT_DIR}" -name "*.puml" | wc -l | tr -d ' ')
    if [[ ${FILE_COUNT} -eq 0 ]]; then
        print_error "No .puml files found in ${INPUT_DIR}"
        exit 1
    fi
    print_success "Found ${FILE_COUNT} .puml files"

    # Create output directory
    mkdir -p "${OUTPUT_DIR}"
    print_success "Output directory: ${OUTPUT_DIR}"

    # Check prerequisites
    check_prerequisites

    print_header "Generating Images"
    print_info "Processing ${FILE_COUNT} files with parallel threads..."

    # Create error log
    ERROR_LOG="${OUTPUT_DIR}/errors.log"

    # Build PlantUML command
    local plantuml_cmd="java -jar ${PLANTUML_JAR}"
    plantuml_cmd="${plantuml_cmd} --threads auto"
    plantuml_cmd="${plantuml_cmd} --output-dir ${OUTPUT_DIR}"
    plantuml_cmd="${plantuml_cmd} -tpng"
    plantuml_cmd="${plantuml_cmd} -stdrpt"
    plantuml_cmd="${plantuml_cmd} --no-error-image"
    plantuml_cmd="${plantuml_cmd} \"${INPUT_DIR}/*.puml\""

    # Start timer
    START_TIME=$(date +%s)

    # Execute PlantUML and capture stderr
    local exit_code=0
    if eval "${plantuml_cmd}" > /dev/null 2> "${ERROR_LOG}"; then
        exit_code=0
    else
        exit_code=$?
    fi

    # End timer
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    # Count generated images (includes error images!)
    IMAGE_COUNT=$(find "${OUTPUT_DIR}" -name "*.png" | wc -l | tr -d ' ')

    # Count files with errors by parsing unique filenames from error log
    local ERROR_FILE_COUNT=0
    if [[ -f "${ERROR_LOG}" && -s "${ERROR_LOG}" ]]; then
        # Extract unique filenames that had errors
        # Format: "Error line X in file: path/to/file.puml"
        ERROR_FILE_COUNT=$(grep "Error line .* in file:" "${ERROR_LOG}" 2>/dev/null | \
            sed 's/^Error line .* in file: //' | \
            sort -u | \
            wc -l | \
            tr -d ' ')

        # If no "Error line" format found, try the :error: format (fallback)
        if [[ ${ERROR_FILE_COUNT} -eq 0 ]]; then
            ERROR_FILE_COUNT=$(grep ":error:" "${ERROR_LOG}" 2>/dev/null | \
                sed 's/:.*$//' | \
                sort -u | \
                wc -l | \
                tr -d ' ')
        fi
    fi

    local VALID_FILE_COUNT=$((FILE_COUNT - ERROR_FILE_COUNT))

    # Generate stats file
    STATS_FILE="${OUTPUT_DIR}/generation_stats.txt"
    {
        echo "PlantUML Image Generation Statistics"
        echo "====================================="
        echo ""
        echo "Timestamp: $(date)"
        echo "Input directory: ${INPUT_DIR}"
        echo "Output directory: ${OUTPUT_DIR}"
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

    print_header "Done"

    # Exit with error if any files had syntax errors
    if [[ ${ERROR_FILE_COUNT} -ne 0 ]]; then
        exit 1
    fi
}

# ============================================
# Execute Main
# ============================================

main "$@"

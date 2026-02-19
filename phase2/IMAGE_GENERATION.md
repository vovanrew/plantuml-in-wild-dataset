# Phase 2: File Preparation and Image Generation

## Overview

Phase 2 takes the base64-encoded PlantUML content from Phase 1 and produces individual `.puml` files and their corresponding PNG images. The pipeline has four steps:

## Pipeline Steps

### Step 1: Generate PUML Files (`1.generate_puml_files/`)

Decodes base64-encoded content into individual `.puml` files, one per blob. Each file is named `{blob_id}.puml` and includes metadata comments (Blob ID, Original Path, Source).

See `1.generate_puml_files/README.md` for details.

### Step 2: Split Multi-Diagram Files (`2.split_diagrams/`)

Some source files contain multiple `@startuml...@enduml` blocks. This step splits them into one-diagram-per-file (`{blob_id}_01.puml`, `{blob_id}_02.puml`, etc.) and moves originals to a separate directory.

See `2.split_diagrams/README.md` for details.

### Step 3: Normalize @startuml Directives (`3.normalize_diagrams/`)

Strips custom names from `@startuml` tags (e.g., `@startuml MyDiagram` → `@startuml`) so that PlantUML uses the source filename for PNG output, preserving the blob-ID-based naming convention.

See `3.normalize_diagrams/README.md` for details.

### Step 4: Generate Images (`4.generate_images/`)

Compiles `.puml` files into PNG images using PlantUML.

- **Command**: `java -jar plantuml.jar -tpng --threads auto --no-error-image -stdrpt`
- Files that fail compilation are logged to `errors.log` and produce no image
- The `newpage` keyword can cause a single `.puml` file to produce multiple PNGs, named `{blob_id}_001.png`, `{blob_id}_002.png`, etc.

## Metrics

The generation process tracks:
- **File-level**: Total individual diagram files processed
- **Image-level**: Total PNG images generated (may exceed file count due to `newpage`)
- **Success rate**: (Total files - Error files) / Total files

# PlantUML Image Generation Process

## Overview

PlantUML processes `.puml` files and generates PNG images for each diagram defined by `@startuml`/`@enduml` pairs.

## File Organization

### Multi-Diagram File Splitting

The dataset originally contained files with multiple diagrams. These have been split into individual files for cleaner processing:

- **Script**: `split_multi_diagrams.py`
- **Naming convention**: Original files split into `{filename}_01.puml`, `{filename}_02.puml`, etc.
- **Original files**: Moved to `many_pumls/` directory


### Current Structure

- **`puml/`**: Contains individual diagram files (one diagram per file)
- **`many_pumls/`**: Contains original files that had multiple diagrams

### Example

Original file `370fbdd3020a3d0e566c0a501e6e0920c20fef14.puml` with 2 diagrams:
- Split into: `370fbdd3020a3d0e566c0a501e6e0920c20fef14_01.puml` and `370fbdd3020a3d0e566c0a501e6e0920c20fef14_02.puml`
- Original moved to: `many_pumls/370fbdd3020a3d0e566c0a501e6e0920c20fef14.puml`

Each split file preserves the original header comments (Blob ID, Original Path, Source).

## Key Behavior

### Single Diagram Per File

After splitting, each `.puml` file in the `puml/` directory contains a single diagram:

```plantuml
@startuml
class A
@enduml
```

This generates:
- `filename.png` (single diagram)

## Generation images

```
Total .puml files:        207,159
PNG images generated:     163,589
```

## PUML Validation Summary

Total PUML files processed: 207,159
Valid PUML files:   162,257 (78.32%) - files for which one or more png produced
Invalid PUML files: 44,902 (21.68%) - files for which no png image produces

### Post-Split Expectations

After splitting multi-diagram files:
- Each `.puml` file can generate more than 1 PNG image because of `newpage` keyword
- If `newpage` encountered separate png file was created with postfix _XXX (where X is numeric) e.g "{blob_id}_001.png"
- Total files in `puml/` increased after splitting
- Image generation becomes more predictable: 1 file = 1 image
- Files that fail will appear in `errors.log` have no corresponding image

## Metrics

The generation process now tracks:
- **File-level**: Total individual diagram files
- **Image-level**: Should equal total files minus error files
- **Success rate**: Can be calculated as (Total files - Error files) / Total files

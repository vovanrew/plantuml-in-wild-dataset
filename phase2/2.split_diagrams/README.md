# Split Multi-Diagram Files

Splits `.puml` files that contain multiple `@startuml...@enduml` blocks into individual one-diagram-per-file.

## Why

PlantUML image generation expects one diagram per file. Some source files from WoC contain multiple diagram blocks. This step try to achieve 1:1 mapping between `.puml` files and generated images (except diagrams with newpage keyword).

## Usage

```bash
# Split multi-diagram files
python3 split_multi_diagrams.py /path/to/puml /path/to/multi_diagram_originals

# Preview without making changes
python3 split_multi_diagrams.py /path/to/puml /path/to/multi_diagram_originals --dry-run
```

## Arguments

| Argument | Description |
|----------|-------------|
| `puml_dir` (positional) | Directory containing `.puml` files to process |
| `multi_diagram_originals_dir` (positional) | Directory to move original multi-diagram files to |
| `--dry-run` | Preview changes without splitting or moving files |

## How It Works

1. Scans all `.puml` files in the input directory
2. Finds `@start...@end...` blocks (case-insensitive, supports all PlantUML types: `@startuml`, `@startditaa`, `@startsalt`, etc.)
3. Files with a single diagram are left unchanged
4. Files with multiple diagrams are:
   - Split into `{blob_id}_01.puml`, `{blob_id}_02.puml`, etc.
   - Each split file gets the original header comments (Blob ID, Original Path, Source)
   - The original file is moved to the `multi_diagram_originals_dir` directory

## Example

Input file `abc123def.puml`:
```plantuml
' Blob ID: abc123def
' Original Path: /src/diagrams.puml

@startuml
class A
@enduml
@startuml
class B
@enduml
```

Output:
- `abc123def_01.puml` — header + class A diagram
- `abc123def_02.puml` — header + class B diagram
- Original moved to `multi_diagram_originals/abc123def.puml`

## Results

In the dataset pipeline, this step increased the file count from **200,144 to 207,161** (1,843 files had multiple diagrams).

# Phase 3, Step 3: Drop Non-UML Content

Removes diagrams classified as `non-uml` by the LLM — PlantUML-specific formats (@startmindmap, @startgantt, @startwbs, @startjson, etc.), ERD/database schemas, sprite/icon library definitions, empty diagrams, and other non-UML content.

## Why

The LLM classifier (step 1) identified 20,434 files (12.5% of 163,946) as `non-uml`. These include reusable graphical assets (`sprite` directives, `!define` macros), non-UML diagram formats (mindmaps, Gantt charts, wireframes), and other content that is syntactically valid PlantUML but not a standard UML diagram. They pass `@startuml`/`@enduml` validation but do not belong in a UML diagram dataset.

## Usage

```bash
# Preview what would be removed:
python3 filter_unclassified.py \
    --classification ../llm-classify-results/final_classification.json \
    --puml-dir /path/to/puml/ \
    --png-dir /path/to/png/ \
    --output ../llm-classify-results/final_classification_filtered.json \
    --dry-run

# Run for real:
python3 filter_unclassified.py \
    --classification ../llm-classify-results/final_classification.json \
    --puml-dir /path/to/puml/ \
    --png-dir /path/to/png/ \
    --output ../llm-classify-results/final_classification_filtered.json
```

## Inputs

| Argument | Description |
|----------|-------------|
| `--classification` | `final_classification.json` from step 1 (not modified) |
| `--puml-dir` | Root directory containing `.puml` files (flat or batch subdirs) |
| `--png-dir` | Root directory containing `.png` files (flat or batch subdirs) |
| `--output` | Path for the new filtered classification JSON |
| `--dry-run` | Report what would be deleted without touching anything |

## Outputs

- **Filtered JSON** at `--output` path, containing:
  - All original metadata plus filter metadata (`filter_timestamp`, `filter_excluded_count`, etc.)
  - Updated `statistics.type_distribution` (9 UML types, no `non-uml`)
  - Updated `statistics.classify_total_files` reflecting the reduced count
  - Only the kept entries in `classifications`
- **Deleted files**: corresponding `.puml` and `.png` files removed from disk

## Result

163,946 → **143,512** diagrams (20,434 removed). Downstream scripts (`count_lines.py`, `add_stats.py`, validation, visualizations) should use the filtered JSON.

# Phase 3, Step 3: Drop Non-UML Content

Removes diagrams classified as `unclassified` by the LLM — predominantly sprite/icon library definitions that are syntactically valid PlantUML but not UML diagrams.

## Why

The LLM classifier (step 1) identified 12,616 files (7.8% of 162,257) as `unclassified`. These are reusable graphical assets (`sprite` directives, `!define` macros) rather than UML diagrams. They pass `@startuml`/`@enduml` validation but do not belong in a UML diagram dataset.

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
  - Updated `statistics.type_distribution` (9 UML types, no `unclassified`)
  - Updated `statistics.classify_total_files` reflecting the reduced count
  - Only the kept entries in `classifications`
- **Deleted files**: corresponding `.puml` and `.png` files removed from disk

## Result

162,257 → **149,641** diagrams (12,616 removed). Downstream scripts (`count_lines.py`, `add_stats.py`, validation, visualizations) should use the filtered JSON.

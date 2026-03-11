# Validation Scripts

Cross-validate LLM diagram classifications against parser-extracted element data.

## Input Files

- **Classification JSON** (`uml_classifications.json`) — LLM-assigned `primary_type` per file, with top-level key `classifications`
- **Element stats JSONL** (`element_connection_counts.json`) — parser-extracted `diagram_type`, `elements`, and `connections` per file (one JSON object per line)

## Scripts

### compare_types.py

Compares LLM `primary_type` against the PlantUML compiler's `diagram_type`. Reports raw accuracy, taxonomy-adjusted accuracy (accounting for the compiler's coarser type system), confusion matrices, and top mismatches.

Taxonomy mapping (compiler uses fewer types):
- compiler `class` = LLM {class, object}
- compiler `component` = LLM {component, usecase, deployment}
- compiler `sequence`, `activity`, `state` map 1:1

```bash
# Basic usage
python3 compare_types.py -i uml_classifications.json -s element_connection_counts.json

# Save report as JSON
python3 compare_types.py -i uml_classifications.json -s element_connection_counts.json -o report.json
```

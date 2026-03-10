# Validation Scripts

Cross-validate LLM diagram classifications against parser-extracted element data.

## Input Files

Both scripts require two input files:

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

### validate_consistency.py

Validates each diagram's classified type against its detected elements. Computes a consistency score (0.0–1.0) per file based on whether expected elements are present and forbidden elements are absent. Flags misclassifications with severity levels (error/warning/info).

Flags detected:
- `TYPE_MISMATCH` — elements suggest a different diagram type
- `FORBIDDEN_ELEMENTS` — elements that shouldn't appear in the classified type
- `MISSING_PRIMARY_ELEMENTS` — no characteristic elements for the classified type
- `HIGH_CONFIDENCE_MISMATCH` — high classification confidence but low element consistency (only when confidence is available)
- `LOW_CONFIDENCE` — classification confidence below threshold (only when confidence is available)
- `NO_ELEMENTS` — no elements detected
- `MULTI_TYPE_AMBIGUOUS` — elements not strongly aligned with any single type

```bash
# Basic usage
python3 validate_consistency.py -i uml_classifications.json -s element_connection_counts.json

# Custom output path and consistency threshold
python3 validate_consistency.py -i uml_classifications.json -s element_connection_counts.json \
    -o validation_report.json -t 0.6

# Only show files with errors
python3 validate_consistency.py -i uml_classifications.json -s element_connection_counts.json \
    --severity-filter error --only-inconsistent
```

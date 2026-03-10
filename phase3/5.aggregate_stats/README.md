# 5. Aggregate Stats

Recompute aggregate statistics from per-record data in the classification JSON. Run these after any dataset modification (removing files, updating records, re-filtering) instead of re-running the full pipeline.

Each script reads per-record fields from `classifications` and overwrites the corresponding keys in `statistics` and `metadata`.

## Scripts

| Script | Updates | Source fields |
|--------|---------|---------------|
| `aggregate_types.py` | `type_distribution`, `total_files`, `uml`, `non_uml`, `mixed_type`, `truncated`, `classify_errored` | `primary_type`, `secondary_types`, `truncated`, `classify_error` |
| `aggregate_lines.py` | `lines_count_statistics`, `lines_count_distribution` | `content_lines` |
| `aggregate_elements.py` | `elements_statistics`, `elements_distribution`, `elements_type_totals`, `connections_statistics`, `connections_distribution`, `connections_type_totals`, `extraction_error_distribution`, `metadata.extraction_successful/errored` | `elements`, `elements_total`, `connections`, `connections_total`, `extraction_error` |

## Usage

All scripts accept `-i` (input JSON) and `-o` (output JSON). Input and output can be the same file for in-place updates.

```bash
# After removing records from the dataset:
python3 aggregate_types.py    -i uml_metadata.json -o uml_metadata.json
python3 aggregate_lines.py    -i uml_metadata.json -o uml_metadata.json
python3 aggregate_elements.py -i uml_metadata.json -o uml_metadata.json
```

Or run all three in sequence:

```bash
for script in aggregate_types.py aggregate_lines.py aggregate_elements.py; do
    python3 "$script" -i uml_metadata.json -o uml_metadata.json
done
```

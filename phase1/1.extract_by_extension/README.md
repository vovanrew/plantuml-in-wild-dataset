# Extract PlantUML Blob IDs by File Extension

Scans the World of Code basemap index to identify all blobs with PlantUML-related file extensions.

## What It Does

This script searches WoC's `lb2fFull` basemaps — 128 sharded gzipped files that map `blob_id;file_path`. It does **not** fetch file content; it only collects blob IDs and file paths where the extension matches PlantUML formats.

## Targeted Extensions

| Extension | Description |
|-----------|-------------|
| `.puml` | Standard PlantUML |
| `.pu` | Short form |
| `.plantuml` | Verbose form |
| `.wsd` | Web Sequence Diagrams |
| `.iuml` | Included UML |
| `.uml` | Generic UML |

## How It Works

1. **Parallel grep** across 128 basemap shards (`lb2fFullV{0..127}.s` at `/da8_data/basemaps/gz/`). Each shard is decompressed with `zcat` and filtered with `grep -iE` for the extensions above. Uses `nproc/2` parallel jobs to avoid overwhelming the system.

2. **Merge** all 128 per-shard results into a single `plantuml_files_all.gz`.

3. **Deduplicate by blob ID** using `sort -u -t\; -k1,1`. The same file content (same SHA-1 hash) can appear across many repositories; this keeps only one entry per unique blob.

## Usage

```bash
# Run on the WoC server (da0)
ssh da0
cd /data/play/$USER/plantuml_extraction
./extract_plantuml.sh
```

## Output

| File | Description |
|------|-------------|
| `plantuml_files_{0..127}.gz` | Per-shard grep results |
| `plantuml_files_all.gz` | Merged results (`blob_id;file_path`) |
| `unique_plantuml_blobs_with_files.gz` | Deduplicated by blob ID — input for the next step |

## Next Step

Feed `unique_plantuml_blobs_with_files.gz` into `2.extract_by_content/extract_plantuml_content.py` to fetch actual file content and validate PlantUML syntax.

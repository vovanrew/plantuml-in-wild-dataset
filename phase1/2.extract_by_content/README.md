# Extract PlantUML Content by Validation

Fetches actual file content from WoC blob storage and validates whether it contains PlantUML syntax.

## Why

The previous step (`1.extract_by_extension`) identified blobs by file extension alone. Many files with `.uml`, `.pu`, etc. extensions are not PlantUML — they may be XMI, other UML tool formats, or incomplete files. This step retrieves the content and checks for actual PlantUML markers.

## Validation Criteria

A blob is considered **valid** PlantUML if its content contains both:
- `@startuml` (or variants, case-insensitive)
- `@enduml` (case-insensitive)

## Usage

```bash
# Run on the WoC server
python3 extract_plantuml_content.py <input_file> <output_dir>

# Example
python3 extract_plantuml_content.py \
    /data/play/vopolva/plantuml_extraction/unique_plantuml_blobs_with_files.gz \
    /data/play/vopolva/plantuml_extraction

# Custom worker count and verbose logging
python3 extract_plantuml_content.py input.gz /output/dir -w 16 -v
```

## Arguments

| Argument | Description |
|----------|-------------|
| `input` (positional) | Gzipped file with `blob_id;file_path` pairs (from step 1) |
| `output_dir` (positional) | Directory for output files |
| `-w, --workers` | Number of parallel worker processes (default: half of CPU cores) |
| `-v, --verbose` | Enable debug logging |

## Architecture

The script uses a multi-process pipeline:

1. **Main process** — reads the gzipped input, parses `blob_id;file_path` lines, feeds them into a work queue
2. **Worker processes** — each creates its own `WocMapsLocal` instance, calls `woc.show_content("blob", blob_id)` to retrieve content, validates it, and Base64-encodes valid content
3. **Writer process** — collects results and writes to three output files

Queues are bounded for backpressure. Workers shut down via poison pill signals.

## Dependencies

- `python-woc` — for `WocMapsLocal` blob retrieval
- `tqdm` — optional, for progress bar

## Output

| File | Format | Description |
|------|--------|-------------|
| `valid_plantuml_content.gz` | `blob_id;file_path;base64_content` | Valid PlantUML blobs — input for Phase 2 |
| `invalid_blobs.txt` | `blob_id;file_path;reason` | Blobs missing `@startuml`/`@enduml` markers |
| `error_blobs.txt` | `blob_id;file_path;error` | Blobs that couldn't be retrieved from WoC |
| `plantuml_stats.json` | JSON | Processing statistics (counts, duration, speed) |

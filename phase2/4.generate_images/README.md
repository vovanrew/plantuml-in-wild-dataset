# Phase 2, Step 4: Generate Images

Compiles preprocessed `.puml` files into PNG images using PlantUML.

## Usage

```bash
./generate_images.sh <input-dir> <output-dir>
```

## PlantUML Command

The script runs:
```bash
java -jar plantuml-1.2025.9.jar \
    --threads auto \
    --output-dir <output-dir> \
    -tpng \
    -stdrpt \
    --no-error-image \
    "<input-dir>/*.puml"
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `--threads auto` | Parallel processing based on available CPU cores |
| `-tpng` | Output format: PNG |
| `-stdrpt` | Report errors to stderr (captured in `errors.log`) |
| `--no-error-image` | **Do not generate PNG for files with syntax errors.** Without this flag, PlantUML creates a red error-description image for every failed file. With it, only successfully compiled diagrams produce a PNG, making it easy to count valid vs invalid files by comparing input/output counts. |
| `--output-dir` | Resolved to an absolute path before passing to PlantUML, because PlantUML resolves relative paths relative to each input file, not the working directory |

## Inputs

- `.puml` files from the previous pipeline steps (split + normalized)
- `plantuml-1.2025.9.jar` (bundled in this directory)
- Java 11+

## Outputs

| File | Description |
|------|-------------|
| `<output-dir>/{blob_id}.png` | Generated diagram images |
| `<output-dir>/errors.log` | Compilation errors (syntax errors, missing includes, etc.) |
| `<output-dir>/generation_stats.txt` | Summary: total files, valid files, failed files, image count |

## Notes

- Files with compilation errors produce no output (due to `--no-error-image`), so the number of PNGs directly equals the number of valid diagrams
- The `newpage` keyword can produce multiple PNGs from a single `.puml` file (`{blob_id}_001.png`, `{blob_id}_002.png`, etc.), so image count may slightly exceed valid file count

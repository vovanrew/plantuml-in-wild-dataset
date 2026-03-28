# UML-in-the-Wild

**UML-in-the-Wild: A Dataset of UML Diagrams in PlantUML Notation from Open-Source Repositories**

Research dataset of 143,427 UML diagrams (9 standard types) extracted from open-source repositories via World of Code (WoC). Licensed CC-BY-4.0. Target publication: **MDPI Data** journal (data descriptor).

## Project Structure

```
pipeline_methodology.md                  # Main methodology document (source of truth for the paper)
classification_methodology.md   # LLM vs parser classification validation details
counting_methodology.md         # Parser-based element/connection extraction (Java tool)

phase1/                         # Data extraction (runs on WoC server)
  1.extract_by_extension/       # Grep 128 lb2fFull basemaps for .puml/.pu/.plantuml/.wsd/.iuml/.uml
  2.extract_by_content/         # Retrieve blobs via python-woc, validate @startuml/@enduml markers
  stats/                        # Per-extension validation rate analysis

phase2/                         # Preprocessing and image generation (local)
  1.generate_puml_files/        # Decode base64 → individual {blob_id}.puml files with metadata headers
  2.split_diagrams/             # Split multi-diagram files into {blob_id}_01.puml, _02.puml, etc.
  3.normalize_diagrams/         # Strip custom @startuml names to preserve blob-ID-based PNG naming
  4.generate_images/            # Compile with PlantUML 1.2025.9, validate puml↔png mapping

phase3/                              # Classification, analysis, validation
  1.classify_with_llm/               # Claude Haiku 4.5 via Batch API → 9 UML types + non-uml
  2.count_lines/                     # Line counts (content_lines, comment_lines) per diagram
  3.count_connections_and_elements/   # Join DiagramStatsExtractor JSONL into classification JSON
  4.cleanup/                         # Filter non-UML, DOT passthrough, and empty diagrams
  5.aggregate_stats/                 # Recompute type/line/element aggregate statistics
  6.manual_validation/               # Stratified sampling + expert review analysis
  auto_validation/                   # Cross-validation: LLM types vs parser types
  visualizations/                    # MDPI-compliant publication figures (fig1–fig4)
  common/                            # Shared preprocessing utilities (strip comments, styling, sprites, etc.)
```

## Pipeline Flow

Phase 1 (WoC server) → `valid_plantuml_content.gz` (blob_id;path;base64) →
Phase 2 (local) → `.puml` files + `.png` images →
Phase 3 (local) → classification JSON + validation reports + figures

## Key Conventions

- **File naming**: All files named by blob ID (40-char SHA-1 hex hash), not human-readable names
- **Metadata headers**: Each .puml file has comment lines: `' Blob ID:`, `' Original Path:`, `' Source: World of Code`
- **No 5-line filter**: The minimum line count filter was removed; all content-validated blobs proceed through the pipeline

## Methodology Documents

`pipeline_methodology.md` is the primary document describing the full pipeline for the paper. It references:
- `classification_methodology.md` for LLM vs parser classification validation
- `counting_methodology.md` for the Java-based DiagramStatsExtractor tool

When updating pipeline scripts, keep methodology docs in sync.

## Tools and Dependencies

- **Phase 1**: Runs on WoC da0–da8 servers. Requires `python-woc`, access to `/da8_data/basemaps/gz/`
- **Phase 2**: PlantUML 1.2025.9 JAR (bundled in `phase2/4.generate_images/`), Java 11+
- **Phase 3**: Anthropic API key (for LLM classification), matplotlib (for figures)
- **Element extraction**: Custom Java class `DiagramStatsExtractor` built within PlantUML source tree (separate repo)

## Common Tasks

- **Rerun pipeline**: Execute phases sequentially; phase2 step 1 reads phase1 output, each subsequent step reads the previous step's output in-place
- **Update methodology numbers**: After rerun, update all TBD values in `pipeline_methodology.md` §5.2 (compilation table), §6.1 (line distribution), and §8 (final stats)
- **Add visualization**: Follow existing pattern in `phase3/visualizations/` — 600 DPI, Arial font, 180mm width for MDPI compliance

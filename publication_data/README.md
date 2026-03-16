# UML-in-the-Wild: A Dataset of UML Diagrams in PlantUML Notation from Open-Source Repositories

A large-scale dataset of 143,427 UML diagrams extracted from open-source repositories via the World of Code (WoC) Version 3 infrastructure (October 2023 snapshot). Each diagram is provided as both PlantUML source code and a rendered PNG image, accompanied by rich metadata including diagram type classification, structural element and connection counts, and source repository attribution.

## Dataset Contents

```
README.md                          # This file
LICENSE                            # CC-BY-4.0 license
uml_metadata_enriched.json         # Metadata for all 143,427 diagrams
puml_files/                        # 143,427 PlantUML source files (.puml)
puml_images/                       # 144,487 rendered PNG images (.png)
```

The number of PNG images exceeds the number of source files because some diagrams use PlantUML's `newpage` keyword, which produces multiple images from a single source file.

For the full extraction pipeline, classification methodology, and element/connection counting methodology, see the accompanying data descriptor paper [2].

## Diagram Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| class | 73,958 | 51.6% |
| sequence | 35,233 | 24.6% |
| activity | 9,794 | 6.8% |
| component | 8,204 | 5.7% |
| usecase | 7,172 | 5.0% |
| state | 4,343 | 3.0% |
| object | 2,456 | 1.7% |
| deployment | 2,078 | 1.4% |
| timing | 189 | 0.1% |

These 9 types correspond to 9 of the 14 diagram types defined in the UML 2.5 specification. The 5 absent types (package, composite structure, interaction overview, communication, profile) are not natively supported by PlantUML's diagram syntax.

## Metadata Schema

The file `uml_metadata_enriched.json` contains three top-level keys: `metadata`, `statistics`, and `classifications`.

The `classifications` dictionary is keyed by filename (e.g., `5f95f42b5b392db1c75ab9f5c6eb514ac273e89e.puml`) with each entry containing:

| Field | Type | Description |
|-------|------|-------------|
| `blob_id` | string | 40-character SHA-1 hash (unique content identifier) |
| `original_path` | string | File path within the source repository |
| `repository` | string or null | WoC project identifier in `{username}_{reponame}` format |
| `diagram_type` | string | Always `"uml"` in this dataset |
| `primary_type` | string | Main UML diagram type (one of the 9 types above) |
| `secondary_types` | array | Additional types for mixed diagrams (empty for most) |
| `reasoning` | string | Brief explanation of the classification decision |
| `content_lines` | integer | Non-blank, non-comment lines (excluding markers and headers) |
| `elements` | object | Per-type element counts (e.g., `{"class": 5, "interface": 2}`) |
| `elements_total` | integer | Sum of all element counts |
| `connections` | object | Per-type connection counts (e.g., `{"extends": 3, "arrow": 7}`) |
| `connections_total` | integer | Sum of all connection counts |
| `extraction_error` | string or null | Parser error type if element extraction failed |

### Source Repository Attribution

The `repository` field provides a WoC project identifier from which the GitHub URL can be constructed as `https://github.com/{username}/{reponame}`. For 1,424 diagrams (1.0%), the WoC b2P mapping did not contain a project entry; these have `repository` set to `null`.

### File Naming Convention

All files are named by blob ID (40-character SHA-1 hex hash). Files originating from multi-diagram splitting use the pattern `{blob_id}_01.puml`, `{blob_id}_02.puml`, etc. Each `.puml` file contains metadata comment headers:

```
' Blob ID: 5f95f42b5b392db1c75ab9f5c6eb514ac273e89e
' Original Path: /src/main/java/ex42/App.puml
' Source: World of Code
@startuml
...
@enduml
```

## Known Limitations

- **Temporal scope**: The dataset reflects repositories indexed by WoC up to October 2023 and does not capture diagrams created or modified after that date.
- **Element/connection extraction gaps**: 347 diagrams (0.2%) have empty element and connection fields due to parser limitations. This includes 178 of 189 timing diagrams (94.2%) and 167 multi-page diagrams. Affected records are identified by the `extraction_error` field. Aggregate element/connection statistics in the metadata are computed over the 143,080 successfully extracted records.

## Usage Example (Python)

```python
import json

with open("uml_metadata_enriched.json") as f:
    data = json.load(f)

# Get all sequence diagrams
sequence_diagrams = [
    (name, info) for name, info in data["classifications"].items()
    if info["primary_type"] == "sequence"
]
print(f"Sequence diagrams: {len(sequence_diagrams)}")

# Access a specific diagram's metadata
entry = data["classifications"]["5f95f42b5b392db1c75ab9f5c6eb514ac273e89e.puml"]
print(f"Type: {entry['primary_type']}, Lines: {entry['content_lines']}")
print(f"Elements: {entry['elements']}, Connections: {entry['connections']}")

# Construct GitHub URL from repository field
if entry["repository"]:
    user, repo = entry["repository"].split("_", 1)
    print(f"Source: https://github.com/{user}/{repo}")
```

## Citation

If you use this dataset, please cite both the dataset and the accompanying paper:

```bibtex
@dataset{uml_in_the_wild_2026,
  title     = {UML-in-the-Wild: A Dataset of UML Diagrams in PlantUML Notation from Open-Source Repositories},
  doi       = {10.5281/zenodo.18952372},
  publisher = {Zenodo},
  year      = {2026}
}
```

```bibtex
% Accompanying data descriptor — to be updated after publication
```

## License

The dataset compilation (selection, arrangement, metadata, and pipeline scripts) is released under the **Creative Commons Attribution 4.0 International License (CC-BY-4.0)**.

Individual PlantUML source files and their rendered images remain under their original repository licenses. The `repository` and `original_path` metadata fields enable users to locate the source repository and verify its license. Aggregate and statistical use of the dataset falls under the CC-BY-4.0 compilation license.

## Acknowledgments

- **World of Code (WoC)** project, University of Tennessee, Knoxville — data source infrastructure [1]
- **PlantUML** (version 1.2025.9) — diagram compilation
- **Anthropic Claude Haiku 4.5** — diagram type classification

## References

[1] Y. Ma, T. Dey, C. Bogart, S. Amreen, M. Valiev, A. Tutko, D. Kennard, R. Zaretzki, and A. Mockus, "World of code: Enabling a research workflow for mining and analyzing the universe of open source VCS data," *Empirical Software Engineering*, vol. 26, no. 2, p. 22, 2021. doi: [10.1007/s10664-020-09905-9](https://doi.org/10.1007/s10664-020-09905-9)

[2] Accompanying data descriptor paper — forthcoming. This README will be updated with the full citation after publication.

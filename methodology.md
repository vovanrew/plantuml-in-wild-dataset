# Methodology

## 1. Data Source

The dataset was constructed using the World of Code (WoC) project [1], a comprehensive collection of open-source repositories maintained by the University of Tennessee, Knoxville. We utilized the WoC Version 3 snapshot dated October 6 2023, which provides access to over 200 million unique source code files through a distributed infrastructure across multiple servers.

The primary data structure used was the **lb2fFull basemap**, consisting of 128 sharded files that map blob identifiers (SHA-1 hashes) to their corresponding file paths in the format `blob_id;file_path`. These basemaps are stored in `/da8_data/basemaps/gz/` and provide comprehensive coverage of file-level metadata across the indexed repositories.

## 2. Data Extraction Pipeline

Our extraction methodology employed a two-stage approach to identify and retrieve UML diagrams from the WoC dataset. We targeted PlantUML source files as the extraction medium, since PlantUML is a widely adopted textual UML notation with dedicated file extensions that enable reliable identification in large-scale code corpora:

### 2.1 Stage 1: Extension-Based Identification

We performed parallel grep operations across all 128 lb2fFull basemap files to identify files with PlantUML-related extensions. The targeted extensions were:
- `.puml` (standard PlantUML)
- `.pu` (short form)
- `.plantuml` (verbose form)
- `.wsd` (Web Sequence Diagrams)
- `.iuml` (included UML)
- `.uml` (generic UML)

The extraction was parallelized using half of the available CPU cores, processing multiple basemap files concurrently. The initial grep operation across all 128 basemap files identified **504,451 total file entries** with PlantUML-related extensions.

Since WoC basemap (lb2fFull) store entries in the format `blob_id;file_path`, the same file content (identified by its SHA-1 blob hash) may appear multiple times with different paths across various repositories or branches. To ensure content-level uniqueness, we performed deduplication using `sort -u -t\; -k1,1` to retain only one instance of each unique blob identifier. This deduplication process reduced the dataset to **367,550 unique blob identifiers**, representing distinct PlantUML file contents regardless of their distribution across repositories.

### 2.2 Stage 2: Content Validation and Retrieval

For each identified blob, we retrieved the actual file content using the `python-woc` library's `WocMapsLocal` interface through the `extract_plantuml_content.py` script. This stage performed basic keyword-based filtration to validate PlantUML structure. Content validation criteria were:

1. **Marker presence**: Files must contain both `@startuml` (or variants) and `@enduml` markers (case-insensitive)
2. **Content accessibility**: Blob must be retrievable from WoC storage

This validation process filtered out files that had PlantUML-related extensions but did not contain actual PlantUML diagram syntax. Valid content was encoded using Base64 and stored in compressed format along with metadata (blob ID and original file path).

**Results** (out of 367,550 unique blobs):
- **Valid blobs**: 202,106 (55.0%) - containing proper PlantUML markers
- **Invalid blobs**: 163,802 (44.6%) - missing required markers (logged separately)
- **Error blobs**: 1,642 (0.4%) - WoC retrieval failures (logged separately)

**Validation rate by extension**:

| Extension | Valid | Invalid | Total | Valid Rate |
|-----------|-------|---------|-------|------------|
| `.plantuml` | 21,980 | 746 | 22,726 | 96.7% |
| `.puml` | 146,851 | 25,766 | 172,617 | 85.1% |
| `.pu` | 10,004 | 2,472 | 12,476 | 80.2% |
| `.wsd` | 14,862 | 8,709 | 23,571 | 63.1% |
| `.iuml` | 1,223 | 1,109 | 2,332 | 52.4% |
| `.uml` | 7,186 | 124,998 | 132,184 | 5.4% |

The validation rates vary significantly across extensions. The `.plantuml` and `.puml` extensions are strong indicators of actual PlantUML content (85–97% valid). In contrast, the generic `.uml` extension has only a 5.4% validation rate, as the vast majority of `.uml` files use other UML formats (e.g., XMI, Eclipse UML).

## 3. Deduplication

Deduplication was inherently performed at the blob level, as WoC's content-addressable storage ensures that identical file contents share the same SHA-1 hash. This guarantees syntactic uniqueness across the dataset.

## 4. Preprocessing and Normalization

The following preprocessing steps address PlantUML-specific syntax conventions to ensure consistent file naming and a one-to-one mapping between files and diagrams.

### 4.1 Multi-Diagram Splitting

Many source files contained multiple diagram blocks within a single file. Out of the 202,106 validated files, **1,842 files (0.9%)** contained multiple PlantUML diagrams. We developed a splitting algorithm using regex patterns to:
- Detect multiple `@startuml...@enduml` blocks within a single file
- Handle case-insensitive variations (`@StartUML`, `@STARTUML`)
- Support different diagram types (`@startditaa`, `@startsalt`)
- Preserve metadata headers (blob ID, file path, source attribution)

Each diagram block was extracted into a separate file with naming convention `{blob_id}_01.puml`, `{blob_id}_02.puml`, etc., ensuring a one-to-one mapping between files and diagrams.

**Results**: The splitting process increased the total file count from **202,106 to 209,122** individual diagram files, extracting all embedded diagrams from multi-diagram files while preserving single-diagram files unchanged.

### 4.2 Tag Normalization

Custom naming in `@startuml` tags (e.g., `@startuml{name}` or `@startuml name`) causes PlantUML to use the custom name in the output PNG filename rather than the source file name. Since our file naming convention is based on blob IDs (e.g., `{blob_id}.puml` → `{blob_id}.png`), preserving these custom names would break the metadata consistency embedded in filenames.

We normalized these patterns to standard `@startuml` format, stripping all custom names regardless of syntax (`{name}`, `(name)`, `[name]`, and space-separated names). This ensures that:
- PNG output files maintain the same blob_id-based naming as their source PUML files
- Metadata remains accessible through filenames
- The blob_id to file mapping remains consistent across both formats

Even when the `newpage` keyword generates multiple PNG files from a single PUML source, the outputs follow the pattern `{blob_id}_001.png`, `{blob_id}_002.png`, etc., preserving the blob_id reference with numeric suffixes.

**Results**: Out of 209,122 files, **35,612 (17.0%)** contained custom `@startuml` names and were normalized. The remaining 173,510 files required no modification.

## 5. Image Generation and Validation

### 5.1 Compilation Process

We used **PlantUML version 1.2025.9** to generate PNG images from the preprocessed `.puml` files. The generation process utilized:
- **Command**: `java -jar plantuml.jar -tpng --threads auto --no-error-image -stdrpt`
- **Parallel processing**: Automatic thread allocation based on system resources
- **Error handling**: Comprehensive logging of syntax errors to `errors.log`

### 5.2 Validation Results

The compilation process provided syntactic validation of diagram correctness:

| Metric | Count |
|--------|-------|
| Total files processed | 209,122 |
| Successfully compiled | 163,946 |
| Compilation errors | 45,176 |
| Generated PNG images | 165,177 |

The number of generated images may slightly exceed the number of successfully compiled files due to the PlantUML `newpage` keyword, which generates multiple images from a single source file.

Files with compilation errors were logged separately and could serve as a complementary dataset for error analysis and tool improvement research.

## 6. Dataset Analysis Framework

### 6.1 Textual Size Metrics

We implemented automated analysis to characterize diagram size using line counts in the PlantUML source notation. These metrics reflect the textual size of the PlantUML specification rather than abstract UML complexity, as the same diagram may require a different number of lines in other representations (e.g., XMI, graphical editors).

- **Line metric**: `content_lines` — non-blank, non-comment lines (excluding metadata header, `@startuml/@enduml` markers)
- **Distribution** (logarithmic bins for right-skewed data):

| Lines | Count | Percentage |
|-------|-------|------------|
| 1-10 | 32,870 | 22.9% |
| 11-100 | 101,098 | 70.5% |
| 101-1000 | 9,338 | 6.5% |
| 1001+ | 121 | 0.1% |

**Summary Statistics**: min = 1, max = 31,784, mean = 39.34, median = 22, Q1 = 11, Q3 = 42

### 6.2 Diagram Type Classification

We developed an LLM-based classifier using Claude Haiku 4.5 to categorize compiled diagrams into standard UML diagram types and to identify non-UML content for exclusion. The classifier leverages Anthropic's Message Batches API for cost-effective processing of all 163,946 compiled diagrams.

#### 6.2.1 Supported Diagram Types

The classifier assigns each diagram to one of 9 standard UML types or labels it as `non-uml` for exclusion:
- **UML Diagrams**: sequence, class, activity, state, usecase, component, deployment, object, timing
- **Non-UML** (`non-uml`): Content that does not constitute a standard UML diagram. This label identifies files for removal from the final dataset and encompasses PlantUML-specific formats (`@startmindmap`, `@startgantt`, `@startwbs`, `@startjson`, etc.), sprite/icon library definitions, ERD/database schemas, auto-generated non-UML visualizations (e.g., Helm chart dependency maps), and files not recognizable as any diagram type

These 9 types correspond to 9 of the 14 diagram types defined in the UML 2.5 specification. The 5 types absent from the dataset — package, composite structure, interaction overview, communication, and profile diagrams — are not natively supported by PlantUML's diagram syntax and therefore do not appear in the source corpus.

#### 6.2.2 Preprocessing Pipeline

Before classification, each diagram undergoes lightweight preprocessing that preserves high-value classification signals while removing token-wasting noise:

**Preserved** (high classification value for LLM):
- Human comments (domain context clues)
- `skinparam`/`hide`/`show`/`style` blocks (contain type-naming keywords)
- `!include` lines (stdlib library references are strong type signals)
- `!define` lines (macro mappings reveal actual diagram element types)
- Salt blocks (`@startsalt...@endsalt` for wireframe detection)
- Title lines (often explicitly name the diagram type)

**Removed** (no classification value):
1. **Metadata Headers**: Pipeline-generated comment headers (`Blob ID`, `Original Path`, `Source`)
2. **Sprite Definitions**: Hex/raster sprites and SVG inline sprites (binary noise)
3. **Preprocessor Bodies**: `!procedure`/`!function` blocks, `!$variable` assignments
4. **Hyperlink Syntax**: `[[url]]` double-bracket links
5. **Note Collapsing**: Multi-line notes collapsed to `[note]` markers; long single-line notes truncated
6. **Documentation Blocks**: `header`, `footer`, `legend`, `caption` blocks (but NOT `title`)
7. **Excessive Blank Lines**: Collapsed to single blank lines

#### 6.2.3 Classification Process

**Model**: `claude-haiku-4-5-20251001`
**API**: Anthropic Message Batches API (batch size: 100,000 requests)

For each diagram, the classifier:
1. Preprocesses content using the pipeline above
2. Truncates files exceeding 5,000 words to 4,000 words (preserves beginning)
3. Submits to Claude with a structured prompt requesting JSON output
4. Extracts diagram type from structured JSON response

**Output Format**:
- `primary_type`: Main diagram type
- `secondary_types`: Array of additional types (empty for most diagrams; populated only when a diagram genuinely combines multiple UML types)
- `reasoning`: Brief explanation of classification decision

#### 6.2.4 Classification Criteria

The prompt instructs the model to identify diagrams based on characteristic features:

| Type | Key Features |
|------|--------------|
| sequence | `participant`, `->`, `activate`, `alt`, `loop` |
| class | `class`, `interface`, `extends`, inheritance arrows |
| activity | `start`, `stop`, `:action;`, `if/then/else` |
| state | `[*]`, `state`, `-->` transitions |
| usecase | `(usecase)`, `:actor:`, system boundaries |
| component | `[component]`, `interface`, `package` |
| deployment | `node`, `artifact`, `device`, `cloud` |
| object | `object`, `map`, field assignments |
| timing | `@time`, `robust`, `concise` |

#### 6.2.5 Classification Results and Non-UML Filtering

The classifier assigned a type to all 163,946 compiled diagrams. Of these, 20,434 (12.5%) were classified as `non-uml` — predominantly sprite/icon library definitions, PlantUML-specific non-UML formats (`@startmindmap`, `@startgantt`, `@startwbs`, `@startjson`, `@startsalt`, `@startditaa`, `@startnwdiag`, `@startdot`), ERD/database schemas, and auto-generated infrastructure visualizations (e.g., Helm chart dependency maps). Since the dataset targets standard UML diagrams, these entries were excluded.

To validate the classifier's non-UML labeling, we performed a manual review of a random sample of 100 entries drawn from the `non-uml` category. A domain expert examined each source file and confirmed 100% agreement with the classifier's decision, supporting the reliability of the automated filtering.

After removing non-UML content, the dataset contains **143,512 UML diagrams**. Two additional filtering steps further refined the dataset: (1) removal of 84 Graphviz DOT passthrough diagrams — files using raw `digraph`/`graph` DOT syntax within `@startuml` blocks, which PlantUML forwards to Graphviz without building a UML diagram model, identified via the parser-based extraction tool's `unsupported_type:PSystemDot` error; and (2) removal of 1 empty diagram with zero content lines. The final dataset contains **143,427 UML diagrams** distributed across 9 standard UML types:

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

# 6.3 Parser-Based Element and Connection Extraction Methodology
In `classification_methodology.md` and `counting_methodology.md`

## 7. Metadata and Reproducibility

### 7.1 Metadata Structure

Each diagram in the final dataset is associated with comprehensive metadata:
- **Blob ID**: SHA-1 hash serving as unique identifier
- **Original path** (`original_path`): File path within the source repository (e.g., `/src/main/java/ex42/App.puml`)
- **Repository** (`repository`): WoC project identifier from the b2P mapping, in the format `{username}_{reponame}` (e.g., `HaoQNguyen_nguyen-COP3330-assignment3`). The corresponding GitHub URL can be constructed as `https://github.com/{username}/{reponame}`. For 1,424 diagrams (1.0%), the WoC b2P mapping did not contain a project entry for the blob; these have `repository` set to `null`. The diagrams are retained in the dataset as they are valid UML content — the missing attribution reflects incomplete coverage of the WoC b2P basemap, not a data quality issue
- **Diagram type**: LLM classification result (primary_type, secondary_types, reasoning)
- **Line metrics**: `content_lines` count
- **Element counts**: Per-type element counts (e.g., `{"class": 5, "interface": 2}`)
- **Connection counts**: Per-type connection counts (e.g., `{"inheritance": 5, "composition": 3}`)

### 7.2 Reproducibility

All extraction, processing, and analysis scripts are version-controlled and documented. The pipeline can be reproduced given:
- Access to WoC infrastructure (or alternative WoC data exports)
- PlantUML JAR file (version 1.2025.9 or compatible)
- Python 3.8+ with `python-woc` library
- Standard Unix utilities (grep, sed, sort, zcat)

## 8. Final Dataset Statistics

**Extraction Summary**:
- Initial candidates (extension-based): 504,451 total file entries
- After deduplication: 367,550 unique blobs
- Content-validated: 202,106 blobs (55.0% validation rate)
- After multi-diagram splitting: 209,122 files
- Successfully compiled: 163,946 diagrams
- After non-UML filtering: 143,512 UML diagrams
- After DOT passthrough removal: 143,428 UML diagrams
- After empty diagram removal: 143,427 UML diagrams

**Dataset Composition**:
- Total UML diagrams: 143,427
- Diagram types: 9 standard UML types (class, sequence, activity, component, usecase, state, object, deployment, timing)
- Format: PNG images + PlantUML source code
- Metadata: JSON format with blob-level attribution

## 9. Limitations

### 9.1 Temporal Scope

The dataset is derived exclusively from World of Code (WoC) Version 3, a snapshot dated October 6, 2023. It therefore reflects the state of open-source repositories indexed up to that date and does not capture PlantUML diagrams created or modified after the snapshot. Any future replication using a newer WoC version may yield different counts and distributions as repositories evolve.

### 9.2 Parser-Based Extraction Coverage

The Java-based DiagramStatsExtractor used for element and connection counting does not support all PlantUML diagram types. Of the 143,427 diagrams in the final dataset, 347 (0.2%) could not be processed by the parser, resulting in empty element and connection fields (`elements_total = 0`, `connections_total = 0`). The aggregate element and connection statistics (distributions, mean, median, quartiles) reported in the metadata are computed over the 143,080 successfully extracted records only.

The extraction failures break down as follows:

| Error Type | Count | Description |
|------------|-------|-------------|
| `unsupported_type:TimingDiagram` | 178 | Timing diagrams not supported by the parser |
| `unsupported_type:NewpagedDiagram` | 167 | Multi-page diagrams not supported by the parser |
| `unsupported_type:PSystemMath` | 1 | Math formula block |
| `unsupported_type:PSystemVersion` | 1 | Version info block |

Notably, 178 of the 189 timing diagrams (94.2%) lack element and connection data due to the parser limitation. Only 11 timing diagrams were successfully parsed. Researchers using element/connection counts for timing diagrams should be aware of this near-complete gap. The `extraction_error` field in the metadata identifies all affected records.

## 10. Ethical Considerations and Licensing

All source code was obtained from publicly accessible repositories indexed by the World of Code project. The dataset preserves attribution to original repositories through blob-to-project mappings, enabling proper citation and license compliance. Users of this dataset are advised to respect the licenses of source repositories when utilizing the diagrams for research or commercial purposes.

### 10.1 Dataset License

The **dataset compilation** — including the selection and arrangement of diagrams, all metadata (classification labels, element/connection counts, line metrics), and the pipeline scripts — is released under the **Creative Commons Attribution 4.0 International License (CC-BY-4.0)**. This license allows:
- **Sharing**: Copying and redistributing the material in any medium or format
- **Adaptation**: Remixing, transforming, and building upon the material for any purpose, including commercial use

Under the condition that appropriate credit is given, a link to the license is provided, and any changes are indicated.

**Important**: CC-BY-4.0 applies to the dataset as a curated collection, not to the individual PlantUML source files or their rendered images. Each source file originates from an open-source repository with its own license (e.g., MIT, Apache-2.0, GPL, or others). Users must consult the original repository license before reusing individual files beyond research fair-use. The metadata includes source repository attribution (via WoC blob-to-project mapping) to facilitate license verification. This approach is consistent with established research code datasets such as The Stack and CodeSearchNet, which similarly distinguish between compilation-level and file-level licensing.

### 10.2 Attribution Requirements

When using this dataset, please:
1. **Cite the dataset** using the Zenodo DOI: [DOI PLACEHOLDER - to be updated after upload]
2. **Acknowledge the data source**: World of Code (WoC) Version 3 (October 2023 snapshot)
3. **Verify original licenses before file-level reuse**: Individual PlantUML source files and their rendered images remain under their original repository licenses. The metadata provides the `repository` field (WoC project identifier in `{username}_{reponame}` format) and the `original_path` field, from which the source GitHub repository can be located and its license verified. Aggregate and statistical use of the dataset (e.g., corpus-level analysis, diagram type distributions) falls under the CC-BY-4.0 compilation license

### 10.3 Data Provenance

Each diagram in the dataset includes metadata linking back to its source repository through two fields: (1) `repository` — a WoC project identifier derived from the blob-to-project (b2P) mapping, stored in `{username}_{reponame}` format (e.g., `HaoQNguyen_nguyen-COP3330-assignment3`), from which the GitHub URL can be constructed as `https://github.com/{username}/{reponame}`; and (2) `original_path` — the file path within that repository (e.g., `/src/main/java/ex42/App.puml`). Together, these provide full traceability from any diagram in the dataset to its origin, enabling users to verify original licensing terms, inspect surrounding project context, and ensure compliance when reusing individual files beyond the scope of the CC-BY-4.0 compilation license.

**Tools and Dependencies**:
- World of Code V3 (Oct 7 2023 snapshot)
- PlantUML 1.2025.9
- Python 3.8+ (libraries: python-woc, multiprocessing, base64, gzip, json, re)
- Java Runtime Environment 11+
- GNU utilities: grep, sed, sort, find, zcat

## References

[1] Y. Ma, T. Dey, C. Bogart, S. Amreen, M. Valiev, A. Tutko, D. Kennard, R. Zaretzki, and A. Mockus, "World of code: Enabling a research workflow for mining and analyzing the universe of open source VCS data," *Empirical Software Engineering*, vol. 26, no. 2, p. 22, 2021. doi: [10.1007/s10664-020-09905-9](https://doi.org/10.1007/s10664-020-09905-9)

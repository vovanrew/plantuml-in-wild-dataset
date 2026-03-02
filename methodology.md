# Methodology

## 1. Data Source

The dataset was constructed using the World of Code (WoC) project, a comprehensive collection of open-source repositories maintained by the University of Tennessee, Knoxville. We utilized the WoC Version 3 snapshot dated October 6 2023, which provides access to over 200 million unique source code files through a distributed infrastructure across multiple servers.

The primary data structure used was the **lb2fFull basemap**, consisting of 128 sharded files that map blob identifiers (SHA-1 hashes) to their corresponding file paths in the format `blob_id;file_path`. These basemaps are stored in `/da8_data/basemaps/gz/` and provide comprehensive coverage of file-level metadata across the indexed repositories.

## 2. Data Extraction Pipeline

Our extraction methodology employed a two-stage approach to identify and retrieve PlantUML diagrams from the WoC dataset:

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
| Successfully compiled | TBD |
| Compilation errors | TBD |
| Generated PNG images | TBD |

The number of generated images may slightly exceed the number of successfully compiled files due to the PlantUML `newpage` keyword, which generates multiple images from a single source file.

Files with compilation errors were logged separately and could serve as a complementary dataset for error analysis and tool improvement research.

## 6. Dataset Analysis Framework

### 6.1 Complexity Metrics

We implemented automated analysis to characterize diagram complexity:
- **Line metrics**:
  - `content_lines`: Non-blank, non-comment lines (excluding metadata header, `@startuml/@enduml` markers)
  - `comment_lines`: Pure comment lines
- **Distribution** (logarithmic bins for right-skewed data):

| Lines | Count | Percentage |
|-------|-------|------------|
| 1-10 | TBD | TBD |
| 11-100 | TBD | TBD |
| 101-1000 | TBD | TBD |
| 1001+ | TBD | TBD |

**Summary Statistics**: TBD

### 6.2 Diagram Type Classification

We developed an LLM-based classifier using Claude Haiku 4.5 to categorize PlantUML diagrams into UML diagram types. The classifier leverages Anthropic's Message Batches API for cost-effective processing of the full dataset (162k+ diagrams).

#### 6.2.1 Supported Diagram Types

The classifier identifies 10 diagram categories:
- **UML Diagrams**: sequence, class, activity, state, usecase, component, deployment, object
- **Unclassified**: Diagrams without recognizable UML patterns (library files, sprites, minimal content)

#### 6.2.2 Preprocessing Pipeline

Before classification, each diagram undergoes preprocessing to remove non-semantic content that could cause false positives:

1. **Comment Stripping**: Single-line (`'`), multi-line (`/' ... '/`), and inline comments
2. **Styling Block Removal**: `skinparam`, `hide/show` directives, `style` blocks
3. **Sprite Definition Removal**: Hex/raster sprites and SVG inline sprites
4. **Preprocessor Directive Removal**: `!define`, `!include`, `!procedure`, `!function` blocks
5. **Note Block Removal**: Single-line, multi-line, and floating notes
6. **Documentation Block Removal**: `header`, `footer`, `title`, `legend`, `caption` blocks

#### 6.2.3 Classification Process

**Model**: `claude-haiku-4-5-20251001`
**API**: Anthropic Message Batches API (batch size: 100,000 requests)

For each diagram, the classifier:
1. Preprocesses content using the pipeline above
2. Truncates files exceeding 5,000 words to 4,000 words (preserves beginning)
3. Submits to Claude with a structured prompt requesting JSON output
4. Extracts diagram types with confidence scores (0.0-1.0)

**Output Format**:
- `primary_type`: Highest-confidence diagram type
- `types`: Dictionary of all detected types with confidence scores
- `confidence`: Primary type confidence value
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

#### 6.2.5 Classification Stats

**Type Distribution**:

| Type | Count | Percentage |
|------|-------|------------|
| class | 73,865 | 45.5% |
| sequence | 35,229 | 21.7% |
| unclassified | 12,616 | 7.8% |
| activity | 9,836 | 6.1% |
| component | 8,215 | 5.1% |
| usecase | 7,460 | 4.6% |
| deployment | 5,972 | 3.7% |
| object | 4,419 | 2.7% |
| state | 4,359 | 2.7% |
| timing | 286 | 0.2% |

# 6.3 Parser-Based Element and Connection Extraction Methodology
In @classification_and_counting_methodology.md

## 7. Metadata and Reproducibility

### 7.1 Metadata Structure

Each diagram in the final dataset is associated with comprehensive metadata:
- **Blob ID**: SHA-1 hash serving as unique identifier
- **Original file path**: Path in source repository
- **Source repository**: GitHub URL (via WoC b2P mapping)
- **Diagram type**: LLM classification result with confidence score
- **Line metrics**: `content_lines` and `comment_lines` counts
- **Element counts**: Per-type element counts (e.g., `{"class": 5, "interface": 2}`)
- **Connection counts**: Per-category connection counts (e.g., `{"structural": 12}`)
- **Consistency score**: Validation score (0.0-1.0) indicating classification confidence
- **Validation flags**: Any detected issues from cross-validation

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
- Successfully compiled: TBD diagrams
- Generated images: TBD PNG files

**Dataset Composition**:
- Total diagrams: TBD
- Format: PNG images + PlantUML source code
- Metadata: JSON format with blob-level attribution

## 9. Ethical Considerations and Licensing

All source code was obtained from publicly accessible repositories indexed by the World of Code project. The dataset preserves attribution to original repositories through blob-to-project mappings, enabling proper citation and license compliance. Users of this dataset are advised to respect the licenses of source repositories when utilizing the diagrams for research or commercial purposes.

### 9.1 Dataset License

This dataset is released under the **Creative Commons Attribution 4.0 International License (CC-BY-4.0)**. This license allows:
- **Sharing**: Copying and redistributing the material in any medium or format
- **Adaptation**: Remixing, transforming, and building upon the material for any purpose, including commercial use

Under the condition that appropriate credit is given, a link to the license is provided, and any changes are indicated.

### 9.2 Attribution Requirements

When using this dataset, please:
1. **Cite the dataset** using the Zenodo DOI: [DOI PLACEHOLDER - to be updated after upload]
2. **Acknowledge the data source**: World of Code (WoC) Version 3 (October 2023 snapshot)
3. **Respect original repository licenses**: Individual diagrams may be subject to their original repository licenses. The metadata includes source repository URLs (`file_path` field) to facilitate license verification

### 9.3 Data Provenance

Each diagram in the dataset includes metadata linking back to its source repository, ensuring full traceability and enabling users to verify original licensing terms when required for specific use cases.

**Tools and Dependencies**:
- World of Code V3 (Oct 7 2023 snapshot)
- PlantUML 1.2025.9
- Python 3.8+ (libraries: python-woc, multiprocessing, base64, gzip, json, re)
- Java Runtime Environment 11+
- GNU utilities: grep, sed, sort, find, zcat

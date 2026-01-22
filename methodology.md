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

## 3. Filtering and Quality Control

### 3.1 Length-Based Filtering

To ensure diagram complexity and completeness, we applied a minimum threshold filter:
- **Minimum requirement**: 5 non-empty lines of PlantUML code (excluding whitespace)
- **Rationale**: Eliminates trivial or incomplete diagram fragments

This filter reduced the dataset to **200,144 PlantUML files** while tracking line count distribution statistics for subsequent analysis.

### 3.2 Deduplication

Deduplication was inherently performed at the blob level, as WoC's content-addressable storage ensures that identical file contents share the same SHA-1 hash. This guarantees syntactic uniqueness across the dataset.

## 4. Preprocessing and Normalization

### 4.1 Multi-Diagram Splitting

Many source files contained multiple diagram blocks within a single file. Out of the 200,144 files after length-based filtering, **1,843 files (0.9%)** contained multiple PlantUML diagrams. We developed a splitting algorithm using flexible regex patterns to:
- Detect multiple `@startuml...@enduml` blocks within a single file
- Handle case-insensitive variations (`@StartUML`, `@STARTUML`)
- Support different diagram types (`@startditaa`, `@startsalt`)
- Preserve metadata headers (blob ID, file path, source attribution)

Each diagram block was extracted into a separate file with naming convention `{blob_id}_01.puml`, `{blob_id}_02.puml`, etc., ensuring a one-to-one mapping between files and diagrams.

**Results**: The splitting process increased the total file count from **200,144 to 207,161** individual diagram files, extracting all embedded diagrams from multi-diagram files while preserving single-diagram files unchanged.

### 4.2 Tag Normalization

Custom naming in `@startuml` tags (e.g., `@startuml{name}` or `@startuml name`) causes PlantUML to use the custom name in the output PNG filename rather than the source file name. Since our file naming convention is based on blob IDs (e.g., `{blob_id}.puml` → `{blob_id}.png`), preserving these custom names would break the metadata consistency embedded in filenames.

We normalized these patterns to standard `@startuml` format while preserving valid PlantUML parameters such as `@startuml(id=...)` or `@startuml[scale=...]`. This ensures that:
- PNG output files maintain the same blob_id-based naming as their source PUML files
- Metadata remains accessible through filenames
- The blob_id to file mapping remains consistent across both formats

Even when the `newpage` keyword generates multiple PNG files from a single PUML source, the outputs follow the pattern `{blob_id}_001.png`, `{blob_id}_002.png`, etc., preserving the blob_id reference with numeric suffixes.

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
| Total files processed | 207,161 |
| Successfully compiled | 162,257 (78%) |
| Compilation errors | 44,803 (22%) |
| Generated PNG images | 163,589 |

The slight excess of images over valid files (163,589 .png vs. 162,257 .puml) is due to the PlantUML `newpage` keyword, which generates multiple images from a single source file.

Files with compilation errors were logged separately and could serve as a complementary dataset for error analysis and tool improvement research.



---------------------------------------------------------------------------------
---------------------------------------------------------------------------------
---------------------------------------------------------------------------------



## 6. Dataset Analysis Framework

### 6.1 Complexity Metrics

We implemented automated analysis to characterize diagram complexity:
- **Line count**: Non-blank, non-comment lines (excluding `@startuml/@enduml` markers)
- **Complexity categories**:
  - Simple: < 10 lines
  - Medium: 10-50 lines
  - Complex: > 50 lines

### 6.2 Diagram Type Classification

We developed a hierarchical rule-based classifier to automatically categorize PlantUML diagrams into their respective UML diagram types. The classifier supports 9 UML diagram types (sequence, class, activity, state, use case, component, deployment, object, timing) plus 4 non-UML types (Graphviz, Ditaa, Salt, Gantt).

#### 6.2.1 Classification Architecture

The classification pipeline consists of six stages:

1. **Comment Stripping**: Removal of PlantUML comments (single-line `'` and multi-line `/' ... '/`) to prevent false keyword detection in documentation
2. **Styling Block Removal**: Elimination of non-semantic configuration blocks (`skinparam`, `hide`, `show`, `style`) that contain diagram type keywords in styling context, preventing false positives from presentation markup
3. **Preprocessor Directive Removal**: Stripping of PlantUML preprocessor directives (`!define`, `!include`, `!procedure`, `!function`) that are meta-programming constructs for reusable components, not diagram content. This prevents icon/sprite library files from being misclassified based on macro parameter patterns like `(_alias)` matching use case parentheses syntax
4. **Feature Extraction**: Detection of 80+ diagram-specific features including keywords, syntax patterns, and structural elements
5. **Hierarchical Scoring**: Four-tier weighted scoring system with exponential multipliers
6. **Normalization and Thresholding**: Score normalization and multi-label classification support

#### 6.2.2 Hierarchical Feature Tier System

Unlike traditional flat scoring systems where all features contribute equal weight, our classifier employs a **4-tier hierarchy** with exponential multipliers to ensure decisive features dominate classification:

**Tier Structure:**
- **Tier 1 (Decisive)**: 100x multiplier - Unique/definitive features that nearly guarantee diagram type
- **Tier 2 (Strong)**: 10x multiplier - Highly characteristic features with minimal ambiguity
- **Tier 3 (Moderate)**: 1x multiplier - Common features that may appear across multiple types
- **Tier 4 (Weak)**: 0.1x multiplier - Ambiguous features requiring contextual interpretation

**Example Weight Calculation:**
```
Sequence Diagram with:
- has_participant (Tier 1, base weight 1.5): 1.5 × 100 = 150 points
- has_alt_loop (Tier 2, base weight 2.5): 2.5 × 10 = 25 points
- has_end (Tier 3, base weight 0.5): 0.5 × 1 = 0.5 points
Total raw score: 175.5 points (normalized across all diagram types)
```

This exponential weighting ensures that a single Tier 1 feature (e.g., `has_member_visibility` for class diagrams) dominates hundreds of weak signals, preventing noise accumulation and improving classification accuracy.

#### 6.2.3 Feature Extraction

The feature extraction system identifies diagram-specific patterns through regex-based detection:

**Sequence Diagram Features:**
- Core: `participant`, `actor`, `activate`, message arrows (`->`, `-->`)
- Lifecycle: `**` (create), `!!` (destroy), `++`/`--` (activation shortcuts)
- Control flow: `alt`, `loop`, `opt`, `par`, `else`, `end`
- Special: `autonumber`, `ref over`, lost messages (`-->x`)

**Activity Diagram Features:**
- New syntax: `:action;`, `|Swimlane|`, `fork again`, `split`, `elseif`
- Old syntax: `(*)` markers, `===` synchronization bars
- Unique keywords: `switch`, `case`, `backward`, `kill`, `detach`
- Shared: `start`, `stop`, `partition`, `if/then/else`, `while`

**Class Diagram Features:**
- Distinctive: Member visibility (`+`, `-`, `#`, `~`), `abstract`, `interface`
- Relationships: Inheritance (`<|--`), realization (`<|..`), composition (`*--`), aggregation (`o--`)
- Elements: `class`, `enum`, association classes

**State Diagram Features:**
- Unique: History states (`[H]` shallow, `[H*]` deep)
- Pseudo-states: `<<choice>>`, `<<entryPoint>>`, `<<exitPoint>>`, `<<fork>>`, `<<join>>`
- Markers: `[*]` (initial/final states), composite states (`state X { ... }`)

**Component Diagram Features:**
- Highly distinctive: Port keywords (`port`, `portin`, `portout`)
- Elements: `component`, `[ComponentName]` bracket notation, interface symbols `()`
- Grouping: `package`, `database`, `folder`, `cloud`, `frame`

**Deployment Diagram Features:**
- Physical hardware: `artifact`, `device`, `storage`, `server`, `container`
- Infrastructure: `node`, `deployment`, execution environment stereotypes
- Nesting patterns: `node { ... }`, `cloud { ... }`

**Use Case Diagram Features:**
- Notation: `(Use Case)` parentheses, `:Actor:` colons
- Relationships: `<<extend>>`, `<<include>>`, `rectangle` (system boundary)

**Object Diagram Features:**
- Unique: `map` keyword, `=>` key-value separator
- Elements: `object`, instance notation (`name : Type`), field assignments

**Timing Diagram Features:**
- Participants: `robust`, `concise`, `binary`, `clock`, `analog`
- Time notation: `@` symbols (`@0`, `@+10`), time constraints (`<->`)
- State control: `has` keyword, `is` state assignments, `hide time-axis`

#### 6.2.4 Context-Aware Feature Adjustment

Ambiguous features that appear in multiple diagram types receive **dynamic weight adjustment** based on surrounding context:

- `has_interface`: High weight (2.8) in class diagrams when `has_class` or `has_member_visibility` present; high weight in component diagrams when `has_component` present; otherwise low weight (0.5)
- `has_node`: High weight (2.0) in deployment diagrams when `has_artifact` present; high weight (1.8) in component diagrams when artifact absent; otherwise low weight
- `has_actor`: High weight (1.2) in use case diagrams when use case markers present; medium weight in sequence diagrams with many arrows; otherwise weak weight (0.4)

This context-awareness prevents misclassification when shared keywords have different semantic meanings across diagram types.

#### 6.2.5 Conflict Resolution and Penalties

When conflicting Tier 1 or Tier 2 features from different diagram types are detected, **hierarchical penalties** reduce scores to prevent false positives:

- **Sequence vs Activity**: If activity-unique keywords detected (`switch`, `backward`, `kill`), sequence score penalized by 0.3-0.4x
- **Class vs Component**: If component ports detected (`portin`, `portout`), class score penalized by 0.5x
- **Component vs Deployment**: If deployment features detected (`artifact`, `physical_deployment`), component score penalized by 0.6-0.75x

Penalties are multiplicative and applied after tier-weighted scoring, ensuring that strong conflicting evidence significantly reduces inappropriate classifications.

#### 6.2.6 Multi-Label Classification

The system supports **multi-label classification** through threshold-based filtering (default threshold: 0.3). After normalization, any diagram type with confidence ≥ 30% is included in the result set, allowing diagrams with hybrid characteristics to be tagged with multiple types.

Example multi-label scenario:
```
Diagram with both class structure AND object instances:
- Primary: class (0.52 confidence)
- Secondary: object (0.44 confidence)
Result: Tagged as both [class, object]
```

Multi-label rate in validation sample: 32.1% of diagrams exhibit characteristics of multiple diagram types.

#### 6.2.7 Classification Performance

Validation on 1,000-file representative sample:

| Metric | Result |
|--------|--------|
| Processing speed | ~260 files/second |
| Success rate | 100% (no crashes) |
| Average confidence | 0.73 |
| High confidence (>0.90) | ~40% of diagrams |
| Multi-label diagrams | 32.1% |

**Type Distribution (validation sample):**
- Class: 37.5%
- Use Case: 24.3%
- Sequence: 16.1%
- Component: 8.3%
- Activity: 6.4%
- Object: 3.2%
- Deployment: 2.3%
- State: 1.1%
- Timing: 0.2%
- Non-UML (Ditaa, Salt, Gantt): 0.4%
- Unclassified: 0.2%

#### 6.2.8 Design Rationale

The hierarchical approach addresses key limitations of flat scoring systems:

1. **Noise Resistance**: 100+ weak features cannot outweigh a single decisive feature (e.g., member visibility markers are nearly definitive for class diagrams)
2. **Contextual Intelligence**: Shared keywords like `interface` and `node` adapt their contribution based on surrounding features
3. **Transparent Logic**: Tier structure makes classification reasoning interpretable (Tier 1 features indicate "why" a diagram was classified)
4. **Maintainability**: New features can be easily added by assigning them to the appropriate tier with minimal impact on existing logic

The classifier achieved a **78% successful compilation rate** validation against PlantUML's official parser, with unclassified diagrams (<1%) typically being edge cases with minimal distinctive features or mixed diagram types within single files.


### 6.4 Quality Criteria

Manual validation assessed the following dimensions:
1. **Syntactic validity**: Successful PlantUML compilation (automated)
2. **Semantic coherence**: Models a plausible real-world scenario
3. **Naming quality**: Uses meaningful entity names (not generic placeholders like "Foo", "Bar")
4. **Structural completeness**: Contains sufficient elements and relationships

## 7. Metadata and Reproducibility

### 7.1 Metadata Structure

Each diagram in the final dataset is associated with comprehensive metadata:
- **Blob ID**: SHA-1 hash serving as unique identifier
- **Original file path**: Path in source repository
- **Source repository**: GitHub URL (via WoC b2P mapping)
- **Diagram type**: Automated classification result
- **Complexity metrics**: Line count, element count, relationship count

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
- Post-filtering (≥5 lines): 200,144 files
- After multi-diagram splitting: 207,161 files
- Successfully compiled: 162,257 diagrams (78% compilation success rate)
- Generated images: 163,589 PNG files

**Dataset Composition**:
- Total diagrams: 162,257
- Format: PNG images + PlantUML source code
- Metadata: JSON format with blob-level attribution

## 9. Ethical Considerations and Licensing

All source code was obtained from publicly accessible repositories indexed by the World of Code project. The dataset preserves attribution to original repositories through blob-to-project mappings, enabling proper citation and license compliance. Users of this dataset are advised to respect the licenses of source repositories when utilizing the diagrams for research or commercial purposes.

The dataset itself is released under [LICENSE TBD], with metadata clearly indicating source repository URLs for each diagram to facilitate license verification and proper attribution.

---

**Tools and Dependencies**:
- World of Code V3 (Oct 7 2023 snapshot)
- PlantUML 1.2025.9
- Python 3.8+ (libraries: python-woc, multiprocessing, base64, gzip, json, re)
- Java Runtime Environment 11+
- GNU utilities: grep, sed, sort, find, zcat

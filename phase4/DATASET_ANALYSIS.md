# Phase 4: Dataset Analysis for MDPI Data Paper

## Goal

Create a comprehensive analysis of the PlantUML-in-Wild dataset to support publication as a **Data Descriptor** in MDPI Data journal. The analysis will characterize the dataset's composition, quality, and utility for machine learning research.

**Target**: MDPI Data journal (dataset descriptor paper)
**Timeline**: 5-7 days
**Dataset Size**: 162,257 PlantUML diagrams with 163,589 generated PNG images

---
## Work Required

### 1. Dataset Characterization (Days 1-2)

**What**: Analyze ALL ~163K diagrams to extract key metrics

**Metrics to compute**:
- Diagram type (class, sequence, activity, use case, state, component, other)
- Lines of code (LOC) - non-blank, non-comment lines
- Element count (classes, participants, states, etc.)
- Relationship count (arrows, connections)

**Output**:
- `dataset_profile.csv` - one row per diagram with all metrics
- Basic statistics: min/max/median/mean/quartiles for each metric

**Implementation**:
- Single Python script analyzing all PUML files
- Keyword-based type detection (simple regex patterns)
- Count elements and relationships via pattern matching
- Processing time estimate: 1-2 hours for 163K files

---

### 2. Descriptive Statistics & Visualizations (Day 3)

**What**: Generate tables and figures for the paper

**Tables needed**:
1. **Dataset Overview** (Table 1)
   - Total diagrams, file count, size distribution
   - Compilation success rate (valid vs errors)
   - Repository count (unique sources)

2. **Diagram Type Distribution** (Table 2)
   - Count and percentage per type
   - Average LOC per type
   - Average complexity per type

3. **Complexity Breakdown** (Table 3)
   - Simple (<10 LOC): count, %
   - Medium (10-50 LOC): count, %
   - Complex (>50 LOC): count, %

**Figures needed**:
1. **Diagram type distribution** - bar chart showing % of each type
2. **LOC distribution** - histogram (log scale if needed)
3. **Complexity heatmap** - 2D grid of Type × Complexity category
4. **Example showcase** - 2×3 grid of representative diagrams (one per type)

**Tools**: Python (pandas, matplotlib, seaborn)

---

### 3. Quality Validation (Days 4-5)

**What**: Manual review of sample to validate automated analysis and assess quality

**Sample size**: 180 diagrams (30 per diagram type, stratified by complexity)

**What to check for each diagram**:
1. ✓/✗ Type classification correct?
2. ✓/✗ Models real-world scenario? (not "Car extends Banana")
3. ✓/✗ Uses meaningful names? (not just Foo/Bar/Example)
4. ✓/✗ Syntactically valid? (already known from compilation)

**Output**:
- `manual_validation.csv` with validation results
- Classification accuracy rate (%)
- Semantic quality rate (%)
- Notes on common issues found

**Purpose**: Demonstrate dataset quality and validate automated metrics

---

### 4. Dataset Documentation (Days 6-7)

**What**: Create metadata and documentation for dataset release

#### A. Metadata File (`metadata.json`)

Complete mapping of all diagrams:

```json
{
  "dataset_info": {
    "name": "PlantUML-in-Wild",
    "version": "1.0",
    "creation_date": "2025-01-XX",
    "total_diagrams": 163593,
    "valid_diagrams": 163593,
    "failed_diagrams": 44803,
    "source": "World of Code V3 (GitHub, Oct 2023)",
    "license": "CC-BY-4.0"
  },
  "diagrams": [
    {
      "id": "7f77342aff0de635f7912f75e156bf5c0c5dd8fa",
      "puml_file": "puml/7f77342aff0de635f7912f75e156bf5c0c5dd8fa.puml",
      "image_file": "images/7f77342aff0de635f7912f75e156bf5c0c5dd8fa.png",
      "diagram_type": "sequence",
      "loc": 23,
      "elements": 5,
      "relationships": 12,
      "blob_hash": "7f77342aff0de635f7912f75e156bf5c0c5dd8fa"
    }
  ]
}
```

#### B. Dataset README (`README.md`)

User-friendly documentation covering:
- What the dataset contains
- How it was collected (brief methodology)
- File structure and formats
- How to use the data
- License and citation info
- Statistics summary

#### C. Paper Sections Draft

Prepare text and figures for:
- **Data Description section**: composition, structure, formats
- **Methods section**: collection, validation, quality control
- **Usage Notes section**: how to access and use the data

---

## Implementation Plan

### Day 1: Setup & Full Dataset Analysis
- [ ] Set up analysis environment (pandas, matplotlib, seaborn, Pillow)
- [ ] Write script to analyze all PUML files in phase3/
- [ ] Extract metrics: type, LOC, elements, relationships
- [ ] Generate `dataset_profile.csv`
- [ ] Compute basic statistics

### Day 2: Statistics Processing
- [ ] Calculate distribution statistics
- [ ] Identify representative examples for each type
- [ ] Cross-reference with image files (check file matching)
- [ ] Generate summary statistics tables

### Day 3: Visualization
- [ ] Create Figure 1: Type distribution bar chart
- [ ] Create Figure 2: LOC histogram
- [ ] Create Figure 3: Complexity heatmap
- [ ] Create Figure 4: Example diagram showcase
- [ ] Export high-quality images for paper

### Day 4: Manual Validation Setup
- [ ] Stratified random sample selection (180 diagrams)
- [ ] Export sample with images for review
- [ ] Create validation spreadsheet template

### Day 5: Manual Validation Execution
- [ ] Review 180 diagrams manually
- [ ] Record validation results
- [ ] Compute accuracy and quality metrics
- [ ] Document common issues/patterns

### Day 6: Dataset Documentation
- [ ] Generate complete metadata.json (all diagrams)
- [ ] Write dataset README.md
- [ ] Organize final dataset structure
- [ ] Create example usage notebook (optional)

### Day 7: Paper Preparation
- [ ] Draft Data Description section with stats/figures
- [ ] Draft Methods section validation methodology
- [ ] Prepare supplementary materials list
- [ ] Review and finalize all outputs

---

## Expected Deliverables

### For Paper Submission:
1. **3 Tables** (dataset overview, type distribution, complexity breakdown)
2. **4 Figures** (type chart, LOC histogram, heatmap, examples)
3. **Statistics** (all descriptive stats computed)
4. **Validation results** (classification accuracy, quality assessment)
5. **Draft text** for Data Description and Methods sections

### For Dataset Release:
1. **metadata.json** - complete dataset metadata
2. **README.md** - dataset documentation
3. **Analysis scripts** - reproducible Python code
4. **Manual validation data** - validation sample and results

### File Structure:
```
phase4/
├── DATASET_ANALYSIS.md (this file)
├── ANALYSIS_PLAN.md (detailed research plan - for reference)
├── scripts/
│   ├── analyze_dataset.py (main analysis script)
│   ├── generate_visualizations.py
│   └── create_metadata.py
├── outputs/
│   ├── dataset_profile.csv (all diagrams with metrics)
│   ├── summary_statistics.json
│   ├── manual_validation.csv
│   └── metadata.json
├── figures/
│   ├── fig1_type_distribution.png
│   ├── fig2_loc_histogram.png
│   ├── fig3_complexity_heatmap.png
│   └── fig4_examples.png
└── tables/
    ├── table1_overview.csv
    ├── table2_types.csv
    └── table3_complexity.csv
```

## Success Criteria

✅ Complete characterization of all 163K diagrams
✅ High-quality figures ready for paper
✅ Manual validation demonstrates dataset quality (>85% semantic quality target)
✅ Complete metadata enables dataset reuse
✅ Reproducible analysis scripts provided
✅ Paper sections drafted with findings

This focused approach balances thoroughness with efficiency, meeting MDPI Data requirements while avoiding overengineering.

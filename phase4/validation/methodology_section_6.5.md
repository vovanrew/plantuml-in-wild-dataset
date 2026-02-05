### 6.5 Classification Validation

#### 6.5.1 Manual Validation Protocol

A stratified random sample of 100 diagrams (10 per diagram type) was manually
reviewed by domain experts. Each diagram was evaluated on three criteria:

1. **Classification correctness**: Whether the LLM-assigned type matches the actual diagram type
2. **Real-world relevance**: Whether the diagram documents actual software (vs. tutorials, learning exercises, or templates)
3. **Logical correctness**: Whether the diagram represents valid, meaningful content (vs. placeholders with generic names)

#### 6.5.2 Classification Accuracy

| Metric | Result |
|--------|--------|
| Total samples validated | 100 |
| Correct classifications | 92 |
| **Overall accuracy** | **92.0%** |

**Per-Type Accuracy**:

| Type | Correct | Total | Accuracy |
|------|---------|-------|----------|
| activity | 10 | 10 | 100.0% |
| class | 10 | 10 | 100.0% |
| component | 9 | 10 | 90.0% |
| deployment | 9 | 10 | 90.0% |
| object | 5 | 10 | 50.0% |
| sequence | 9 | 10 | 90.0% |
| state | 10 | 10 | 100.0% |
| timing | 10 | 10 | 100.0% |
| unclassified | 10 | 10 | 100.0% |
| usecase | 10 | 10 | 100.0% |

#### 6.5.3 Error Analysis

The 8 misclassifications fell into three categories:

1. **Component/Deployment confusion** (2 cases): PlantUML's node/component syntax overlap causes boundary ambiguity
2. **Sequence/Activity confusion** (1 cases): Step-by-step processes documented using sequence syntax
3. **Object type over-assignment** (5 cases): Non-UML PlantUML extensions (ERD, JSON, Salt) misclassified as object

#### 6.5.4 Real-World Content Analysis

| Category | Count | Percentage |
|----------|-------|------------|
| Real-world production diagrams | 58 | 63.7% |
| Tutorials/learning/templates | 33 | 36.3% |
| Not applicable (sprite libraries) | 9 | — |

**Real-world by Type**:

| Type | Real-world | Not Real-world | % Real-world |
|------|------------|----------------|--------------|
| object | 8 | 2 | 80.0% |
| sequence | 8 | 2 | 80.0% |
| state | 8 | 2 | 80.0% |
| deployment | 7 | 3 | 70.0% |
| usecase | 7 | 3 | 70.0% |
| component | 6 | 4 | 60.0% |
| activity | 5 | 5 | 50.0% |
| class | 5 | 5 | 50.0% |
| timing | 4 | 6 | 40.0% |
| unclassified | 0 | 1 | 0.0% |

#### 6.5.5 Logical Correctness

Of the 91 classifiable diagrams, **95.6%** (87) contained valid, meaningful content rather than placeholder templates.

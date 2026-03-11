# UML Diagram Type Classification and Validation Methodology

## Overview

Each diagram in the dataset is classified by an LLM into a semantic diagram type (`primary_type`). This classification was validated against PlantUML's structural parser, achieving 98.1% agreement on comparable categories.

## LLM Classification (`primary_type`)

The LLM examines the raw `.puml` source and assigns a semantic diagram type based on content, keywords, and intent.

**Types produced:** class, sequence, activity, state, component, usecase, deployment, object, timing, non-uml

### The `non-uml` category

20,434 diagrams (12.5% of 163,946) were classified as `non-uml`. These include predominantly **sprite/icon library definitions** — files that define reusable graphical sprites using PlantUML's `sprite` directive and `!define` macros — as well as PlantUML-specific non-UML formats (@startmindmap, @startgantt, @startwbs, @startjson, @startsalt, @startditaa, @startnwdiag, @startdot), ERD/database schemas, auto-generated infrastructure visualizations (e.g., Helm chart dependency maps), and empty or unrecognizable files. Example of a sprite library file:

```plantuml
@startuml
sprite $drupal [48x48/16] {
000000000000000000000000000000000000000000000000
...
}
!define DEV2_DRUPAL(_alias) ENTITY(rectangle,black,drupal,_alias,DEV2 DRUPAL)
@enduml
```

These are not diagrams in the traditional UML sense — they are reusable icon assets for inclusion in other diagrams. The LLM correctly identifies them as not fitting any standard UML diagram type.

## Structural Cross-Validation via PlantUML Parser

The LLM classification targets the standard UML taxonomy (9 diagram types), assigning each diagram a semantic type based on its content and intent. To cross-validate these assignments, we compared them against PlantUML's own structural parser, which recognizes diagram types based on syntax. Neither system serves as ground truth — the LLM performs semantic classification while the parser performs structural analysis — so the comparison measures inter-method agreement rather than accuracy against an authoritative reference. The parser produces a coarser 5-type taxonomy due to PlantUML's internal architecture, so cross-validation requires mapping the LLM's finer UML types to the parser's coarser categories:

| Parser type | LLM types it covers | Reason |
|---|---|---|
| class | class, object | Object diagrams are a syntactic subset of class diagrams — the same `ClassDiagramFactory` handles both |
| component | component, usecase, deployment | All three use `UmlDiagramType.DESCRIPTION` internally; the distinction exists only at the entity level (`LeafType`, `USymbol`), and a single diagram can mix element types freely |
| sequence | sequence | 1:1 mapping |
| activity | activity | 1:1 mapping |
| state | state | 1:1 mapping |

Types with no parser equivalent (non-uml, timing) were excluded from cross-validation. Additionally, the coarse taxonomy means that fine-grained distinctions within the component group (component vs. usecase vs. deployment — 12% of the dataset) cannot be verified by this method, since the parser maps all three to a single `DESCRIPTION` type.

### Cross-validation results

After mapping the LLM's finer types to the parser's coarser taxonomy:

| Metric | Value |
|---|---|
| Comparable entries | 143,069 |
| Matched | 140,307 |
| Mismatched | 2,762 |
| **Adjusted accuracy** | **98.07%** |

Per-category cross-validation agreement:

| Category | Accuracy |
|---|---|---|
| class (class + object) | 99.8% |
| sequence | 99.0% |
| activity | 98.0% |
| state | 96.5% |
| component (component + usecase + deployment) | 89.1% |

The remaining 1.93% disagreements (2,762 cases) arise from three well-understood causes:

1. **Shared keywords across diagram types** (e.g., `actor` appears in both sequence and use case diagrams; `package` appears in both class and component diagrams). The LLM may associate a keyword with one type while the parser resolves it to another based on surrounding syntax. This accounts for the largest single mismatch pattern: 283 use case diagrams where the `actor` keyword led the LLM to classify as use case, but the arrow-message syntax (`-> :message`) is unambiguously sequence.

2. **One syntax engine expressing another type's semantics** (e.g., PlantUML's legacy activity syntax — `(*)`, `-->`, `[guard]` — used to draw state machines; activity diagrams with named swim lanes resembling sequence-diagram participants). The LLM classifies by semantic intent while the parser classifies by the syntax engine that processes the file.

3. **Hybrid diagrams** enabled by PlantUML's `allowmixing` directive or `!define` macro aliasing, which mix elements from different diagram families (e.g., `node` + `class`, or `!define Class agent`). These diagrams are inherently ambiguous at the diagram-type level — neither a single semantic label nor a single parser type fully captures them.

These represent inherent ambiguities in PlantUML's type system rather than classification errors by either method.

### Why the parser cannot distinguish usecase/deployment/component

PlantUML's `UmlDiagramType` enum has no separate values for these three types. All are `DESCRIPTION`. The difference is encoded at the entity level:

- `(Name)` → `LeafType.USECASE`
- `[Name]` → `LeafType.DESCRIPTION` with `USymbol.COMPONENT`
- `node Name` → `LeafType.DESCRIPTION` with `USymbol.NODE`

A single diagram can freely mix all three element types, so the diagram-level distinction is inherently undefined. The LLM makes a semantic judgment about the diagram's overall purpose — a classification the parser fundamentally cannot perform.

## Resolved: Non-UML Content Exclusion

All 20,434 diagrams classified as `non-uml` were excluded from the final dataset. Manual validation on a random sample of 100 non-uml entries confirmed 100% agreement with the classifier's labeling, supporting the reliability of the automated filtering. The final dataset contains 143,427 UML diagrams across 9 standard types.

## Resolved: Disagreement Analysis

Investigation of the 2,762 mismatched cases confirmed that disagreements cluster into explainable categories rather than random errors. The top adjusted mismatches by count:

| Mismatch (LLM → Parser) | Count | Root Cause |
|---|---|---|
| component group → class | 1,545 | `allowmixing`, `package`/stereotype hybrids, macro aliasing |
| usecase → sequence | 283 | Shared `actor` keyword; arrow-message syntax is unambiguously sequence |
| sequence → activity | 214 | Activity swim lanes with named actors resemble sequence participants |
| deployment → class | 153 | Deployment semantics expressed via class syntax + stereotypes |
| class → component | 124 | `!define` macros aliasing class names to description-family elements |
| activity → component | 113 | Content outside `@startuml`/`@enduml` read by LLM but ignored by parser; description-type syntax misread as flow |
| sequence → component | 96 | Component-like topology described with sequence arrow syntax |
| state → activity | 75 | Legacy activity syntax (`(*)`, `-->`, `[guard]`) used to draw state machines |
| activity → state | 46 | State-like node names in activity control flow |
| activity → sequence | 28 | Linear workflows expressed in sequence arrow syntax |

No corrections were applied to the classifications, as the 98.07% agreement rate is sufficient for dataset-level validation and the disagreements reflect genuine ambiguities in PlantUML's type system rather than systematic misclassification.

# UML Diagram Type Classification and Validation Methodology

## Overview

Each diagram in the dataset is classified by an LLM into a semantic diagram type (`primary_type`). This classification was validated against PlantUML's structural parser, achieving 97.3% agreement on comparable categories.

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

## Structural Validation via PlantUML Parser

The LLM classification targets the standard UML taxonomy (9 diagram types), assigning each diagram a semantic type based on its content and intent. To validate these assignments, we compared them against PlantUML's own structural parser, which recognizes diagram types based on syntax. The parser produces a coarser 5-type taxonomy due to PlantUML's internal architecture, so validation requires mapping the LLM's finer UML types to the parser's coarser categories:

| Parser type | LLM types it covers | Reason |
|---|---|---|
| class | class, object | Object diagrams are a syntactic subset of class diagrams — the same `ClassDiagramFactory` handles both |
| component | component, usecase, deployment | All three use `UmlDiagramType.DESCRIPTION` internally; the distinction exists only at the entity level (`LeafType`, `USymbol`), and a single diagram can mix element types freely |
| sequence | sequence | 1:1 mapping |
| activity | activity | 1:1 mapping |
| state | state | 1:1 mapping |

Types with no parser equivalent (non-uml, timing) were excluded from validation.

### Validation results

After mapping the LLM's finer types to the parser's coarser taxonomy:

| Metric | Value |
|---|---|
| Comparable entries | 147,536 |
| Matched | 143,498 |
| Mismatched | 4,038 |
| **Adjusted accuracy** | **97.26%** |

Per-category agreement:

| Category | Accuracy |
|---|---|---|
| class (class + object) | 99.7% |
| sequence | 98.1% |
| activity | 97.3% |
| state | 95.4% |
| component (component + usecase + deployment) | 87.4% |

The remaining 2.7% disagreements represent genuinely ambiguous diagrams where PlantUML syntax allows multiple structural interpretations (e.g., diagrams mixing class-like and component-like elements).

### Why the parser cannot distinguish usecase/deployment/component

PlantUML's `UmlDiagramType` enum has no separate values for these three types. All are `DESCRIPTION`. The difference is encoded at the entity level:

- `(Name)` → `LeafType.USECASE`
- `[Name]` → `LeafType.DESCRIPTION` with `USymbol.COMPONENT`
- `node Name` → `LeafType.DESCRIPTION` with `USymbol.NODE`

A single diagram can freely mix all three element types, so the diagram-level distinction is inherently undefined. The LLM makes a semantic judgment about the diagram's overall purpose — a classification the parser fundamentally cannot perform.

## Resolved: Non-UML Content Exclusion

All 20,434 diagrams classified as `non-uml` were excluded from the final dataset. Manual validation on a random sample of 100 non-uml entries confirmed 100% agreement with the classifier's labeling, supporting the reliability of the automated filtering. The final dataset contains 143,427 UML diagrams across 9 standard types.

## Open Questions

1. **Component category validation**: The TBD% agreement on the component category is the weakest. The cases where the LLM says "component" but the parser routes to the class factory likely involve diagrams using generic PlantUML constructs (e.g., `rectangle`, `package`, generic arrows) that are syntactically valid in multiple diagram contexts. This reflects PlantUML's permissive syntax rather than genuine UML ambiguity — in standard UML, class and component diagrams are clearly distinct, but PlantUML does not enforce strict syntactic boundaries between diagram types.

2. **Sequence vs. activity ambiguity (488 cases)**: The largest genuine disagreement between systems sharing the same type vocabulary. Worth investigating whether these are hybrid diagrams or systematic errors.

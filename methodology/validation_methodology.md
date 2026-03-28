# Validation Methodology

## 1. Overview

This document describes the manual validation procedure for the UML-in-the-Wild dataset. The validation targets three aspects of each diagram: (1) the LLM-assigned diagram type classification, (2) the parser-extracted element counts, and (3) the parser-extracted connection counts.

A single domain expert (the first author) performed all validation. The validation uses a two-layered approach: the reviewer first independently counts total elements and connections from the PlantUML source (Layer 1), then verifies the tool's per-type breakdown against a reference table of type key mappings (Layer 2). This design eliminates confirmation bias on totals while remaining feasible for the 57 element type keys and 28 connection type keys, many of which are PlantUML-internal names not deducible from syntax alone. The rationale for source-based validation over visual validation is discussed in §2.

## 2. Validation Approach: Source-Based Structural Counting

Two approaches were considered for validating element and connection counts:

**Source-based (chosen):** The reviewer reads the `.puml` source file and counts elements and connections by identifying PlantUML constructs that correspond to the extraction tool's documented semantics.

**Visual (rejected):** The reviewer counts elements and connections by inspecting the rendered PNG image.

Source-based validation was chosen for the following reasons:

1. **The extraction tool operates on source, not images.** The DiagramStatsExtractor reads PlantUML's parsed intermediate representation, which is derived from source code. Validating against source directly tests the claim being made.

2. **Activity diagram connections have no visual counterpart.** The tool counts implicit control flow edges (`sequential`, `branch`, `merge`, `loop_entry`, `loop_back`, `loop_exit`, `fork_split`, `fork_join`) derived from the instruction tree. These are graph edges in the control flow model, not visible arrows in the rendered diagram. A `while` loop contributes 3 connections (entry, back, exit), but the rendered image may show a different number of arrows. Visual counting would compare against a different quantity than what the tool measures.

3. **Groups are counted as elements but are not visually salient.** A class diagram with 5 classes inside 2 packages reports `elements_total = 7`. A visual reviewer would likely count 5 boxes. The discrepancy is correct behavior, not an error.

4. **The rendered image is generated from the same parsed representation.** If PlantUML's parser misinterprets a construct, both the image and the extraction tool will reflect the same misinterpretation. Visual validation cannot detect parser-level errors.

The rendered PNG images are available alongside the source files and may be consulted as a secondary reference to aid comprehension, but the source file is the authoritative basis for all counts.

### 2.1 Visual vs Structural Connection Counts in Activity Diagrams

The divergence between visual arrows and structural connection counts deserves specific illustration, as it is the most counterintuitive aspect of the counting methodology.

Consider a deduplication flow with a nested `if/else` (`74168e443c06eb2e1ee3764636da51722d64ed15.puml`, sample_id 5):

```
start
:Start Transaction;
:Add MessageID to Store;
if (MessageID added?) then (yes)
  :Process Message;
  if (Success?) then (yes)
    :Commit;
  else (no)
    :Rollback;
  endif
else (no)
endif
stop
```

The tool reports 11 connections: `{"sequential": 5, "branch": 4, "merge": 2}`. The rendered diagram shows 12 visual arrows. The mapping between visual arrows and structural connections is not one-to-one:

| # | Visual arrow | Structural connection |
|---|---|---|
| 1 | start → Start Transaction | `sequential` |
| 2 | Start Transaction → Add MessageID to Store | `sequential` |
| 3 | Add MessageID to Store → outer if diamond | `sequential` |
| 4 | outer if → Process Message ("success") | `branch` |
| 5 | outer if → outer merge diamond ("conflict") | `branch` |
| 6 | Process Message → inner if diamond | `sequential` |
| 7 | inner if → Commit ("yes") | `branch` |
| 8 | inner if → Rollback ("no") | `branch` |
| 9 | Commit → inner merge diamond | (part of inner `merge`) |
| 10 | Rollback → inner merge diamond | (part of inner `merge`) |
| 11 | inner merge diamond → outer merge diamond | (part of outer `merge`) |
| 12 | outer merge diamond → stop | `sequential` |

The discrepancy (12 visual vs 11 structural) arises because merge edges do not map one-to-one to visual arrows. A structural `merge` represents a single convergence point ("branches rejoin here"), counted as 1 edge per `if` or `switch` block. Visually, this convergence requires one incoming arrow per branch — so the inner merge diamond receives 2 visual arrows (from Commit and Rollback) but corresponds to 1 structural `merge` edge.

This overlap is a general property of the counting model, not specific to this example. It occurs in any activity diagram where a compound instruction (`if`, `while`, `repeat`, `fork`, `switch`) is followed by another instruction: the compound instruction's exit edge (merge, loop_exit, or fork_join) and the sequential edge to the next instruction share a single visual arrow. Conversely, merge points with multiple incoming branches render as multiple visual arrows but count as a single structural edge. As a result, the visual arrow count and the structural connection count will generally differ for any activity diagram that contains compound instructions.

This non-trivial mapping between logical edges and visual arrows is why source-based structural counting is used rather than visual arrow counting. The structural count is well-defined and deterministic; the visual arrow count depends on rendering layout and does not correspond one-to-one to the control flow graph edges that the extraction tool measures.

## 3. Sampling Design

### 3.1 Sample Size and Stratification

The validation sample consists of **270 diagrams**: 30 per diagram type across all 9 types (activity, class, component, deployment, object, sequence, state, timing, usecase). Diagrams were selected by stratified random sampling from the final dataset of 143,427 diagrams using a fixed random seed (42) for reproducibility.

### 3.2 Sampling Script

The sampling was performed by `phase3/manual_validation/sample_for_validation.py`, which:
- Loads the dataset metadata JSON
- Groups diagrams by `primary_type`
- Randomly samples 30 diagrams per type (seed = 42)
- Exports selected diagrams with their tool-reported counts and empty fields for manual review
- Copies corresponding `.puml` source files and `.png` images into a self-contained validation directory

## 4. Validation Procedure

For each of the 270 sampled diagrams, the reviewer performs the following steps:

### 4.1 Diagram Type Validation

1. Read the PlantUML source file
2. Optionally inspect the rendered PNG for additional context
3. Determine the actual UML diagram type based on the structural constructs present
4. Record the actual type in `actual_type`
5. If the actual type differs from `classified_type`, note the reason in `notes`

### 4.2 Element and Connection Count Validation — Two-Layered Approach

The extraction tool produces 57 distinct element type keys and 28 connection type keys, many of which are PlantUML-internal names (e.g., `circle_start` for `[*]`, `description` for component/deployment/usecase entities, `synchro_bar` for legacy activity sync bars). Expecting a reviewer to independently assign these keys from scratch is not feasible. Instead, validation proceeds in two layers:

#### Layer 1: Independent Total Count

The reviewer reads the PlantUML source file **without consulting the tool's per-type breakdown** and independently counts:

- **Total elements**: how many structural entities (classes, participants, states, action nodes, etc.) are declared in the diagram
- **Total connections**: how many relationships (arrows, messages, control flow edges) exist

What counts as an element or connection depends on the diagram family:

**Entity-link diagrams (class, object, component, deployment, usecase, state):**
- Elements: each declared entity (class, interface, component, state, actor, etc.) + each group container (package, namespace) — excluding the implicit root group. Notes and floating annotations also count.
- Connections: each arrow or line between entities.

**Sequence diagrams:**
- Elements: each participant (explicit declarations + implicit first-use participants).
- Connections: each message arrow. Combined fragments (`alt`, `opt`, `loop`, etc.), notes, dividers, and delays are NOT counted.

**Activity diagrams:**
- Elements: each action statement (`:text;`), `start`, `stop`, `end`, plus each control flow construct (`if`, `while`, `repeat`, `fork`, `switch`) as one element each. Note: an `if` with multiple `elseif` clauses is one element.
- Connections: derive from control flow structure — N−1 sequential edges for N consecutive instructions, branch/merge edges for conditionals, 3 edges per loop (entry, back, exit), 2×N edges per fork with N branches.

**Timing diagrams:** Skipped (see §4.4).

The reviewer records the independent total in `actual_elements_count` and `actual_connections_count`. If the total disagrees with the tool's reported `total_elements` or `total_connections`, the reviewer proceeds to Layer 2 to locate the discrepancy. If totals agree, the reviewer still proceeds to Layer 2 but with higher confidence.

#### Layer 2: Guided Per-Type Verification

The reviewer now examines the tool's reported per-type breakdown (e.g., `{"class": 5, "interface": 2, "package": 1}`) and verifies each claimed count against the source. The reviewer uses the reference tables in `element_type_keys.md` and `connection_type_keys.md` to understand unfamiliar keys.

For each key in the tool's reported breakdown:

1. **Identify** what PlantUML construct the key corresponds to (consult reference table if needed)
2. **Count** how many instances of that construct appear in the source
3. **Confirm or correct** the tool's claimed count

The reviewer also checks for elements or connections present in the source but **missing** from the tool's breakdown — cases where the tool may have failed to count a construct entirely.

#### Nature of corrections

Because the extraction tool reads type keys directly from PlantUML's internal enums (`LeafType`, `GroupType`, `ParticipantType`, `LinkDecor`), per-type key misclassification is not expected — the tool cannot assign a wrong key name because it reads the enum value, not the syntax. Realistic corrections are:

- **Count adjustment**: a key's count is wrong (e.g., `"class": 5` should be `"class": 6` because the reviewer found one more class declaration)
- **Missing key**: a construct was not counted at all (e.g., the tool omitted a `note`, so the reviewer adds `"note": 1` to the breakdown)
- **Extra key**: a construct was counted that should not have been (e.g., a styling directive was misinterpreted as an entity)

When totals agree in Layer 1 and per-type counts look plausible in Layer 2, the reviewer copies the tool's breakdown as-is into `actual_elements`/`actual_connections`. Corrections only apply when a discrepancy is found.

After Layer 2, the reviewer records:
- `actual_elements`: the tool's per-type breakdown (copied if correct) or the reviewer's corrected breakdown (with counts adjusted, keys added, or keys removed)
- `actual_connections`: same as above for connections
- `elements_correct`: `true` if both per-type breakdown AND total match exactly
- `connections_correct`: `true` if both per-type breakdown AND total match exactly

#### Reference Tables

The following reference documents map all observed type keys to their PlantUML syntax triggers:

- `element_type_keys.md` — 57 element type keys organized by diagram family
- `connection_type_keys.md` — 28 connection type keys organized by diagram family

### 4.3 Timing Diagrams — Classification Only

Of the 189 timing diagrams in the dataset, 178 (94.2%) have empty element and connection fields due to the `unsupported_type:TimingDiagram` extraction error. For the 30 sampled timing diagrams, only diagram type classification is validated. Element and connection fields are marked as not applicable.

## 5. Recording Format

Each validated diagram is recorded as a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `sample_id` | int | Sequential identifier (1–270) |
| `filename` | string | PlantUML source filename |
| `classified_type` | string | Tool-assigned diagram type |
| `content_lines` | int | Non-blank, non-comment line count |
| `elements` | object | Tool-reported element counts by type |
| `total_elements` | int | Tool-reported total element count |
| `connections` | object | Tool-reported connection counts by type |
| `total_connections` | int | Tool-reported total connection count |
| `actual_type` | string | Reviewer-determined diagram type |
| `elements_correct` | bool | Whether tool element counts match reviewer counts |
| `actual_elements` | object | Reviewer-determined element counts by type |
| `actual_elements_count` | int | Reviewer-determined total element count |
| `connections_correct` | bool | Whether tool connection counts match reviewer counts |
| `actual_connections` | object | Reviewer-determined connection counts by type |
| `actual_connections_count` | int | Reviewer-determined total connection count |
| `notes` | string | Free-text observations, disagreement explanations, edge cases |

### 5.1 Recording Conventions

- `actual_elements_count` and `actual_connections_count` are always filled from the Layer 1 independent count, regardless of agreement
- `actual_elements` and `actual_connections` are filled from Layer 2 verification — either a copy of the tool's breakdown (if correct) or the reviewer's corrected breakdown
- `elements_correct` and `connections_correct` are set to `true` only if both the per-type breakdown AND the total match exactly
- When counts disagree, the reviewer explains the discrepancy in `notes` (which key was wrong, what construct was missed or miscounted, and why)
- For timing diagrams, `elements_correct`, `actual_elements`, `actual_elements_count`, `connections_correct`, `actual_connections`, and `actual_connections_count` are left as `null` (not applicable)

## 6. Metrics

The following metrics will be computed from the completed validation:

### 6.1 Classification Accuracy

- **Overall accuracy**: proportion of diagrams where `classified_type == actual_type`
- **Per-type accuracy**: accuracy broken down by diagram type (30 samples each)
- **Confusion patterns**: any systematic misclassifications (e.g., component vs deployment)

### 6.2 Element Count Accuracy

- **Exact match rate**: proportion where `elements_correct == true` (excluding timing diagrams)
- **Per-type match rate**: broken down by diagram family
- **Total count agreement**: for disagreements, magnitude and direction of error (over/under-count)

### 6.3 Connection Count Accuracy

- **Exact match rate**: proportion where `connections_correct == true` (excluding timing diagrams)
- **Per-type match rate**: broken down by diagram family
- **Error analysis**: categorization of disagreement causes from `notes` field

## 7. Validation Followups

During validation, the reviewer may encounter edge cases or systematic patterns not anticipated by this methodology. The `notes` field captures these observations. After validation is complete, notes will be reviewed for:

- **Systematic extraction errors**: patterns where the tool consistently miscounts (e.g., a specific PlantUML construct that is missed or double-counted)
- **Ambiguous constructs**: cases where the "correct" count is debatable, requiring a documented interpretation decision
- **Methodology refinements**: any counting rules that needed clarification or amendment during the review process
- **Legacy syntax encounters**: activity diagrams using legacy syntax that are handled by the entity-link strategy instead of the activity tree traversal, resulting in different element labels

Any methodology refinements made during validation will be recorded as amendments to this document with the affected sample IDs noted.

### 7.1 Findings: Systematic `none` Connection Overcounting

The dominant source of connection count disagreement is the extraction tool reporting spurious `none`-type connections that have no corresponding relationship in the PlantUML source. Of the 28 connection disagreements across 240 validated diagrams (excluding timing), 25 are caused exclusively by `none` overcounting — no other connection type key differs in these cases.

**Affected diagram types** (none-only errors / total errors):

| Type | None-only | Total errors | Excess `none` |
|------|-----------|--------------|---------------|
| class | 8/8 | 8 | +42 |
| usecase | 6/7 | 7 | +23 |
| deployment | 5/5 | 5 | +7 |
| state | 3/3 | 3 | +7 |
| component | 2/2 | 2 | +3 |
| activity | 1/3 | 3 | +6 |

**Root causes identified from notes:**

1. **Note-attachment links** (samples #35, #40, #44, #70, #100, #112, #115, #117, #194, #198, #203, #249, #252, #257, #263): When a diagram contains `note left of X`, `note on link`, or similar note constructs, PlantUML internally creates a `Link` object to attach the note to its target entity. The extraction tool reads these internal links and counts them as `none` connections. These are rendering instructions, not user-declared UML relationships.

2. **Phantom links with no identifiable source** (samples #33, #39, #43, #50, #57, #259, #261): The tool reports `none` connections in diagrams where no undirected relationship syntax (`--`, `..`, or similar) appears in the source. These may originate from class member separators, namespace boundary links, or other PlantUML-internal constructs that create `Link` objects during parsing.

**Non-`none` errors** (3 cases):
- **Activity unreachable merge/join** (#22, #24): The tool counts `merge` or `fork_join` edges for control flow constructs whose branches terminate with `end`/`stop`, making the merge/join point unreachable. The structural edges exist in the model but do not correspond to actual control flow paths.
- **Complete extraction failure** (#254): The tool returned zero elements and zero connections for a valid usecase diagram, likely due to an unhandled parsing edge case.

### 7.2 Impact Assessment

If the 25 none-only errors were excluded (treating note-attachment and phantom links as a known tool limitation rather than extraction errors), the connection exact-match rate would rise from 212/240 (88.3%) to 237/240 (98.8%). This suggests that the extraction tool is highly accurate for user-declared UML relationships, but its scope includes PlantUML-internal link objects that do not correspond to diagram-level connections. Users of the dataset's connection counts should be aware that `none`-type connections may include note-attachment links and other rendering artifacts.

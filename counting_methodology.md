# Parser-Based Element and Connection Extraction Methodology

## 1. Motivation

We developed an extraction tool that reuses the PlantUML compiler's own internal parser and data model. Rather than attempting to replicate PlantUML's parsing logic through pattern matching, we invoke the same code path that PlantUML uses to compile diagrams for rendering, then inspect the resulting intermediate representation to extract element and connection counts.

## 2. Approach Overview

The extraction tool operates as a Java program embedded within the PlantUML source tree (version 1.2025.9). It reuses PlantUML's parsing pipeline — including preprocessing (macro expansion, file inclusion, conditional compilation), lexical analysis, and diagram-type-specific command interpretation — to produce fully resolved diagram objects. The tool then inspects these objects to enumerate structural elements and connections, outputting per-diagram statistics in JSON Lines (JSONL) format.

This approach ensures that element and connection counts reflect the same interpretation of PlantUML syntax that the compiler itself applies when generating visual output. Any valid PlantUML construct — including aliases, stereotypes, shorthand notations, qualified names, and implicit flows — is handled by the compiler's existing logic rather than by independent reimplementation.

## 3. Parsing Pipeline

The extraction tool invokes the following PlantUML internal pipeline for each input file:

### 3.1 Preprocessing

The source file is read and processed by `BlockUmlBuilder`, which applies PlantUML's Tim preprocessor. This stage handles `!include` directives, `!define` macros, `!procedure` and `!function` blocks, conditional compilation (`!ifdef`, `!ifndef`), and variable substitution. The preprocessor also identifies individual diagram blocks delimited by `@startuml`/`@enduml` markers, producing one `BlockUml` object per block.

### 3.2 Diagram Type Detection and Factory Selection

When `BlockUml.getDiagram()` is invoked, `PSystemBuilder` examines the `@startuml` directive to determine the diagram type (via `DiagramType.getTypeFromArobaseStart()`). It then iterates through registered `PSystemFactory` implementations — each corresponding to a specific diagram type — until one successfully parses the input. This factory selection mechanism supports over 30 diagram types, including class, sequence, activity, state, component, use case, deployment, object, timing, and others.

### 3.3 Command-Based Parsing

For structural UML diagrams, parsing is performed by `PSystemCommandFactory`, which implements a command pattern. Each diagram type registers a set of `Command` implementations, each responsible for recognizing and interpreting a specific syntactic construct (e.g., class declarations, arrow definitions, note attachments). The factory iterates through the preprocessed source lines, matching each line against the registered commands and executing the first match to update the diagram's internal state. This produces a fully populated diagram object containing all declared entities, their attributes, and all connections between them.

## 4. Extraction Strategies

PlantUML employs different internal representations for different diagram families. The extraction tool implements three strategies, dispatched based on the runtime type of the parsed diagram object. All three strategies extract two disjoint metrics: **elements** (the nodes of the diagram's underlying graph — e.g., classes, participants, activity actions) and **connections** (the edges between those nodes — e.g., inheritance links, messages, control flow arrows). A given diagram construct is counted as either an element or a connection, never both.

### 4.1 Strategy 1: Entity-Link Diagrams (CucaDiagram)

**Applicable diagram types**: class, object, component, deployment, use case, state

These diagram types inherit from the `CucaDiagram` base class, which maintains two primary collections:

- **Entities**: stored in a hierarchical namespace (`Plasma<Entity>`) and accessible via `leafs()` (terminal entities) and `groups()` (container entities such as packages and namespaces). Each entity carries a `LeafType` enum value assigned during parsing that identifies its UML type (e.g., `CLASS`, `INTERFACE`, `ABSTRACT_CLASS`, `ENUM`, `ANNOTATION`, `COMPONENT`, `STATE`, `USECASE`). The `LeafType` enumeration defines 51 distinct entity types. Container entities carry a `GroupType` enum value (e.g., `PACKAGE`, `STATE`, `CONCURRENT_STATE`).

- **Links**: stored as a flat list accessible via `getLinks()`. Each `Link` object references its two endpoint entities and carries a `LinkType` that encodes the visual representation of the relationship. `LinkType` consists of two `LinkDecor` enum values (one per endpoint) and a `LinkStyle`. The `LinkDecor` enumeration distinguishes inheritance (`EXTENDS`), composition (`COMPOSITION`), aggregation (`AGREGATION`), dependency arrows (`ARROW`), and other UML relationship types.

**Element extraction**: The tool iterates over `leafs()` and `groups()`, reads each entity's `LeafType` or `GroupType`, and accumulates counts per type. The implicit root group is excluded. Element type names are derived directly from the enum constant names (e.g., `LeafType.INTERFACE` produces the key `"interface"`).

**Connection extraction**: The tool iterates over `getLinks()`, reads each link's `LinkDecor` values at both endpoints, and classifies the connection into a semantic category (e.g., `"extends"`, `"composition"`, `"aggregation"`, `"arrow"`, `"none"`). The classification prioritizes the semantically stronger decoration when both endpoints carry non-trivial decorations.

### 4.2 Strategy 2: Sequence Diagrams (SequenceDiagram)

**Applicable diagram types**: sequence

Sequence diagrams use a fundamentally different internal representation based on participants and events rather than entities and links.

- **Participants**: accessible via `participants()`, returning an ordered collection. Each `Participant` carries a `ParticipantType` enum value distinguishing `PARTICIPANT`, `ACTOR`, `BOUNDARY`, `CONTROL`, `ENTITY`, `DATABASE`, `COLLECTIONS`, and `QUEUE`.

- **Events**: accessible via `events()`, returning an ordered list. Events include messages (`Message`), external messages (`MessageExo`), and non-connection events (notes, delays, dividers, groupings). Each `Message` object references its source and target `Participant` objects.

**Element extraction**: The tool iterates over `participants()` and accumulates counts by `ParticipantType`.

**Connection extraction**: The tool iterates over `events()`, filtering for `Message` and `MessageExo` instances, and counts each as a connection. Messages between two participants are classified as `"message"`; messages originating from or directed to an external actor are classified as `"message_exo"`.

### 4.3 Strategy 3: Activity Diagrams (ActivityDiagram3)

**Applicable diagram types**: activity (beta syntax)

Modern activity diagrams use a tree-structured intermediate representation composed of `Instruction` nodes. The tool extracts both elements and connections from this single tree: each `Instruction` node is counted as one **element** (a vertex in the control flow graph), while the implicit control flow relationships between nodes are counted as **connections** (edges in the control flow graph). Unlike entity-link diagrams, where elements and connections are stored in separate collections, here both are derived from the same tree — but they remain disjoint, as nodes and edges are different graph primitives.

The parser constructs a composite tree where compound instructions contain child instructions:

- `InstructionList` represents sequential composition of its N children.
- `InstructionIf` represents conditional branching with a list of `Branch` objects (one per `then`/`else if` path) and an optional `else` branch.
- `InstructionWhile` represents pre-test iteration containing a loop body.
- `InstructionRepeat` represents post-test iteration (repeat-until) containing a loop body.
- `InstructionFork` represents concurrent execution with N parallel branches.
- `InstructionSwitch` represents multi-way branching (switch/case) with one branch per case.
- Leaf instructions (`InstructionSimple`, `InstructionStart`, `InstructionStop`, `InstructionEnd`) represent individual activity nodes with no children.

**Element extraction**: The tool traverses the instruction tree and counts each node as one element, labeled by its instruction type. Compound instructions are labeled by their control flow role (`"decision"` for `InstructionIf`, `"loop"` for `InstructionWhile`/`InstructionRepeat`, `"fork"` for `InstructionFork`, `"switch"` for `InstructionSwitch`). Leaf instructions derive their label from their class name (e.g., `InstructionSimple` produces `"simple"`, `InstructionStart` produces `"start"`).

**Connection extraction**: The tool performs a separate depth-first traversal of the same tree, this time counting the control flow edges implied by each node's semantics rather than the nodes themselves:

- `InstructionList` with N children: N-1 `"sequential"` edges between consecutive children.
- `InstructionIf`: one `"branch"` edge per conditional path from the decision point, plus one `"merge"` edge where paths reconverge.
- `InstructionWhile`: three edges — `"loop_entry"` into the body, `"loop_back"` from body to condition, and `"loop_exit"` when the condition fails.
- `InstructionRepeat`: the same three edge types as `InstructionWhile`.
- `InstructionFork` with N branches: N `"fork_split"` edges (fork bar to each branch) and N `"fork_join"` edges (each branch to join bar).
- `InstructionSwitch`: one `"branch"` edge per case, plus one `"merge"` edge at reconvergence.
- Leaf instructions: no edges (they are endpoints, not sources of additional control flow).

## 5. Diagram Type Identification

The extraction tool derives the diagram type name from PlantUML's internal `UmlDiagramType` enumeration, which is assigned during parsing. The enum value is converted to lowercase to produce the output label (e.g., `UmlDiagramType.CLASS` becomes `"class"`, `UmlDiagramType.STATE` becomes `"state"`). One mapping adjustment is applied: `UmlDiagramType.DESCRIPTION` — PlantUML's internal designation for component and deployment-style diagrams — is emitted as `"component"` for consistency with standard UML terminology.

## 6. Output Format

The tool emits one JSON object per diagram block to standard output, formatted as JSON Lines (JSONL). The schema is:

```json
{
  "file": "<filename>",
  "diagram_type": "<type>",
  "elements": {"<element_type>": <count>, ...},
  "elements_total": <int>,
  "connections": {"<connection_type>": <count>, ...},
  "connections_total": <int>,
  "error": null
}
```

- `file`: the input filename, with a numeric suffix appended for multi-diagram files (e.g., `"diagram.puml_1"` for the second block).
- `diagram_type`: one of `"class"`, `"sequence"`, `"activity"`, `"state"`, `"component"`, `"object"`, or the lowercase name of any other `UmlDiagramType` value. Null if parsing failed.
- `elements`: a dictionary mapping element type labels to occurrence counts. Keys are dynamic and depend on the diagram type and its contents.
- `connections`: a dictionary mapping connection type labels to occurrence counts. Keys are dynamic and depend on the diagram type.
- `error`: null on success; a descriptive string on failure (e.g., `"parse_error"`, `"unsupported_type:<class>"`, `"io_error:<message>"`).

Files that fail PlantUML's parser produce an error record with `diagram_type: null` and zero counts rather than being silently omitted.

## 7. Coverage and Limitations

### 7.1 Diagram Type Coverage

| Strategy | Diagram Types | Internal Representation |
|----------|--------------|------------------------|
| Entity-Link (CucaDiagram) | class, object, component, deployment, use case, state | Entity + Link collections |
| Sequence (SequenceDiagram) | sequence | Participant + Event lists |
| Activity (ActivityDiagram3) | activity (beta syntax) | Instruction tree |

Together, these three strategies cover the nine diagram types present in the dataset. Diagram types not matching any strategy (e.g., timing, mind map, Gantt) are reported with an `unsupported_type` error code.

### 7.2 Accuracy Characteristics

Because the extraction tool operates on PlantUML's own parsed intermediate representation, element and connection counts are by construction consistent with the compiler's interpretation of the input. This eliminates the classes of errors inherent in regex-based approaches:

- **Syntax variant handling**: PlantUML supports multiple syntactic forms for the same construct (e.g., `class Foo`, `class "Foo Bar" as FB`, bracket notation `[Component]`, lollipop notation `() Interface`). All variants are resolved by the parser into the same internal entity types.
- **Alias and namespace resolution**: Entities referenced by alias or qualified name are resolved to their canonical identity by the parser.
- **Implicit connection resolution**: Activity diagram control flow edges that have no textual arrow representation are fully captured through the instruction tree traversal.
- **Preprocessor-dependent content**: Entities and connections defined within included files, macro expansions, or conditional blocks are included after preprocessing.

### 7.3 Limitations

- **Compilation failures**: Diagrams that fail PlantUML's parser (22% of the dataset) cannot be analyzed by this tool. For these files, the tool emits an error record. A fallback to regex-based counting may be applied to these files at the cost of reduced accuracy.
- **Activity diagram element semantics**: Activity diagram nodes (actions) are behavioral rather than structural. The tool counts them as instruction-type occurrences (e.g., `"simple"`, `"start"`, `"stop"`) rather than as UML structural elements. This is consistent with the UML metamodel, where actions are not classifiers.
- **Legacy activity syntax**: The legacy activity diagram syntax (explicit arrows between quoted action names) is parsed by PlantUML into a different internal representation (`ActivityDiagram`, a subclass of `CucaDiagram`). These diagrams are handled by Strategy 1 rather than Strategy 3.

## 8. Implementation

The extraction tool is implemented as a single Java class (`DiagramStatsExtractor`) embedded within the PlantUML source tree at `net.sourceforge.plantuml.stats`. Placement within the PlantUML package hierarchy grants access to package-private members of the instruction tree classes, which are required for the activity diagram traversal (Strategy 3). Nine minimal public getter methods were added to PlantUML's `activitydiagram3` package classes to expose the private fields of the instruction tree nodes (`InstructionList.getAll()`, `InstructionIf.getThens()`, `InstructionIf.getElseBranch()`, `InstructionWhile.getRepeatList()`, `InstructionRepeat.getRepeatList()`, `InstructionFork.getForks()`, `InstructionSwitch.getSwitches()`, `Branch.getInstructionList()`, and `ActivityDiagram3.getRootInstruction()`). No modifications were made to PlantUML's parsing logic, command definitions, or diagram construction code.

**Build**: The tool is compiled together with PlantUML using the project's Gradle build system (`./gradlew build -x test -x javaDoc`), producing a single executable JAR file containing the tool and all PlantUML dependencies.

**Execution**:
```
java -cp plantuml-<version>.jar net.sourceforge.plantuml.stats.DiagramStatsExtractor [--dir <directory> | <file.puml> ...]
```

**Batch processing**: The tool accepts multiple file paths or a directory argument, processing all files within a single JVM process to avoid per-file startup overhead. Processing 162,257 diagrams completes within a single execution.

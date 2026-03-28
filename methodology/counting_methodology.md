# Parser-Based Element and Connection Extraction Methodology

## 1. Motivation

We developed an extraction tool that reuses the PlantUML compiler's own internal parser and data model. Rather than attempting to replicate PlantUML's parsing logic through pattern matching, we invoke the same code path that PlantUML uses to compile diagrams for rendering, then inspect the resulting intermediate representation to extract element and connection counts.

## 2. Approach Overview

The extraction tool operates as a Java program embedded within the PlantUML source tree (version 1.2025.9). It reuses PlantUML's parsing pipeline — including preprocessing (macro expansion, file inclusion, conditional compilation), lexical analysis, and diagram-type-specific command interpretation — to produce fully resolved diagram objects. The tool then inspects these objects to enumerate structural elements and connections, outputting per-diagram statistics in JSON Lines (JSONL) format.

This approach ensures that element and connection counts reflect the same interpretation of PlantUML syntax that the compiler itself applies when generating visual output. Any valid PlantUML construct — including aliases, stereotypes, shorthand notations, qualified names, and implicit flows — is handled by the compiler's existing logic rather than by independent reimplementation.

## 3. Parsing Pipeline

For each input file, the tool invokes PlantUML's full parsing pipeline: preprocessing (macro expansion, `!include` resolution, conditional compilation), diagram type detection, and type-specific command interpretation. This produces a fully resolved diagram object — the same intermediate representation that PlantUML uses to render visual output. The tool then inspects this object to extract element and connection counts.

## 4. Extraction Strategies

The tool extracts two disjoint metrics from each parsed diagram: **elements** (the nodes of the diagram's underlying graph) and **connections** (the edges between those nodes). A given diagram construct is counted as either an element or a connection, never both. Three extraction strategies are used, dispatched based on the diagram's internal representation:

| Diagram family | Diagram types | Elements extracted | Connections extracted |
|---|---|---|---|
| Entity-link | class, object, component, deployment, use case, state | UML entity types (e.g., `class`, `interface`, `enum`, `abstract_class`, `component`, `state`, `usecase`, `package`) | Relationship types by endpoint decoration (e.g., `extends`, `composition`, `aggregation`, `arrow`, `none`) |
| Sequence | sequence | Participant types (e.g., `participant`, `actor`, `boundary`, `control`, `entity`, `database`, `queue`) | Messages: `message` (inter-participant), `message_exo` (external) |
| Activity | activity | Control flow nodes (e.g., `simple`, `decision`, `loop`, `fork`, `switch`, `start`, `stop`) | Control flow edges (e.g., `sequential`, `branch`, `merge`, `loop_entry`/`loop_back`/`loop_exit`, `fork_split`/`fork_join`) |

### 4.1 Entity-Link Diagrams

Six diagram types (class, object, component, deployment, use case, state) share a common internal representation where elements and connections are stored in separate collections. The parser assigns each element a typed label identifying its UML type (e.g., `class`, `interface`, `enum`, `component`, `state`) and each connection a type label derived from its endpoint decorations. The tool reads both collections and accumulates per-type counts.

Connection types are classified using a priority-based scheme that inspects the decorations on both endpoints of each link. The tool selects the most semantically specific decoration present on either end, checked in the following order: `extends` (UML generalization — triangle arrowhead), `composition` (filled diamond), `aggregation` (open diamond), `redefines`, `definedby`, `arrow` (plain arrowhead — covers directed associations and dependencies), `none` (undecorated line — undirected associations). If neither endpoint matches any of these, the tool falls back to the decoration's internal enum name (e.g., `circle_crowfoot`, `half_arrow_up`). This means a link with `extends` on one end and `arrow` on the other is classified as `extends`, not as two separate relationships. The priority ordering reflects UML semantics: specific relationship types (generalization, composition) take precedence over generic directional markers.

### 4.2 Sequence Diagrams

Sequence diagrams represent participants and events. The tool counts participants by their type (`participant`, `actor`, `boundary`, `control`, `entity`, `database`, `collections`, `queue`) as elements, and counts messages between participants as connections. Inter-participant messages are classified as `message`; messages directed to or from outside the diagram boundary are classified as `message_exo`.

The tool counts only message events, not other sequence diagram constructs. Combined fragments (`alt`, `opt`, `loop`, `break`, `par`, `critical`, `group`), notes, dividers (`==`), delays (`...`), and references (`ref`) are not counted as either elements or connections. This scope reflects the tool's focus on the graph structure of diagrams — participants as nodes, messages as edges — rather than on behavioral annotations that constrain or organize the message flow.

### 4.3 Activity Diagrams

Activity diagrams use a tree-structured intermediate representation where each node represents a control flow construct. The tool performs two traversals of this tree: one counting nodes as elements, and another counting the implicit control flow edges between nodes as connections. These connections represent edges in the abstract control flow graph (nodes = instructions, edges = control flow between them), not visual arrows in the rendered diagram. The two counts generally differ: compound instruction exit edges (e.g., merge, loop exit) and sequential edges to the next instruction may share a single visual arrow, while merge points with multiple incoming branches render as multiple visual arrows but count as a single structural edge.

The element labels used by the tool are derived from PlantUML's internal instruction types rather than standard UML terminology. The following table shows the correspondence:

| Tool label | UML 2.5 equivalent |
|---|---|
| simple | Action node |
| start | Initial node |
| stop, end | Activity final node, flow final node |
| decision | Decision / merge node |
| loop | Loop node (structured, maps to decision + merge) |
| fork | Fork / join node |
| switch | Decision node (multi-way) |

Note that activity diagram elements are behavioral (control flow nodes) rather than structural (UML classifiers), consistent with the UML metamodel.

**Merge as connection, not element.** In the UML 2.5 metamodel, a MergeNode is a control node (i.e., an element), not an edge. The tool instead counts merge as a connection — representing "branches converge here" — rather than as a separate element. This is because PlantUML's `InstructionIf` tree node implicitly contains both the decision point (entry) and the merge point (exit) as a single compound instruction; the tool counts the entry as a `decision` element and the exit as a `merge` connection. The same applies to `switch` blocks. This modeling choice keeps the element count focused on constructs the user explicitly wrote (actions, decisions, loops) rather than structural artifacts of the control flow graph. The merge count is still available in the connection data for researchers who need it.

### 4.4 Implementation Details

Full details of the Java class hierarchy, enum types, and tree traversal rules are documented in the tool's source repository. In summary: entity-link diagrams use PlantUML's `LeafType` and `GroupType` enumerations for elements and `LinkDecor` for connection classification; sequence diagrams use `ParticipantType` for elements and filter the event list for messages; activity diagrams map compound instruction nodes (conditionals, loops, forks) to control flow element labels and derive edge counts from each node's branching semantics.

## 5. Diagram Type Identification

The extraction tool derives the diagram type name from PlantUML's internal `UmlDiagramType` enumeration, which is assigned during parsing. The enum value is converted to lowercase to produce the output label (e.g., `UmlDiagramType.CLASS` becomes `"class"`, `UmlDiagramType.STATE` becomes `"state"`). One mapping adjustment is applied: `UmlDiagramType.DESCRIPTION` — PlantUML's internal designation that encompasses component, deployment, and use case diagrams — is emitted as `"component"`. Because the parser cannot distinguish between these three UML types (see `classification_methodology.md` for details), the parser-derived type serves only as a validation signal, while the LLM classification provides the primary diagram type label used in the dataset.

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
| Entity-Link | class, object, component, deployment, use case, state | Entity + Link collections |
| Sequence | sequence | Participant + Event lists |
| Activity | activity | Instruction tree |

Together, these three strategies cover the nine diagram types present in the dataset. Diagram types not matching any strategy are reported with an `unsupported_type` error code. The following unsupported types were encountered in the dataset:

| Error code | Count | Explanation |
|---|---|---|
| `unsupported_type:TimingDiagram` | 178 | Timing diagrams use a distinct internal representation not covered by the three extraction strategies. Since timing diagrams constitute only 0.1% of the dataset (189 total), dedicated support was not implemented. |
| `unsupported_type:NewpagedDiagram` | 167 | Multi-page diagrams using the `newpage` keyword produce a `NewpagedDiagram` wrapper that the tool does not unwrap. |
| `unsupported_type:PSystemMath` | 1 | LaTeX math notation block (`@startmath`/`@startlatex`), not a UML diagram. |
| `unsupported_type:PSystemVersion` | 1 | PlantUML `@startversion` block displaying version info. |
Additionally, 84 diagrams with `unsupported_type:PSystemDot` errors (Graphviz DOT passthrough using raw `digraph`/`graph` syntax within `@startuml` blocks) were identified by the extraction tool and subsequently removed from the dataset during filtering (see methodology §6.2.5).

### 7.2 Accuracy Characteristics

Because the extraction tool operates on PlantUML's own parsed intermediate representation, element and connection counts are by construction consistent with the compiler's interpretation of the input. This eliminates the classes of errors inherent in regex-based approaches:

- **Syntax variant handling**: PlantUML supports multiple syntactic forms for the same construct (e.g., `class Foo`, `class "Foo Bar" as FB`, bracket notation `[Component]`, lollipop notation `() Interface`). All variants are resolved by the parser into the same internal entity types.
- **Alias and namespace resolution**: Entities referenced by alias or qualified name are resolved to their canonical identity by the parser.
- **Implicit connection resolution**: Activity diagram control flow edges that have no textual arrow representation are fully captured through the instruction tree traversal.
- **Preprocessor-dependent content**: Entities and connections defined within included files, macro expansions, or conditional blocks are included after preprocessing.

### 7.3 Limitations

- **Compilation failures**: Diagrams that fail PlantUML's parser (22% of the pre-filtered dataset) cannot be analyzed by this tool. For these files, the tool emits an error record.
- **Extraction errors**: Of the 143,427 diagrams in the final dataset, 347 (0.2%) produced extraction errors — predominantly timing diagrams (178) and newpage diagrams (167), with 2 additional edge cases. Element and connection counts are unavailable for these diagrams.
- **Phantom convergence edges**: The tool unconditionally counts convergence edges for compound instructions, regardless of whether any branch actually flows through to the convergence point. Specifically: (1) 1 `merge` connection is counted for every `if` and `switch` block, even when all branches terminate with `stop` or `end` before reaching the merge point; (2) N `fork_join` connections are counted for every `fork` with N branches, even when branches terminate with `end` and never rejoin. This results in a slight overcount of connections in diagrams where branches terminate early.
- **Auto-generated links counted as connections**: In entity-link diagrams, PlantUML's internal link collection includes links generated automatically by the rendering pipeline that do not correspond to user-written arrows in the source. These appear as `none` connections in the tool's output. Three mechanisms were identified: (1) **Note attachment links** — PlantUML creates `NONE`/`NONE` links to position notes relative to their target entities (`note left of X`, `note right of X`). One link per attached note; floating notes without attachment do not produce links. (2) **Implicit type-dependency links** — in class diagrams, when a field or method parameter references a type that is also defined in the diagram (e.g., `status: AppointmentStatusType` where `AppointmentStatusType` is a declared enum), PlantUML auto-generates a dependency link between the two entities. (3) **Layout arrangement links** — during diagram finalization, PlantUML identifies standalone entities not referenced by any explicit link and creates invisible `NONE`/`NONE` links to arrange them in a grid layout for rendering. This affects any entity-link diagram type. All three mechanisms are internal to PlantUML's diagram construction and rendering pipeline; the extraction tool observes them as returned by `getLinks()`. There is no flag in PlantUML's `Link` object to distinguish auto-generated links from user-written relationships, so the tool cannot filter them. This affects all entity-link diagram types (class, object, component, deployment, usecase, state, and legacy activity). Manual validation of a stratified sample of 30 class diagrams found that 7 (23%) contained phantom `none` connections from these sources, with overcounts ranging from 2 to 9 per diagram.
- **Legacy activity syntax**: PlantUML supports a legacy activity diagram syntax (explicit arrows between quoted action names) that uses a different internal representation (`CucaDiagram` rather than `ActivityDiagram3`). These diagrams are handled by the entity-link strategy rather than the activity tree traversal strategy. As a consequence, the same UML concept may appear under different type keys depending on the syntax used: for example, an action node is labeled `simple` in modern (beta) syntax but `activity` (from `LeafType.ACTIVITY`) in legacy syntax; a decision node is `decision` in modern syntax but `branch` (from `LeafType.BRANCH`) in legacy syntax. Researchers aggregating element counts across activity diagrams should be aware of this labeling inconsistency.

## 8. Implementation

The extraction tool is implemented as a single Java class (`DiagramStatsExtractor`) embedded within the PlantUML source tree at `net.sourceforge.plantuml.stats`. Placement within the PlantUML package hierarchy grants access to package-private members of the instruction tree classes, which are required for the activity diagram traversal (Strategy 3). Nine minimal public getter methods were added to PlantUML's `activitydiagram3` package classes to expose the private fields of the instruction tree nodes (`InstructionList.getAll()`, `InstructionIf.getThens()`, `InstructionIf.getElseBranch()`, `InstructionWhile.getRepeatList()`, `InstructionRepeat.getRepeatList()`, `InstructionFork.getForks()`, `InstructionSwitch.getSwitches()`, `Branch.getInstructionList()`, and `ActivityDiagram3.getRootInstruction()`). No modifications were made to PlantUML's parsing logic, command definitions, or diagram construction code.

**Build**: The tool is compiled together with PlantUML using the project's Gradle build system (`./gradlew build -x test -x javaDoc`), producing a single executable JAR file containing the tool and all PlantUML dependencies.

**Execution**:
```
java -cp plantuml-<version>.jar net.sourceforge.plantuml.stats.DiagramStatsExtractor [--dir <directory> | <file.puml> ...]
```

**Batch processing**: The tool accepts multiple file paths or a directory argument, processing all files within a single JVM process to avoid per-file startup overhead. Processing 143,427 diagrams completes within a single execution.

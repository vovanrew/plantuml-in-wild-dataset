# Element Type Key Reference

All 57 element type keys observed in the dataset, organized by diagram family. Each key is the lowercased name of a PlantUML internal enum value or instruction class name.

## Entity-Link Diagrams

Keys produced by `LeafType.name().toLowerCase()` and `GroupType.name().toLowerCase()`. These apply to class, object, component, deployment, usecase, and state diagrams.

### Class / Object Diagram Entities

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `class` | 444,111 | `class Foo`, `class "Foo Bar" as F` | Class |
| `interface` | 63,894 | `interface Foo` | Interface |
| `abstract_class` | 25,085 | `abstract class Foo`, `abstract Foo` | Abstract class |
| `enum` | 12,993 | `enum Foo` | Enumeration |
| `entity` | 12,255 | `entity Foo` | Entity (ER-style in class diagrams) |
| `annotation` | 1,116 | `annotation Foo` | Annotation (Java-style) |
| `circle` | 650 | `circle Foo` | Circle node (interface ball in component/class) |
| `struct` | 156 | `struct Foo` | Struct |
| `association` | 46 | (implicit) | Diamond node created by association class syntax (`(A, B) .. C`) |
| `protocol` | 33 | `protocol Foo` | Protocol (Kotlin/Swift-style) |
| `json` | 8 | `json "Name" as Alias { ... }` | Inline JSON data structure |
| `lollipop_half` | 3 | Half lollipop notation | Half lollipop (required interface) |
| `exception` | 1 | `exception Foo` | Exception class |

### Object Diagram Specific

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `object` | 19,276 | `object Foo`, `object "Foo" as F` | Object instance |
| `map` | 145 | `map Foo { key => value }` | Map data structure |

### Component / Deployment / Usecase Diagram Entities

In these three diagram types, PlantUML uses a shared internal representation (`DescriptionDiagram`). Most entity keywords produce the same `description` leaf type.

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `description` | 93,328 | `component Foo`, `[Foo]`, `actor Foo`, `:Foo:`, `node Foo`, `artifact Foo`, `database Foo`, `cloud Foo`, `folder Foo`, `frame Foo`, `storage Foo`, `card Foo`, `queue Foo`, `stack Foo`, `file Foo`, `hexagon Foo`, `label Foo`, `collections Foo`, `rectangle Foo` | Shared type for most entities in component/deployment/usecase diagrams. All the listed keywords produce this same key. |
| `usecase` | 50,805 | `usecase Foo`, `usecase "Foo" as F`, `(Foo)` | Use case (has its own leaf type, unlike other description entities) |
| `usecase_business` | 216 | `usecase/ Foo /` | Business use case variant |
| `lollipop_full` | 616 | `() Foo` (provided interface in component) | Full lollipop (provided interface) |

### State Diagram Entities

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `state` | 34,090 | `state Foo` (simple state, no body) | State. Also produced by `GroupType.STATE` for composite states (`state Foo { ... }`). Both contribute to this key. |
| `circle_start` | 7,491 | `[*] -->` (as source of transition) | Initial pseudostate |
| `circle_end` | 4,054 | `--> [*]` (as target of transition) | Final pseudostate |
| `state_choice` | 679 | `state choice <<choice>>`, diamond `<<choice>>` | Choice pseudostate |
| `state_fork_join` | 228 | `state forkpoint <<fork>>`, `state joinpoint <<join>>` | Fork/join bar in state diagrams |
| `pseudo_state` | 117 | `state ep <<entryPoint>>`, `state ep <<exitPoint>>` | Entry/exit point pseudostate |
| `deep_history` | 9 | `[H*]` | Deep history pseudostate |

### Legacy Activity Diagram Entities

Legacy activity syntax uses the entity-link strategy. These keys come from `LeafType` values specific to the old activity notation.

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `activity` | 16,907 | `"Do something"` (quoted action in legacy syntax), `(*) --> "action"` | Action node (legacy activity syntax) |
| `branch` | 3,180 | `if "condition" then`, `(*) --> if "" then` | Decision node (legacy activity syntax) |
| `synchro_bar` | 864 | `=== B1 ===` | Synchronization bar (legacy activity syntax) |
| `circle_start` | (shared) | `(*)` as source | Initial node (legacy activity syntax). Shares key with state diagram initial pseudostate. |
| `circle_end` | (shared) | `(*)` as target | Final node (legacy activity syntax). Shares key with state diagram final pseudostate. |

### Shared Entities (All Entity-Link Types)

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `note` | 20,170 | `note "text" as N`, `note left of X: text`, `note right: text`, `note top of X`, floating notes | Note element. Appears in all entity-link diagram types. |
| `tips` | 832 | `note` on a specific entity via `tip` command | Tip/hint marker attached to an entity (internal PlantUML construct) |
| `point_for_association` | 977 | (implicit) | Hidden connection point. Created internally when PlantUML routes complex association paths. |

### Port Entities

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `portin` | 179 | `portin Foo` | Input port |
| `portout` | 30 | `portout Foo` | Output port |

### Group Containers

Keys from `GroupType.name().toLowerCase()`. The implicit `ROOT` group is excluded by the extraction tool.

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `package` | 157,539 | `package Foo { }`, `namespace Foo { }`, `rectangle Foo { }` (as grouping) | Package, namespace, or rectangle group container |
| `state` | (shared) | `state Foo { ... }` (with body — composite state) | Composite state group. Shares the `state` key with leaf states. |
| `concurrent_state` | 281 | `state Foo { ... -- ... }` (concurrent regions separated by `--`) | Concurrent state region |

---

## Sequence Diagrams

Keys produced by `ParticipantType.name().toLowerCase()`. Each participant declaration (explicit or implicit) produces one element.

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `participant` | 130,938 | `participant Foo`, or implicit first use in a message (e.g., `Foo -> Bar`) | Participant lifeline (default type) |
| `actor` | 20,830 | `actor Foo` | Actor lifeline |
| `database` | 7,242 | `database Foo` | Database lifeline |
| `control` | 4,870 | `control Foo` | Control lifeline |
| `boundary` | 4,070 | `boundary Foo` | Boundary lifeline |
| `collections` | 2,005 | `collections Foo` | Collections lifeline |
| `queue` | 606 | `queue Foo` | Queue lifeline |
| `entity` | (shared) | `entity Foo` | Entity lifeline. Shares the `entity` key with ER-style entities in class diagrams. |

Note: The same keywords (`database`, `actor`, `collections`, `queue`, `entity`) produce different keys depending on diagram type. In sequence diagrams, they produce the participant type keys listed above. In component/deployment/usecase diagrams, they produce `description`.

---

## Activity Diagrams (Modern/Beta Syntax)

Element keys come from two mechanisms in the extraction tool:
- **Compound instructions** are explicitly mapped: `InstructionIf` → `decision`, `InstructionWhile`/`InstructionRepeat` → `loop`, `InstructionFork` → `fork`, `InstructionSwitch` → `switch`
- **Leaf instructions** use class name stripping: `InstructionX` → `x` (lowercased, "Instruction" prefix removed)

### Compound Instructions (Explicit Mapping)

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `decision` | 12,759 | `if (...) then (...)` / `elseif (...)` / `else (...)` / `endif` | Decision node. One per `if` block regardless of how many `elseif` clauses. |
| `loop` | 3,990 | `while (...) is (...)` / `endwhile`, `repeat` / `repeat while (...)` | Loop construct. One per `while` or `repeat` block. |
| `fork` | 1,305 | `fork` / `fork again` / `end fork` | Fork/join construct. One per `fork` block. |
| `switch` | 145 | `switch (...)` / `case (...)` / `endswitch` | Multi-way switch. One per `switch` block. |

**Properties:**
- `decision`: An `if` with 3 `elseif` clauses and an `else` is still 1 `decision` element. The number of branches affects connection counts (`branch`, `merge`), not the element count.
- `loop`: Always equals the total of `loop_entry` (or `loop_back` or `loop_exit`) in connection counts — each loop produces exactly 1 element and 3 connections.
- `fork`: The fork and its join bar are counted as a single element. The number of parallel branches affects connection counts (`fork_split`, `fork_join`), not the element count.

### Leaf Instructions (Class Name Stripping)

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `simple` | 68,677 | `:action text;`, `:multi\nline;` | Action node (the colon-semicolon notation) |
| `stop` | 8,958 | `stop` | Activity final node (filled circle with border) |
| `start` | 7,313 | `start` | Initial node (filled circle) |
| `end` | 2,205 | `end` | Flow final node (circle with X) |
| `group` | 3,516 | `group "label" { }`, `partition "label" { }`, `package "label" { }`, `rectangle "label" { }`, `card "label" { }` (beta syntax only) | Group container in activity diagram (beta/modern syntax). PlantUML's own parser routes all five grouping keywords through `InstructionGroup` (via `CommandPartition3`) — only the visual style differs. This is PlantUML's internal representation, not a tool-specific mapping. In legacy activity syntax, these keywords produce their entity-link keys instead (e.g., `package` → `package`). |
| `split` | 729 | `split` / `split again` / `end split` | Split construct (parallel without join) |
| `spot` | 503 | `(X)` colored spot marker | Spot/colored circle marker |
| `label` | 86 | `label labelname` | Label (goto target) |
| `break` | 110 | `break` | Break out of enclosing construct |
| `goto` | 27 | `goto labelname` | Goto jump to label |

---

## Key Disambiguation

Several keys appear in multiple diagram families with different meanings:

| Key | In Entity-Link | In Sequence | In Activity |
|-----|----------------|-------------|-------------|
| `entity` | ER-style entity (`LeafType.ENTITY`) | Entity lifeline (`ParticipantType.ENTITY`) | — |
| `state` | Leaf state (`LeafType.STATE`) + composite state group (`GroupType.STATE`) | — | — |
| `database` | Produces `description` | Database lifeline (`ParticipantType.DATABASE`) | — |
| `collections` | Produces `description` | Collections lifeline (`ParticipantType.COLLECTIONS`) | — |
| `queue` | Produces `description` | Queue lifeline (`ParticipantType.QUEUE`) | — |
| `circle_start` | Initial pseudostate in state diagrams | — | Initial node in legacy activity |
| `circle_end` | Final pseudostate in state diagrams | — | Final node in legacy activity |
| `branch` | Decision node in legacy activity (`LeafType.BRANCH`) | — | — |

---

## Keys NOT Observed in Dataset

The following `LeafType` values exist in PlantUML's enum but were never encountered in the 143,427 diagrams:

`empty_package`, `metaclass`, `stereotype`, `dataclass`, `record`, `arc_circle`, `activity_concurrent`, `state_concurrent` (as leaf), `state_transition_label`, `block`, `domain` (as leaf), `requirement` (as leaf), `chen_entity`, `chen_relationship`, `chen_attribute`, `chen_circle`, `still_unknown`

The following `GroupType` values were not observed: `inner_activity`, `concurrent_activity`, `domain`, `requirement`

The following activity instruction was not observed: `partition` (from `InstructionPartition`). Note: `InstructionPartition` is effectively dead code — PlantUML routes all five grouping keywords (`partition`, `package`, `rectangle`, `card`, `group`) through `InstructionGroup` via `CommandPartition3`, so the `partition` key can never appear in practice. The `partition` keyword in source produces the `group` key in tool output.

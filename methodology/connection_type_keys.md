# Connection Type Key Reference

All 28 connection type keys observed in the dataset, organized by diagram family.

## Entity-Link Diagrams

Keys produced by the `classifyLinkDecor` method, which inspects the `LinkDecor` enum value on both endpoints of each link and selects the highest-priority decoration. These apply to class, object, component, deployment, usecase, and state diagrams (including legacy activity diagrams handled via the entity-link strategy).

### Priority-Based Classification

The tool checks both endpoints and returns the first match from this priority list:

| Priority | Key | Count | LinkDecor Enum | PlantUML Arrow Syntax | Description |
|:--------:|-----|------:|----------------|----------------------|-------------|
| 1 | `extends` | 211,429 | `EXTENDS` | `<\|--`, `--\|>`, `<\|..`, `..\|>` | Generalization (triangle arrowhead). Covers both inheritance (solid line) and realization (dashed line) when using the standard `\|>` notation. |
| 2 | `composition` | 51,014 | `COMPOSITION` | `*--`, `--*`, `*..`, `..*` | Composition (filled diamond) |
| 3 | `aggregation` | 59,507 | `AGREGATION` | `o--`, `--o`, `o..`, `..o` | Aggregation (open diamond). Note: PlantUML's internal enum uses the misspelling `AGREGATION`. |
| 4 | `redefines` | 46 | `REDEFINES` | `<\|\|--`, `--\|\|>`, `<\|\|..`, `..\|\|>` | Redefines relationship (double-bar triangle) |
| 5 | `definedby` | — | `DEFINEDBY` | `<\|:--`, `--:\|>` | Defined-by relationship (colon triangle). Not observed in dataset (0 count). |
| 6 | `arrow` | 367,297 | `ARROW`, `ARROW_TRIANGLE` | `-->`, `<--`, `..>`, `<..`, `->`, `<-`, `<<--`, `-->>` | Directed association or dependency (plain arrowhead). Both single (`>`) and double (`>>`) arrowheads map to this key. Dashed lines (`..>`) also produce `arrow`. |
| 7 | `none` | 141,227 | `NONE` (both ends) | `--`, `..` | Undirected association (plain line, no decoration on either end). Both solid and dashed lines with no endpoint symbols. **Note**: this count is inflated by auto-generated `NONE`/`NONE` links that PlantUML creates internally: (1) note attachment links, (2) implicit type-dependency links in class diagrams when fields reference defined types, and (3) layout arrangement links for standalone entities with no explicit connections. These cannot be distinguished from genuine undirected associations at the Link API level. Manual validation found 23% of class diagrams affected. |

### Fallback Classification

If neither endpoint matches priorities 1–7, the tool uses the `LinkDecor` enum name (lowercased) of whichever endpoint is not `NONE`. These are less common ER/crowfoot and specialty decorations:

| Key | Count | LinkDecor Enum | PlantUML Arrow Syntax | Description |
|-----|------:|----------------|----------------------|-------------|
| `plus` | 6,573 | `PLUS` | `--+`, `+--` | Plus/cross decoration. Used in component diagrams for assembly connectors. |
| `parenthesis` | 1,403 | `PARENTHESIS` | `--(`, `)--` | Parenthesis decoration (socket/required interface notation) |
| `crowfoot` | 929 | `CROWFOOT` | `--{`, `}--` | Crowfoot (many) in ER notation |
| `circle_crowfoot` | 566 | `CIRCLE_CROWFOOT` | `--o{`, `}o--` | Crowfoot with circle (zero-or-many) |
| `square` | 554 | `SQUARE` | `--#`, `#--` | Square decoration |
| `double_line` | 543 | `DOUBLE_LINE` | `--\|\|`, `\|\|--` | Double line (one-and-only-one in ER notation) |
| `line_crowfoot` | 438 | `LINE_CROWFOOT` | `--\|{`, `}\|--` | Line with crowfoot (one-or-many) |
| `circle_line` | 173 | `CIRCLE_LINE` | `--o\|`, `\|o--` | Circle with line (zero-or-one) |
| `not_navigable` | 55 | `NOT_NAVIGABLE` | `--x`, `x--` | Not navigable (X mark) |
| `arrow_and_circle` | 41 | `ARROW_AND_CIRCLE` | (rare, composite decoration) | Arrow combined with circle |
| `circle` | 36 | `CIRCLE` | `--0`, `0--` | Open circle decoration |
| `circle_connect` | 33 | `CIRCLE_CONNECT` | `--0)`, `(0--` | Circle connection (ball-and-socket) |

### Line Style Note

Solid lines (`--`) vs dashed lines (`..`) do NOT affect the connection type key. Only the endpoint decorations matter. For example:
- `A --> B` (solid, arrow) → `arrow`
- `A ..> B` (dashed, arrow) → `arrow`
- `A --|> B` (solid, triangle) → `extends`
- `A ..|> B` (dashed, triangle) → `extends`

### Asymmetric Links

When a link has different decorations on each end (e.g., `A *--|> B` with composition on the left and extends on the right), the **highest priority** decoration wins. In this example, `extends` (priority 1) outranks `composition` (priority 2), so the connection is classified as `extends`.

---

## Sequence Diagrams

Keys produced by checking the event type in the sequence diagram's event list. Only `Message` and `MessageExo` events are counted; all other events are skipped.

| Key | Count | PlantUML Syntax | Description |
|-----|------:|-----------------|-------------|
| `message` | 460,396 | `A -> B : text`, `A --> B`, `A ->> B`, `A -> A` (self-message), `A -\ B`, `A /- B`, return messages | Inter-participant message. Any arrow between two declared participants, regardless of arrow style (solid, dashed, lost, found, etc.). Self-messages count as one `message`. |
| `message_exo` | 5,077 | `[-> A : text`, `A ->]`, `[o-> A`, `A ->o]` | External message. Arrow to/from outside the diagram boundary (uses `[` or `]` to denote external origin/destination). |

### Not Counted as Connections

The following sequence diagram constructs are NOT counted:
- `activate`/`deactivate` — activation bars
- `alt`/`opt`/`loop`/`break`/`par`/`critical`/`group` — combined fragments
- `note left`/`note right`/`note over` — notes
- `== text ==` — dividers
- `...` — delays
- `ref over` — references
- `create`/`destroy` — the create/destroy keywords themselves (the associated message IS counted)
- `return` — the return keyword generates a message which IS counted

---

## Activity Diagrams (Modern/Beta Syntax)

Keys are hardcoded string literals in the `countActivityConnections` method. These represent implicit control flow graph edges derived from the instruction tree structure — they are NOT directly visible as individual arrows in the source or rendered diagram.

### Sequential Flow

| Key | Count | Derivation Rule | Description |
|-----|------:|-----------------|-------------|
| `sequential` | 67,579 | For N consecutive instructions in any instruction list: N − 1 edges | Edge between consecutive instructions. Counted at every nesting level (top-level, inside branches, inside loop bodies, inside fork branches). |

**Properties:**
- Compound instructions (`if`, `while`, `repeat`, `fork`, `switch` blocks) count as a single item in their parent list. An `if/endif` block followed by `stop` produces 1 sequential edge (the if block → stop), not separate edges for each branch exit.
- Must be counted at every nesting level — inside branch bodies, loop bodies, and fork branches, not just the top-level list.
- The "and then" relationship: instruction A finishes, then instruction B starts.

### Conditional Flow (if/switch)

| Key | Count | Derivation Rule | Description |
|-----|------:|-----------------|-------------|
| `branch` | 27,895 | For `if`: 1 per `then`/`elseif` branch + 1 if `else` present. For `switch`: 1 per `case`. | Edge from decision node into a branch. |
| `merge` | 12,904 | 1 per `if` block + 1 per `switch` block | Edge from end of branching back to single flow. Always exactly 1 per `if` or `switch`, regardless of branch count. |

**Properties:**
- `branch` scales with the number of branches; `merge` does not. An `if` with 4 `elseif` clauses and an `else` produces 6 `branch` edges but only 1 `merge` edge.
- `merge` is counted as a connection, not an element, even though the UML 2.5 metamodel defines MergeNode as a control node. This is because PlantUML's `InstructionIf` tree node contains both the decision and merge points as a single compound instruction.
- Even an `if` with an empty `else` branch produces 1 `merge` edge.
- **Known overcount**: The tool counts `merge` unconditionally for every `if`/`switch` block, even when all branches terminate with `stop` or `end` and no control flow reaches the merge point. These are phantom edges that don't correspond to real control flow.

### Loop Flow (while/repeat)

| Key | Count | Derivation Rule | Description |
|-----|------:|-----------------|-------------|
| `loop_entry` | 3,990 | 1 per `while` or `repeat` block | Edge entering the loop body (from condition/start of loop into the first instruction inside) |
| `loop_back` | 3,990 | 1 per `while` or `repeat` block | Back-edge returning from end of loop body to the condition check |
| `loop_exit` | 3,990 | 1 per `while` or `repeat` block | Edge exiting the loop when condition fails (continuing to the next instruction after the loop) |

**Properties:**
- Always equal counts: each loop produces exactly 1 of each, so `loop_entry` == `loop_back` == `loop_exit` always. Their dataset counts (3,990 each) confirm this invariant.
- 1 per loop block regardless of how many instructions are inside the loop body. Instructions inside are connected by `sequential` edges.
- 3 edges per loop total. The `loop` element count should always equal `loop_entry` count.

### Parallel Flow (fork)

| Key | Count | Derivation Rule | Description |
|-----|------:|-----------------|-------------|
| `fork_split` | 5,235 | For `fork` with N branches: N splits | Edge from fork bar into each parallel branch |
| `fork_join` | 5,235 | For `fork` with N branches: N joins | Edge from each parallel branch back to join bar |

**Properties:**
- Always equal counts in the tool's output: `fork_split` == `fork_join` always. Each fork produces N of each for N branches.
- Unlike `merge`, which is always 1 per block, fork split/join scales with the number of parallel branches.
- **Known overcount**: The tool counts `fork_join` unconditionally for every branch, even when branches terminate with `end`/`stop` and never rejoin. For example, a `fork` with 5 branches where 4 terminate with `end` will report `fork_join: 5`, but only 1 branch actually reaches the join point.

---

## Connection Keys NOT Observed in Dataset

The following `LinkDecor` values exist but were never encountered:
- `circle_fill` (`@` decoration)
- `circle_cross` (circle with X)
- `half_arrow_up` (`\\` decoration)
- `half_arrow_down` (`//` decoration)

The `definedby` key (priority 5 in the classification scheme) was also not observed.

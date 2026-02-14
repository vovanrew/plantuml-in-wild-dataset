# Plan: Reusing PlantUML Parsers for Element & Connection Extraction

## Goal

Replace custom regex-based element/connection counting with PlantUML's own parsers to achieve ~100% accuracy on the 162,257 diagrams that successfully compile. Key win: **un-exclude beta-syntax activity diagrams** from connection statistics (currently skipped due to ~52% regex accuracy).

## Architecture

```
input.puml
  → SourceStringReader (PlantUML API entry point)
    → BlockUml.getDiagram() (fully parsed diagram object)
      → instanceof check:
          CucaDiagram      → leafs() + getLinks()        [class, component, state, object, usecase, deployment]
          SequenceDiagram   → participants() + events()    [sequence]
          ActivityDiagram3  → instruction tree traversal   [activity beta-syntax]
      → JSON output: { elements: {...}, connections: {...} }
```

## Steps

### Step 1: Build PlantUML from source

Verify the project compiles in your environment.

```bash
cd /Users/vovapolischuk/indiehacker/projects/university/plantuml
gradle build -x test -x javaDoc
```

This produces a fat JAR at `build/libs/plantuml-<version>.jar` with all dependencies bundled.

### Step 2: Create the extractor class

Create a single Java file inside the PlantUML source tree:

```
src/main/java/net/sourceforge/plantuml/stats/DiagramStatsExtractor.java
```

Package `net.sourceforge.plantuml.stats` — being inside the `net.sourceforge.plantuml` hierarchy gives access to package-private fields (needed for ActivityDiagram3 instruction tree).

The class has a `main()` method that:
1. Reads a `.puml` file path from command-line args
2. Parses it with `SourceStringReader`
3. Dispatches to the appropriate extraction logic based on diagram type
4. Prints JSON to stdout

### Step 3: Implement extraction pattern 1 — CucaDiagram

Covers: **class, component, usecase, deployment, object, state** (~64% of dataset, ~104k diagrams)

```java
CucaDiagram cuca = (CucaDiagram) diagram;

// Elements
for (Entity entity : cuca.leafs()) {
    LeafType type = entity.getLeafType();   // CLASS, INTERFACE, ENUM, COMPONENT, STATE...
    // count by type
}
for (Entity group : cuca.groups()) {
    GroupType type = group.getGroupType();   // PACKAGE, STATE, CONCURRENT_STATE...
    // count by type
}

// Connections
for (Link link : cuca.getLinks()) {
    Entity from = link.getEntity1();
    Entity to = link.getEntity2();
    LinkDecor decor1 = link.getType().getDecor1();  // EXTENDS, COMPOSITION, AGREGATION...
    LinkDecor decor2 = link.getType().getDecor2();
    // count and classify
}
```

Key classes: `CucaDiagram`, `Entity`, `LeafType`, `GroupType`, `Link`, `LinkType`, `LinkDecor`

### Step 4: Implement extraction pattern 2 — SequenceDiagram

Covers: **sequence** (~22% of dataset, ~35k diagrams)

```java
SequenceDiagram seq = (SequenceDiagram) diagram;

// Elements
for (Participant p : seq.participants()) {
    ParticipantType type = p.getType();  // PARTICIPANT, ACTOR, BOUNDARY, CONTROL...
    // count by type
}

// Connections
for (Event event : seq.events()) {
    if (event instanceof Message) {
        Message msg = (Message) event;
        msg.getParticipant1();  // source
        msg.getParticipant2();  // target
        // count
    } else if (event instanceof MessageExo) {
        // external message (from/to outside)
        // count
    }
}
```

Key classes: `SequenceDiagram`, `Participant`, `ParticipantType`, `Event`, `Message`, `MessageExo`

### Step 5: Implement extraction pattern 3 — ActivityDiagram3

Covers: **activity** (~6% of dataset, ~9.8k diagrams) — **the biggest accuracy improvement**

This requires a recursive tree walk over the `Instruction` hierarchy. Each instruction type contributes a known number of connections:

| Instruction Type | Connections |
|---|---|
| `InstructionList` (sequential) | N-1 connections between N children + recurse each |
| `InstructionIf` | 1 per branch (then/else) + recurse each branch |
| `InstructionWhile` | 3 (entry + loop-back + exit) + recurse body |
| `InstructionFork` | 2*N (split into N + join from N) + recurse each |
| `InstructionSwitch` | 1 per case + recurse each |
| `InstructionRepeat` | 3 (entry + repeat-back + exit) + recurse body |
| `InstructionSimple` | 0 (leaf node) |
| `InstructionStart/Stop/End` | 0 (terminal) |

This is the only non-trivial part (~50 lines of recursive code). Some fields may be package-private, which is why the class lives inside the `net.sourceforge.plantuml` package.

For elements: activity diagrams have limited structural elements (partitions, swimlanes). Most "nodes" are actions (behavioral, not structural). Match your existing policy of only counting explicit containers.

### Step 6: Build and test on sample diagrams

```bash
# Rebuild with your new class
gradle build -x test -x javaDoc

# Run on a single file
java -cp build/libs/plantuml-*.jar net.sourceforge.plantuml.stats.DiagramStatsExtractor sample.puml
```

Test against your manually validated set of 100 diagrams (from section 6.5 of methodology) to compare accuracy against existing regex-based counts.

### Step 7: Batch processing integration

Two options for processing 162k files:

**Option A — Shell loop (simple)**
```bash
for f in /path/to/puml/files/*.puml; do
    java -cp plantuml.jar net.sourceforge.plantuml.stats.DiagramStatsExtractor "$f"
done >> results.jsonl
```
Slow due to JVM startup per file (~0.5s each = ~22 hours for 162k files).

**Option B — Batch mode in Java (recommended)**
Modify `DiagramStatsExtractor.main()` to accept a directory or file list, process all diagrams in a single JVM process. This avoids JVM startup overhead and should process 162k files in minutes.

### Step 8: Validate and compare

- Run on full dataset
- Compare element counts against your existing regex-based counts (expect high agreement on elements, since you already have 90%+ accuracy)
- Compare connection counts — expect significant improvements on:
  - Beta-syntax activity diagrams (from 0% coverage to ~100%)
  - Edge cases in arrow patterns across all types
- Re-run manual validation on the 100-sample set

## Output Format

Each diagram produces one JSON line (JSONL format):

```json
{
  "file": "abc123.puml",
  "diagram_type": "class",
  "elements": {
    "class": 5,
    "interface": 2,
    "enum": 1,
    "package": 2
  },
  "connections": {
    "total": 12,
    "by_type": {
      "EXTENDS": 3,
      "COMPOSITION": 2,
      "AGREGATION": 1,
      "NONE": 6
    }
  },
  "error": null
}
```

## What This Approach Does NOT Cover

- **Diagrams that fail PlantUML compilation** (44,803 files / 22%): fall back to existing regex parsers for these
- **Timing diagrams** (286 files): specialized internal model, needs separate investigation — low priority given tiny count
- **Unclassified diagrams** (12,616 files): may or may not parse; PlantUML will try all factories and either succeed or return `PSystemError`

## Key Source Files Reference

| File | Purpose |
|---|---|
| `net.sourceforge.plantuml.SourceStringReader` | API entry point — string to parsed diagram |
| `net.sourceforge.plantuml.BlockUml` | Single diagram block, call `.getDiagram()` |
| `net.atmp.CucaDiagram` | Base for entity+link diagrams: `.leafs()`, `.groups()`, `.getLinks()` |
| `net.sourceforge.plantuml.abel.Entity` | Structural element with `.getLeafType()` |
| `net.sourceforge.plantuml.abel.LeafType` | Enum: CLASS, INTERFACE, ENUM, COMPONENT, STATE... (51 types) |
| `net.sourceforge.plantuml.abel.Link` | Connection: `.getEntity1()`, `.getEntity2()`, `.getType()` |
| `net.sourceforge.plantuml.decoration.LinkDecor` | Enum: EXTENDS, COMPOSITION, AGREGATION, CROWFOOT... |
| `net.sourceforge.plantuml.sequencediagram.SequenceDiagram` | `.participants()`, `.events()` |
| `net.sourceforge.plantuml.sequencediagram.Message` | `.getParticipant1()`, `.getParticipant2()` |
| `net.sourceforge.plantuml.activitydiagram3.ActivityDiagram3` | Root of instruction tree |
| `net.sourceforge.plantuml.activitydiagram3.InstructionList` | Sequential container |
| `net.sourceforge.plantuml.activitydiagram3.InstructionIf` | If/else branching |
| `net.sourceforge.plantuml.activitydiagram3.InstructionWhile` | While loop |
| `net.sourceforge.plantuml.activitydiagram3.InstructionFork` | Parallel fork/join |

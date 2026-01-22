#!/usr/bin/env python3
"""
PlantUML Element Counter - counts unique elements in diagrams.

Single self-contained script with global deduplication.
Implicit elements are typed based on the diagram's primary_type.

Usage:
    python3 count_elements.py --classifications <json> --puml-dir <dir> --output <json>

Example:
    python3 count_elements.py \
        --classifications ../classify/1k_sample_diagram_classifications.json \
        --puml-dir ../1k_puml_sample \
        --output element_counts.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Any, List, Optional

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Import shared preprocessing utilities
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent))
from common.preprocessing import preprocess_content, strip_member_bodies


# =============================================================================
# CONSTANTS
# =============================================================================

VERSION = "2.4.0"

# All element types and their explicit declaration keywords
ELEMENT_TYPES = {
    # Class diagram elements
    'class': ['class'],
    'abstract class': ['abstract class', 'abstract'],
    'interface': ['interface'],
    'enum': ['enum'],
    'annotation': ['annotation'],
    'struct': ['struct'],
    'protocol': ['protocol'],
    'exception': ['exception'],
    'metaclass': ['metaclass'],
    'object': ['object'],
    'json': ['json'],
    'map': ['map'],

    # Sequence diagram elements
    'participant': ['participant'],
    'actor': ['actor'],
    'boundary': ['boundary'],
    'control': ['control'],
    'entity': ['entity'],
    'database': ['database'],
    'collections': ['collections'],
    'queue': ['queue'],

    # Usecase elements
    'usecase': ['usecase'],

    # State diagram elements
    'state': ['state'],

    # Containers (shared across diagram types)
    'package': ['package'],
    'namespace': ['namespace'],
    'node': ['node'],
    'folder': ['folder'],
    'frame': ['frame'],
    'cloud': ['cloud'],
    'component': ['component'],
    'rectangle': ['rectangle'],

    # Special
    'circle': ['circle'],
    'diamond': ['diamond'],

    # Deployment diagram elements
    'action': ['action'],
    'agent': ['agent'],
    'artifact': ['artifact'],
    'file': ['file'],
    'hexagon': ['hexagon'],
    'label': ['label'],
    'person': ['person'],
    'process': ['process'],
    'stack': ['stack'],
    'storage': ['storage'],

    # Additional containers
    'box': ['box'],
    'partition': ['partition'],
    'card': ['card'],
    'group': ['group'],
}

# Build keyword to element type mapping
KEYWORD_TO_TYPE: Dict[str, str] = {}
for _elem_type, _keywords in ELEMENT_TYPES.items():
    for _keyword in _keywords:
        KEYWORD_TO_TYPE[_keyword] = _elem_type

# All keywords for regex (sorted by length descending to match longer first)
ALL_KEYWORDS = sorted(KEYWORD_TO_TYPE.keys(), key=len, reverse=True)

# Default implicit element type by primary diagram type
# Supported UML diagram types for element counting
SUPPORTED_DIAGRAM_TYPES = {
    'class', 'sequence', 'usecase', 'component',
    'activity', 'object', 'deployment', 'state', 'timing'
}

# Note: activity diagrams use partition/group containers, not a specific element type
IMPLICIT_DEFAULTS = {
    'sequence': 'participant',
    'class': 'class',
    'usecase': 'actor',
    'component': 'component',
    'deployment': 'node',
    'state': 'state',
    'activity': 'partition',
    'object': 'object',
    'timing': 'participant',
}

# Keywords to ignore when detecting implicit elements
IGNORE_KEYWORDS = {
    'hide', 'show', 'remove', 'skinparam', 'title', 'footer', 'header',
    'legend', 'note', 'url', 'left', 'right', 'top', 'bottom', 'of',
    'start', 'stop', 'end', 'if', 'else', 'endif', 'together',
    'abstract', 'static', 'as', 'extends', 'implements',
    'loop', 'alt', 'opt', 'par', 'break', 'critical',
    'ref', 'activate', 'deactivate', 'create', 'destroy',
    'return', 'newpage', 'autonumber',
}

# Keywords that are control flow in sequence diagrams but elements elsewhere
# group is a structural container in Deployment/Activity but control flow in Sequence
SEQUENCE_CONTROL_FLOW = {
    'group', 'alt', 'opt', 'par', 'break', 'critical', 'loop', 'ref',
}

# Pattern to detect cardinality markers like "1", "*", "0..*", "1..*"
CARDINALITY_PATTERN = re.compile(r'^[\d*]+(?:\.\.[\d*]+)?$')


# =============================================================================
# PREPROCESSING - uses shared module from common.preprocessing
# =============================================================================


# =============================================================================
# ELEMENT DETECTION
# =============================================================================

def extract_explicit(
    content: str,
    elements: Dict[str, Set[str]],
    declared_names: Set[str],
    alias_map: Dict[str, str],
    primary_type: str = 'class'
) -> None:
    """Extract all explicitly declared elements in a single pass.

    Args:
        content: PlantUML content to parse
        elements: Dict to store found elements by type
        declared_names: Set of already declared names (for deduplication)
        alias_map: Dict mapping aliases to canonical names
        primary_type: Primary diagram type (affects contextual element handling)
    """
    keywords_pattern = '|'.join(re.escape(kw) for kw in ALL_KEYWORDS)

    pattern = rf'''
        ^\s*                                    # line start
        [+\-#~]?                               # optional visibility modifier
        ({keywords_pattern})                   # keyword (group 1)
        \s+                                    # required whitespace
        (?:
            "([^"]+)"                          # quoted name (group 2)
            |
            ([\w.$]+(?:<[^>]+>)?)              # unquoted name with dots/unicode (group 3)
        )
        (?:\s*<<[^>]*>>)?                      # optional stereotype
        (?:\s*\#[a-zA-Z0-9]+)?                 # optional color
        (?:\s+as\s+(?:"([^"]+)"|([\w.$]+)))?  # alias with dots/unicode (groups 4, 5)
    '''

    for match in re.finditer(pattern, content, re.MULTILINE | re.VERBOSE | re.IGNORECASE):
        keyword_raw = match.group(1).lower()
        quoted_name = match.group(2)
        unquoted_name = match.group(3)
        alias_quoted = match.group(4)
        alias_unquoted = match.group(5)

        keyword = keyword_raw.strip()
        if 'abstract' in keyword and 'class' in keyword:
            keyword = 'abstract class'

        # Skip 'group' in sequence diagrams (it's control flow, not a structural element)
        if keyword == 'group' and primary_type == 'sequence':
            continue

        elem_type = KEYWORD_TO_TYPE.get(keyword)
        if not elem_type:
            continue

        canonical_name = quoted_name if quoted_name else unquoted_name
        if not canonical_name:
            continue

        canonical_name = canonical_name.strip()
        name_lower = canonical_name.lower()

        if name_lower in declared_names:
            continue

        elements[elem_type].add(canonical_name)
        declared_names.add(name_lower)

        name_no_generics = re.sub(r'<[^>]+>', '', canonical_name).lower()
        if name_no_generics != name_lower:
            declared_names.add(name_no_generics)

        alias = alias_quoted if alias_quoted else alias_unquoted
        if alias:
            alias = alias.strip()
            alias_lower = alias.lower()
            alias_map[alias_lower] = canonical_name
            declared_names.add(alias_lower)


def extract_bracket_components(
    content: str,
    elements: Dict[str, Set[str]],
    declared_names: Set[str],
    alias_map: Dict[str, str]
) -> None:
    """Extract component elements declared with bracket notation [Name].

    PlantUML shorthand: [Foo] is equivalent to component "Foo"

    Patterns matched:
    - [ComponentName]
    - [ComponentName] as Alias
    - [Component Name] (quoted via brackets)

    Note: Skips state diagram markers like [*], [H], [H*]
    """
    # Pattern: [Name] with optional stereotype and alias
    # Must be at line start (not a bracket label in arrow like A --> B : [label])
    bracket_pattern = r'''
        ^\s*                                    # line start
        \[                                      # opening bracket
        ([^\]]+)                               # component name (group 1)
        \]                                      # closing bracket
        (?:\s*<<[^>]*>>)?                      # optional stereotype
        (?:\s*\#[a-zA-Z0-9]+)?                 # optional color
        (?:\s+as\s+(?:"([^"]+)"|([\w.$]+)))?  # alias with dots/unicode (groups 2, 3)
    '''

    for match in re.finditer(bracket_pattern, content, re.MULTILINE | re.VERBOSE):
        name = match.group(1).strip()
        alias_quoted = match.group(2)
        alias_unquoted = match.group(3)

        if not name:
            continue

        # Skip state diagram markers: [*], [H], [H*]
        if name in ('*', 'H', 'H*'):
            continue

        name_lower = name.lower()

        # Always register alias even if name already declared (for deduplication)
        alias = alias_quoted if alias_quoted else alias_unquoted
        if alias:
            alias = alias.strip()
            alias_lower = alias.lower()
            if alias_lower not in declared_names:
                alias_map[alias_lower] = name
                declared_names.add(alias_lower)

        # Only add element if not already declared
        if name_lower in declared_names:
            continue

        elements['component'].add(name)
        declared_names.add(name_lower)


def extract_interface_notation(
    content: str,
    elements: Dict[str, Set[str]],
    declared_names: Set[str],
    alias_map: Dict[str, str]
) -> None:
    """Extract interface elements declared with parenthesis notation.

    PlantUML shorthand patterns:
    - () "InterfaceName" - lollipop with quoted name
    - () InterfaceName - lollipop with unquoted name
    - ()InterfaceName - lollipop attached to name

    Note: Does NOT match (*) activity markers.
    """
    # Pattern: () followed by name - lollipop interface notation
    # Matches: () "Name", () Name, ()Name
    lollipop_pattern = r'''
        ^\s*                                    # line start
        \(\s*\)                                # empty parentheses ()
        \s*                                    # optional whitespace
        (?:
            "([^"]+)"                          # quoted name (group 1)
            |
            ([\w.$]+)                          # unquoted name with dots/unicode (group 2)
        )
        (?:\s*<<[^>]*>>)?                      # optional stereotype
        (?:\s+as\s+(?:"([^"]+)"|([\w.$]+)))?  # alias with dots/unicode (groups 3, 4)
    '''

    def add_interface(name: Optional[str], alias_quoted: Optional[str],
                      alias_unquoted: Optional[str]) -> None:
        if not name:
            return
        name = name.strip()
        if not name or name == '*':  # Skip activity markers
            return
        name_lower = name.lower()
        if name_lower in declared_names:
            return

        elements['interface'].add(name)
        declared_names.add(name_lower)

        alias = alias_quoted if alias_quoted else alias_unquoted
        if alias:
            alias = alias.strip()
            alias_lower = alias.lower()
            alias_map[alias_lower] = name
            declared_names.add(alias_lower)

    # Extract lollipop notation: () Name, ()"Name", ()Name
    for match in re.finditer(lollipop_pattern, content, re.MULTILINE | re.VERBOSE):
        name = match.group(1) if match.group(1) else match.group(2)
        add_interface(name, match.group(3), match.group(4))


def extract_usecase_parentheses(
    content: str,
    elements: Dict[str, Set[str]],
    declared_names: Set[str],
    alias_map: Dict[str, str]
) -> None:
    """Extract usecase elements with (Name) parenthesis syntax.

    PlantUML shorthand patterns:
    - (UseCase Name) - standalone usecase
    - (UseCase Name) as (Alias) - usecase with alias
    - "Display Name" as (Identifier) - quoted name with parenthesized alias

    Note: Does NOT match (*) activity markers or () interface notation.
    """
    # Pattern 1: (UseCase Name) with optional alias
    # Must not match (*) or empty ()
    usecase_pattern = r'''
        (?:^|[\s\n])                           # line start or whitespace
        \(                                     # opening paren
        ([^()*\n][^)\n]*?)                     # usecase name - not starting with * or (
        \)                                     # closing paren
        (?:\s+as\s+\(([^)]+)\))?               # optional alias in parens
        (?:\s+as\s+([\w.$]+))?                 # or plain alias with dots/unicode
    '''

    for match in re.finditer(usecase_pattern, content, re.MULTILINE | re.VERBOSE):
        name = match.group(1)
        if name:
            name = name.strip()
        alias_paren = match.group(2)
        alias_plain = match.group(3)

        if not name:
            continue

        name_lower = name.lower()
        if name_lower in declared_names:
            continue

        elements['usecase'].add(name)
        declared_names.add(name_lower)

        # Handle aliases
        alias = alias_paren if alias_paren else alias_plain
        if alias:
            alias = alias.strip()
            alias_lower = alias.lower()
            alias_map[alias_lower] = name
            declared_names.add(alias_lower)

    # Pattern 2: "Quoted Name" as (Identifier) - common in usecase diagrams
    quoted_alias_pattern = r'''
        "([^"]+)"                              # quoted name
        \s+as\s+
        \(([^)]+)\)                            # parenthesized identifier
    '''

    for match in re.finditer(quoted_alias_pattern, content, re.MULTILINE | re.VERBOSE):
        name = match.group(1).strip()
        alias = match.group(2).strip()

        if not name or not alias:
            continue

        name_lower = name.lower()
        alias_lower = alias.lower()

        if name_lower not in declared_names:
            elements['usecase'].add(name)
            declared_names.add(name_lower)

        if alias_lower not in declared_names:
            alias_map[alias_lower] = name
            declared_names.add(alias_lower)


def extract_creole_actor(
    content: str,
    elements: Dict[str, Set[str]],
    declared_names: Set[str],
    alias_map: Dict[str, str]
) -> None:
    """Extract actor elements with :Name: creole syntax.

    PlantUML patterns:
    - :Actor Name: - standalone actor
    - :Actor Name: as identifier - actor with alias

    Note: Does NOT match:
    - Sequence message labels (A -> B : message) - colon after arrow
    - Activity actions (:action;) - ends with semicolon
    """
    # Pattern: :Name: with optional alias
    # Must not be followed by semicolon (activity) or preceded by arrow (sequence)
    actor_pattern = r'''
        (?:^|(?<![->.]))                       # not preceded by arrow chars
        \s*
        :([^:\n;]+):                           # :name: - no colons, newlines, or semicolons inside
        (?!\s*;)                               # not followed by semicolon (activity syntax)
        (?:\s+as\s+([\w.$]+))?                 # optional alias with dots/unicode
    '''

    for match in re.finditer(actor_pattern, content, re.MULTILINE | re.VERBOSE):
        name = match.group(1)
        if name:
            name = name.strip()
        alias = match.group(2)

        if not name:
            continue

        name_lower = name.lower()
        if name_lower in declared_names:
            continue

        elements['actor'].add(name)
        declared_names.add(name_lower)

        if alias:
            alias = alias.strip()
            alias_lower = alias.lower()
            alias_map[alias_lower] = name
            declared_names.add(alias_lower)


def is_cardinality(name: str) -> bool:
    """Check if a string is a cardinality marker like '1', '*', '0..*', '1..*'."""
    return bool(CARDINALITY_PATTERN.match(name.strip()))


def get_name_from_groups(quoted: Optional[str], unquoted: Optional[str]) -> Optional[str]:
    """Return quoted name if present, otherwise unquoted."""
    if quoted:
        return quoted.strip()
    if unquoted:
        return unquoted.strip()
    return None


def extract_implicit(
    content: str,
    elements: Dict[str, Set[str]],
    declared_names: Set[str],
    alias_map: Dict[str, str],
    implicit_type: str,
    primary_type: str = 'class'
) -> None:
    """Extract implicit elements from relationship usage."""
    # Main relationship pattern - covers class, component, deployment, etc.
    # Supports both quoted and unquoted element names
    # Note: Cardinality markers like "1", "*" are filtered by is_cardinality()
    # Note: (*) is activity diagram start/end marker, matched but filtered out
    # Structure: LEFT [CARDINALITY] ARROW [LABEL/CARDINALITY] RIGHT
    relation_pattern = r'''
        (?:^|\s)                               # line start or whitespace
        (?:
            "([^"]+)"                          # quoted left element (group 1)
            |
            ([\w.$]+)                          # unquoted left element with dots/unicode (group 2)
            |
            \(([^()*\n][^)\n]*)\)              # parenthesized usecase left (group 3)
            |
            \(\*\)                             # activity start/end marker (not captured)
        )
        (?:[ \t]*"[^"\n]*")?                   # optional cardinality after left (same line)
        [ \t]*
        (
            # Async/special sequence (most specific first)
            ->>|<<-                            # async message
            |
            ->x|x<-                            # lost/found message
            |
            <->                                # bidirectional
            |
            # Inheritance/realization with direction
            (?:<\|)?[-.](?:up|down|left|right|u|d|l|r)?[-.][-.]?(?:\|>|>)?
            |
            (?:<)?[-.][-.]+(?:\|>|>)?
            |
            # Composition/aggregation/deployment endpoints
            [*o#x+^0][-.][-.]+ | [-.][-.]+[*o#x+^0]
            |
            # Dotted dependency
            \.\.+>|<\.\.+
            |
            # Simple arrows (single dash - common in sequence)
            <-+|-+>
        )
        [ \t]*
        (?:"[^"\n]*"[ \t]*)?                   # optional cardinality after arrow (same line)
        (?:\[[^\]\n]*\][ \t]*)?                # optional bracket label [ OK ] (same line)
        (?:
            "([^"]+)"                          # quoted right element (group 5)
            |
            ([\w.$]+)                          # unquoted right element with dots/unicode (group 6)
            |
            \(([^()*\n][^)\n]*)\)              # parenthesized usecase right (group 7)
            |
            \(\*\)                             # activity start/end marker (not captured)
        )
    '''

    # Sequence diagram message pattern: Alice -> Bob : message
    # Supports both quoted and unquoted participant names
    sequence_msg_pattern = r'''
        ^\s*                                   # line start
        (?:
            "([^"]+)"                          # quoted left participant (group 1)
            |
            ([\w.$]+)                          # unquoted left participant with dots/unicode (group 2)
        )
        \s*
        (<?-+>>?|<?\.+>?)                      # arrow (group 3)
        \s*
        (?:
            "([^"]+)"                          # quoted right participant (group 4)
            |
            ([\w.$]+)                          # unquoted right participant with dots/unicode (group 5)
        )
        \s*:\s*                                # colon separator (sequence msg label)
    '''

    def add_implicit_element(name: Optional[str]) -> None:
        """Helper to add an implicit element if valid."""
        if not name:
            return
        name = name.strip()
        if not name:
            return
        # Skip cardinality markers like "1", "*", "0..*", "1..*"
        if is_cardinality(name):
            return
        name_lower = name.lower()
        if name_lower in IGNORE_KEYWORDS:
            return
        if name_lower in declared_names:
            return
        if name_lower in alias_map:
            return
        if name_lower in KEYWORD_TO_TYPE:
            return
        elements[implicit_type].add(name)
        declared_names.add(name_lower)

    def add_bracket_component(name: Optional[str]) -> None:
        """Helper to add a bracket notation component if valid."""
        if not name:
            return
        name = name.strip()
        if not name:
            return
        # Skip state diagram markers: [*], [H], [H*]
        if name in ('*', 'H', 'H*'):
            return
        name_lower = name.lower()
        if name_lower in declared_names:
            return
        if name_lower in alias_map:
            return
        elements['component'].add(name)
        declared_names.add(name_lower)

    # Pass 1: Main relationship pattern (all diagram types)
    for match in re.finditer(relation_pattern, content, re.VERBOSE):
        # Left side: groups 1 (quoted), 2 (unquoted), 3 (parenthesized)
        left_name = match.group(1) or match.group(2) or match.group(3)
        # Right side: groups 5 (quoted), 6 (unquoted), 7 (parenthesized)
        right_name = match.group(5) or match.group(6) or match.group(7)
        if left_name:
            add_implicit_element(left_name.strip())
        if right_name:
            add_implicit_element(right_name.strip())

    # Pass 1b: Bracket notation in relationships: [A] --> [B]
    bracket_relation_pattern = r'\[([^\]]+)\]\s*(?:--?>|<--?|\.\.>|<\.\.|\*--|--\*|o--|--o)'
    for match in re.finditer(bracket_relation_pattern, content):
        add_bracket_component(match.group(1))
    # Also check for right side brackets after arrows
    bracket_right_pattern = r'(?:--?>|<--?|\.\.>|<\.\.|\*--|--\*|o--|--o)\s*\[([^\]]+)\]'
    for match in re.finditer(bracket_right_pattern, content):
        add_bracket_component(match.group(1))

    # Pass 2: Sequence message pattern (sequence diagrams only)
    if primary_type == 'sequence':
        for match in re.finditer(sequence_msg_pattern, content, re.VERBOSE | re.MULTILINE):
            left_name = get_name_from_groups(match.group(1), match.group(2))
            right_name = get_name_from_groups(match.group(4), match.group(5))
            add_implicit_element(left_name)
            add_implicit_element(right_name)


def count_elements(content: str, primary_type: str = 'class') -> Dict[str, int]:
    """
    Count all unique elements in PlantUML content.

    Args:
        content: Preprocessed PlantUML content
        primary_type: Primary diagram type (determines implicit element typing)

    Returns:
        Dict mapping element type to count (empty dict for unsupported types)
    """
    # Skip unsupported diagram types
    if primary_type not in SUPPORTED_DIAGRAM_TYPES:
        return {}

    elements: Dict[str, Set[str]] = {t: set() for t in ELEMENT_TYPES}
    declared_names: Set[str] = set()
    alias_map: Dict[str, str] = {}

    extract_explicit(content, elements, declared_names, alias_map, primary_type)

    # Extract shorthand notation elements (bracket components and interface lollipops)
    extract_bracket_components(content, elements, declared_names, alias_map)
    extract_interface_notation(content, elements, declared_names, alias_map)

    # Extract usecase shorthand patterns
    # (UseCase) syntax - usecase diagrams only
    if primary_type == 'usecase':
        extract_usecase_parentheses(content, elements, declared_names, alias_map)

    # :Actor: syntax - usecase and sequence diagrams (both use actors)
    # Use stripped content to avoid false matches on method signatures like id:string
    if primary_type in ('usecase', 'sequence'):
        content_without_bodies = strip_member_bodies(content)
        extract_creole_actor(content_without_bodies, elements, declared_names, alias_map)

    implicit_type = IMPLICIT_DEFAULTS.get(primary_type, 'class')
    extract_implicit(content, elements, declared_names, alias_map, implicit_type, primary_type)

    return {t: len(names) for t, names in elements.items() if names}


# =============================================================================
# FILE PROCESSING
# =============================================================================

def load_classifications(path: Path) -> Dict[str, Any]:
    """Load classification JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_puml_file(path: Path) -> Optional[str]:
    """Read a PlantUML file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}", file=sys.stderr)
        return None


def process_file(
    content: str,
    primary_type: str,
    diagram_types: List[str],
) -> Dict[str, Any]:
    """Process a single PlantUML file and count elements."""
    clean_content = preprocess_content(content)
    all_elements = count_elements(clean_content, primary_type)

    return {
        "primary_type": primary_type,
        "diagram_types": diagram_types,
        "elements": all_elements,
        "total_elements": sum(all_elements.values())
    }


def aggregate_statistics(
    results: Dict[str, Dict],
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, Any]:
    """Generate aggregate statistics from results."""
    total_files = len(results)
    with_elements = sum(1 for r in results.values() if r["total_elements"] > 0)
    elements_total = sum(r["total_elements"] for r in results.values())

    by_element_type: Dict[str, int] = {}
    for result in results.values():
        for elem_type, count in result["elements"].items():
            by_element_type[elem_type] = by_element_type.get(elem_type, 0) + count

    by_element_type = dict(sorted(by_element_type.items(), key=lambda x: -x[1]))

    duration = end_time - start_time
    processing_time = str(duration).split('.')[0]

    return {
        "total_files": total_files,
        "processed": total_files,
        "with_elements": with_elements,
        "elements_total": elements_total,
        "by_element_type": by_element_type,
        "processing_time": processing_time,
    }


def process_directory(
    classifications_path: Path,
    puml_dir: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """Process all files from classification JSON."""
    start_time = datetime.now()

    print(f"Loading classifications from {classifications_path}...")
    data = load_classifications(classifications_path)
    classifications = data.get("classifications", {})

    print(f"Using unified element counter v{VERSION}")

    results: Dict[str, Dict] = {}
    files_to_process = list(classifications.items())

    print(f"Processing {len(files_to_process)} files...")

    if HAS_TQDM:
        iterator = tqdm(files_to_process, desc="Counting elements")
    else:
        iterator = files_to_process

    for filename, classification in iterator:
        filepath = puml_dir / filename

        if not filepath.exists():
            results[filename] = {
                "primary_type": "",
                "confidence": None,
                "diagram_types": [],
                "elements": {},
                "total_elements": 0,
                "note": "file not found"
            }
            continue

        content = read_puml_file(filepath)
        if content is None:
            results[filename] = {
                "primary_type": "",
                "confidence": None,
                "diagram_types": [],
                "elements": {},
                "total_elements": 0,
                "note": "read error"
            }
            continue

        primary_type = classification.get("primary_type", "class")
        confidence = classification.get("confidence")
        diagram_types = list(classification.get("types", {}).keys())
        if not diagram_types:
            diagram_types = [primary_type]

        result = process_file(content, primary_type, diagram_types)
        result["confidence"] = confidence
        results[filename] = result

    end_time = datetime.now()

    statistics = aggregate_statistics(results, start_time, end_time)

    output = {
        "metadata": {
            "version": VERSION,
            "timestamp": datetime.now().isoformat(),
            "classifications_file": str(classifications_path),
            "puml_directory": str(puml_dir),
            "note": "Unified element counter with global deduplication"
        },
        "statistics": statistics,
        "results": results
    }

    print(f"Writing results to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n=== Summary ===")
    print(f"Total files: {statistics['total_files']}")
    print(f"Files with elements: {statistics['with_elements']}")
    print(f"Total elements: {statistics['elements_total']}")
    print(f"Processing time: {statistics['processing_time']}")
    print("\nElements by type:")
    for elem_type, count in statistics['by_element_type'].items():
        print(f"  {elem_type}: {count}")

    return output


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Count unique elements in PlantUML diagrams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--classifications", "-c",
        type=Path,
        required=True,
        help="Path to classification JSON file"
    )

    parser.add_argument(
        "--puml-dir", "-d",
        type=Path,
        required=True,
        help="Directory containing .puml files"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("element_counts.json"),
        help="Output JSON file path (default: element_counts.json)"
    )

    args = parser.parse_args()

    if not args.classifications.exists():
        print(f"Error: Classification file not found: {args.classifications}", file=sys.stderr)
        sys.exit(1)

    if not args.puml_dir.exists():
        print(f"Error: PUML directory not found: {args.puml_dir}", file=sys.stderr)
        sys.exit(1)

    process_directory(
        args.classifications,
        args.puml_dir,
        args.output,
    )


if __name__ == "__main__":
    main()

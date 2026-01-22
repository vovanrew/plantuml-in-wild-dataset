#!/usr/bin/env python3
"""
Script to classify PlantUML diagrams into UML diagram types.

This script analyzes PlantUML files and classifies them using rule-based
feature extraction and confidence scoring. Supports multi-label classification.

Usage:
    python3 classify_diagrams.py <puml_directory> [options]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Script version
VERSION = "1.0.0"

# Try to import tqdm for progress bar, fallback if not available
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Import shared preprocessing utilities
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent))
from common.preprocessing import preprocess_content, strip_member_bodies, strip_footer_header


def strip_comments(content: str) -> str:
    """
    Remove PlantUML comments to avoid false keyword detection.

    Handles:
    - Single-line comments: ' or ''
    - Multi-line comments: /' ... '/
    - Inline comments: code ' comment (preserves ' in strings)

    Args:
        content: Raw PlantUML content

    Returns:
        Content with comments removed, newlines preserved
    """
    # Remove multi-line comments: /' ... '/
    content = re.sub(r"/'.*?'/", "", content, flags=re.DOTALL)

    # Remove single-line comments: ' or '' at start of line
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove anything after ' at start or after whitespace
        if re.match(r"^\s*'+", line):
            # Entire line is a comment
            cleaned_lines.append('')
        else:
            # Remove inline comments (preserve strings)
            cleaned_lines.append(remove_inline_comment(line))

    return '\n'.join(cleaned_lines)


def remove_inline_comment(line: str) -> str:
    """
    Remove inline PlantUML comment from a single line.

    PlantUML comment rules:
    - ' starts a comment only if preceded by whitespace or at line start
    - Apostrophes inside double-quoted strings are preserved
    - Apostrophes in middle of words (Alice's) are NOT comments

    Args:
        line: Single line of PlantUML code

    Returns:
        Line with comment removed
    """
    result = []
    in_string = False
    i = 0

    while i < len(line):
        char = line[i]

        # Toggle string state on double-quote
        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1

        # Check for comment marker
        elif char == "'" and not in_string:
            # Comment rules: ' starts a comment if:
            # 1. At start of line (already handled by regex)
            # 2. Preceded by whitespace AND followed by space/tab (typical comment)
            # 3. Preceded by whitespace AND at end of line
            # Otherwise, preserve it (could be 'text' or Alice's)

            if i == 0:
                # At start of line (but this should be caught by regex already)
                break
            elif result and result[-1] in (' ', '\t'):
                # Preceded by whitespace - check what follows
                if i + 1 >= len(line):
                    # At end of line after whitespace → comment
                    while result and result[-1] in (' ', '\t'):
                        result.pop()
                    break
                elif line[i + 1] in (' ', '\t'):
                    # Followed by space/tab → comment
                    while result and result[-1] in (' ', '\t'):
                        result.pop()
                    break
                else:
                    # Preceded by space but not followed by space ('text' pattern)
                    result.append(char)
                    i += 1
            else:
                # In middle of word (e.g., "Alice's") → NOT a comment
                result.append(char)
                i += 1

        # Normal character
        else:
            result.append(char)
            i += 1

    return ''.join(result)


def strip_styling_blocks(content: str) -> str:
    """
    Remove styling and configuration blocks to avoid false keyword detection.

    Removes:
    - skinparam blocks: skinparam Type { ... }
    - hide/show directives: hide class members, show footbox
    - style blocks: style Type { ... }

    Args:
        content: PlantUML content with comments already removed

    Returns:
        Content with styling blocks removed
    """
    # Remove skinparam blocks: skinparam Type { ... }
    content = re.sub(
        r'skinparam\s+\w+\s*\{[^}]*\}',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove hide/show directives (single line)
    # Examples: hide footbox, hide class members, show component interface
    content = re.sub(
        r'^\s*(hide|show)\s+.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
    )

    # Remove style blocks: style Type { ... }
    content = re.sub(
        r'style\s+\w+\s*\{[^}]*\}',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    return content


def strip_sprite_blocks(content: str) -> str:
    """
    Remove sprite definitions to avoid false keyword detection.

    Handles two sprite formats:
    - Hex/raster: sprite $name [WxH/depth] { hex_data }
    - SVG inline: sprite $name <svg>...</svg>

    Args:
        content: PlantUML content

    Returns:
        Content with sprite blocks removed
    """
    # Remove hex/raster sprite blocks: sprite $name [dimensions] { ... }
    # Name pattern allows hyphens, underscores, and alphanumerics (e.g., $backbone-icon)
    content = re.sub(
        r'sprite\s+\$?[\w-]+\s*\[[^\]]+\]\s*\{[^}]*\}',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove SVG inline sprites: sprite $name <svg>...</svg>
    content = re.sub(
        r'sprite\s+\$?[\w-]+\s*<svg[^>]*>.*?</svg>',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    return content


def detect_diagram_type(content: str) -> str:
    """
    Detect if diagram is non-UML type (graphviz, ditaa, salt, gantt).

    Args:
        content: PlantUML file content

    Returns:
        'uml' | 'graphviz' | 'ditaa' | 'salt' | 'gantt'
    """
    content_lower = content.lower()

    if '@startdot' in content_lower:
        return 'graphviz'
    elif '@startditaa' in content_lower:
        return 'ditaa'
    elif '@startsalt' in content_lower:
        return 'salt'
    elif '@startgantt' in content_lower:
        return 'gantt'
    else:
        return 'uml'


def extract_features(clean_content: str) -> Dict[str, Any]:
    """
    Extract features from PlantUML content for classification.

    Args:
        clean_content: Content with comments stripped

    Returns:
        Dictionary of feature flags and counts
    """
    content_lower = clean_content.lower()
    lines = clean_content.split('\n')

    # Additional preprocessing for specific feature detection
    # Strip footer/header/title for usecase patterns (URLs, tool credits)
    content_for_usecase = strip_footer_header(clean_content)
    content_for_usecase = strip_member_bodies(content_for_usecase)

    # Strip member bodies for sequence lifecycle detection (bold markdown in class bodies)
    content_for_lifecycle = strip_member_bodies(clean_content)

    features = {
        # Sequence diagram features
        'has_participant': bool(re.search(r'\bparticipant\b', content_lower)),
        'has_actor': bool(re.search(r'\bactor\b', content_lower)),
        'has_activate': bool(re.search(r'\bactivate\b', content_lower)),
        # Use stripped content to avoid matching field names like "- alt : int"
        'has_alt_loop': bool(re.search(r'\b(alt|loop|opt|par)\b', strip_member_bodies(content_lower))),
        'arrow_with_participant': False,  # Calculated below

        # Enhanced sequence diagram features
        'has_lost_message': bool(re.search(r'--?>x', clean_content)),
        'has_return_arrow': bool(re.search(r'<--?', clean_content)),
        'has_activation_shortcut': bool(re.search(r'(?:^|\s)(?:\+\+|--)(?:\s*$)', clean_content, re.MULTILINE)),
        # Require ** after whitespace/arrow, not inside words (avoids **bold** markdown)
        'has_lifecycle_create': bool(re.search(r'(?:^|[\s>-])\*\*(?=\s|$)', content_for_lifecycle, re.MULTILINE)),
        'has_lifecycle_destroy': bool(re.search(r'!!', clean_content)),
        'has_else': bool(re.search(r'\belse\b', content_lower)),
        'has_group': bool(re.search(r'\bgroup\b', content_lower)),
        'has_end': bool(re.search(r'\bend\b', content_lower)),
        'has_ref_over': bool(re.search(r'\bref\s+over\b', content_lower)),
        'has_delay': bool(re.search(r'\.{3}', clean_content)),
        'has_autonumber': bool(re.search(r'\bautonumber\b', content_lower)),
        'has_divider': bool(re.search(r'={3,}', clean_content)),
        # Sequence message arrow pattern: Name->Name : message (require 1-2 dashes, not 3+)
        # Supports unquoted names, quoted names ("Name"), and creole names (:Name:)
        'has_sequence_message': bool(re.search(r'(?:\w+|"[^"]+"|:[^:]+:)\s*-{1,2}>\s*(?:\w+|"[^"]+"|:[^:]+:)\s*:', clean_content)),

        # Class diagram features
        # Match both 'class Name' and 'class "Name"' with quotes
        'has_class': bool(re.search(r'\bclass\s+["\']?\w', content_lower)),
        'has_interface': bool(re.search(r'\binterface\b', content_lower)),
        'has_enum': bool(re.search(r'\benum\b', content_lower)),
        # Match 'abstract class/interface' or standalone 'abstract "Name"'
        'has_abstract': bool(re.search(r'\babstract\s+(?:class|interface|["\']?\w)', content_lower)),
        'has_inheritance': bool(re.search(r'(<\|--|--\|>)', clean_content)),
        'has_composition': bool(re.search(r'\*--', clean_content)),
        'has_aggregation': bool(re.search(r'o--', clean_content)),
        'has_realization': bool(re.search(r'(<\|\.\.|\.\.\|>)', clean_content)),
        'has_member_visibility': bool(re.search(r'^\s*[+\-#~]\s*\w', clean_content, re.MULTILINE)),
        'has_lollipop_interface': bool(re.search(r'\(\s*\)\s*--\s*\(\s*\)', clean_content)),
        'has_association_class': bool(re.search(r'\([^)]+,\s*[^)]+\)\s*\.\.', clean_content)),
        'has_hide_empty_members': bool(re.search(r'\bhide\s+empty\s+members\b', content_lower)),

        # Activity diagram features - OLD SYNTAX (legacy)
        'has_old_activity_syntax': bool(re.search(r'\(\s*\*\s*\)', clean_content)),  # (*) marker
        'has_sync_bar': bool(re.search(r'===\s*\w+\s*===', clean_content)),  # === sync bar ===

        # Activity diagram features - NEW SYNTAX (beta) - HIGHLY DISTINCTIVE
        'has_new_action_syntax': bool(re.search(r':\s*[^:\n]+\s*;', clean_content)),  # :action;
        'has_switch_case': bool(re.search(r'\b(switch|case|endswitch)\b', content_lower)),  # UNIQUE
        'has_backward': bool(re.search(r'\bbackward\b', content_lower)),  # UNIQUE
        'has_kill': bool(re.search(r'\bkill\b', content_lower)),  # UNIQUE
        'has_detach': bool(re.search(r'\bdetach\b', content_lower)),  # UNIQUE
        'has_elseif': bool(re.search(r'\belseif\b', content_lower)),  # Activity-specific
        'has_repeat_while': bool(re.search(r'\b(repeat|repeat\s+while)\b', content_lower)),
        'has_swimlane': bool(re.search(r'\|[^|\n]+\|', clean_content)),  # |Swimlane Name|
        'has_fork_again': bool(re.search(r'\bfork\s+again\b', content_lower)),  # NEW syntax specific
        'has_end_fork': bool(re.search(r'\bend\s+(fork|merge)\b', content_lower)),  # NEW syntax specific
        'has_split': bool(re.search(r'\b(split|split\s+again|end\s+split)\b', content_lower)),  # NEW syntax

        # Activity diagram features - SHARED (both old and new)
        'has_start_stop': bool(re.search(r'\b(start|stop)\b', content_lower)),
        'has_end': bool(re.search(r'\bend\b', content_lower)),  # Separated from start/stop
        'has_fork_join': bool(re.search(r'\b(fork|join)\b', content_lower)),
        'has_partition': bool(re.search(r'\bpartition\b', content_lower)),
        'has_if_then_else': bool(re.search(r'\b(if|then|else|endif)\b', content_lower)),
        'has_while': bool(re.search(r'\b(while|endwhile)\b', content_lower)),

        # Activity composite features (calculated below)
        'has_activity_loop': False,
        'has_new_syntax_markers': False,
        'has_unique_activity_keywords': False,

        # State diagram features
        'has_state_keyword': bool(re.search(r'\bstate\s+\w', content_lower)),
        'has_state_markers': bool(re.search(r'\[\*\]', clean_content)),
        'has_state_transition': False,  # Calculated below

        # History states (HIGHLY DISTINCTIVE - UNIQUE to state diagrams)
        'has_history_shallow': bool(re.search(r'\[H\]', clean_content)),
        'has_history_deep': bool(re.search(r'\[H\*\]', clean_content)),

        # Composite/nested states
        'has_composite_state': bool(re.search(r'\bstate\s+\w+\s*\{', content_lower)),
        'has_state_description': bool(re.search(r'\bstate\s+\w+\s*:\s*[^\n]+', content_lower)),

        # Concurrency stereotypes (state-specific)
        'has_fork_stereotype': bool(re.search(r'<<\s*fork\s*>>', content_lower)),
        'has_join_stereotype': bool(re.search(r'<<\s*join\s*>>', content_lower)),

        # Pseudo-states (state-specific)
        'has_choice_pseudo': bool(re.search(r'<<\s*choice\s*>>', content_lower)),
        'has_entrypoint_pseudo': bool(re.search(r'<<\s*entrypoint\s*>>', content_lower)),
        'has_exitpoint_pseudo': bool(re.search(r'<<\s*exitpoint\s*>>', content_lower)),

        # Transition patterns
        'has_transition_label': bool(re.search(r'-+>\s*:\s*\w+', clean_content)),
        'has_concurrency_separator': bool(re.search(r'(^|\n)\s*--\s*($|\n)', clean_content)),

        # Nesting detection (calculated below)
        'has_nested_states': False,

        # Use case diagram features
        'has_usecase': bool(re.search(r'\busecase\b', content_lower)),
        # Exclude URLs (https://, ftp://), type annotations (:), paths (/), stereotype spots (,)
        'has_usecase_parentheses': bool(re.search(r'\((?!https?://|ftp://)[^):/*,]+\)\s*(?:as\s+\w+)?(?:\s|$)', content_for_usecase)),
        # Require standalone :Name: not adjacent to ( or ) - avoids type annotations
        'has_actor_colons': bool(re.search(r'(?<![(\w]):\w[^:()\n*]+:(?![)\w])', content_for_usecase)),
        'has_rectangle': bool(re.search(r'\brectangle\b', content_lower)),
        'has_extend_include': bool(re.search(r'<<\s*(extend|include)\s*>>', content_lower)),
        'has_dotted_arrow': bool(re.search(r'\.\.[|>]', clean_content)),
        'has_usecase_arrows': bool(re.search(r'(<--(?!\|)|--->)', clean_content)),
        'actor_with_usecase': False,  # Calculated below

        # Component diagram features
        # Require 'component' as PlantUML keyword (not inside stereotypes like <<work-product-component>>)
        'has_component': bool(re.search(r'(?<![-<\w])\bcomponent\s+["\']?\w', content_lower)),
        'has_package': bool(re.search(r'\bpackage\b', content_lower)),
        'has_node': bool(re.search(r'\bnode\b', content_lower)),
        'has_bracket_notation': bool(re.search(r'\[[^\]]+\]', clean_content)),

        # Component diagram features - Port keywords (HIGHLY DISTINCTIVE)
        'has_port': bool(re.search(r'\bport\b', content_lower)),
        'has_portin': bool(re.search(r'\bportin\b', content_lower)),
        'has_portout': bool(re.search(r'\bportout\b', content_lower)),

        # Component diagram features - Component style configuration
        'has_component_style': bool(re.search(r'\bskinparam\s+componentstyle\b', content_lower)),

        # Component diagram features - Interface notation
        'has_interface_symbol': bool(re.search(r'\(\s*\)', clean_content)),
        'has_interface_connection': bool(re.search(r'\(\s*\w*\s*\)\s*[-\.]+', clean_content)),
        'has_named_interface': bool(re.search(r'\w+\s*\(\s*\)', clean_content)),

        # Component diagram features - Additional grouping keywords
        'has_database': bool(re.search(r'\bdatabase\b', content_lower)),
        'has_folder': bool(re.search(r'\bfolder\b', content_lower)),
        'has_cloud': bool(re.search(r'\bcloud\b', content_lower)),
        'has_frame': bool(re.search(r'\bframe\b', content_lower)),

        # Component diagram features - Dependency relationships
        'has_dotted_dependency': bool(re.search(r'\.{2,}>', clean_content)),

        # Component diagram features - Composite features (calculated later)
        'has_node_without_artifact': False,
        'has_component_with_bracket': False,
        'has_component_grouping': False,
        'has_interface_without_members': False,

        # Deployment diagram features
        'has_artifact': bool(re.search(r'\bartifact\b', content_lower)),
        'has_deployment': bool(re.search(r'\bdeployment\b', content_lower)),
        'has_stereotypes': bool(re.search(r'<<[^>]+>>', clean_content)),
        'has_deployment_stereotype': bool(re.search(
            r'<<\s*(device|execution\s*environment|processor|node)\s*>>',
            content_lower
        )),

        # Deployment diagram features - Infrastructure nodes (HIGH distinctiveness)
        'has_device': bool(re.search(r'\bdevice\b', content_lower)),
        'has_storage': bool(re.search(r'\bstorage\b', content_lower)),
        'has_server': bool(re.search(r'\bserver\b', content_lower)),
        'has_container': bool(re.search(r'\bcontainer\b', content_lower)),

        # Deployment diagram features - Deployable elements
        'has_file': bool(re.search(r'\bfile\b', content_lower)),
        'has_process': bool(re.search(r'\bprocess\b', content_lower)),
        'has_card': bool(re.search(r'\bcard\b', content_lower)),

        # Deployment diagram features - Nesting syntax
        'has_node_nesting': bool(re.search(r'\bnode\s+["\w][^{]*\{', content_lower)),
        'has_cloud_nesting': bool(re.search(r'\bcloud\s+["\w][^{]*\{', content_lower)),
        'has_database_nesting': bool(re.search(r'\bdatabase\s+["\w][^{]*\{', content_lower)),
        'has_storage_nesting': bool(re.search(r'\bstorage\s+["\w][^{]*\{', content_lower)),
        'has_device_nesting': bool(re.search(r'\bdevice\s+["\w][^{]*\{', content_lower)),

        # Deployment diagram features - Specialized arrows
        'has_deployment_arrows': bool(re.search(r'--[\*o+#\^0]', clean_content)),

        # Deployment diagram features - Composite (calculated below)
        'has_infrastructure_nodes': False,  # device/storage/server/cloud/database
        'has_physical_deployment': False,   # artifact + (node OR cloud)
        'has_deployment_nesting': False,    # Nesting within infrastructure nodes
        'has_containerization': False,      # container + (artifact OR node)

        # Object diagram features
        # Use stripped content to avoid matching "Object" in class field declarations like "Object bean"
        'has_object': bool(re.search(r'^\s*object\s+["\']?\w', strip_member_bodies(clean_content), re.MULTILINE | re.IGNORECASE)),
        # Instance notation: exclude lines with visibility modifiers (class fields)
        'has_instance_notation': bool(re.search(r'(?:^|\n)\s*(?![-+#~])\w+\s*:\s*\w+\s*(?:$|\n)', clean_content)),

        # Map data structures (UNIQUE to object diagrams)
        # Require line start to avoid matching "Map" in Java generics like "Map<String,T>"
        'has_map_keyword': bool(re.search(r'^\s*map\s+["\']?\w', strip_member_bodies(clean_content), re.MULTILINE | re.IGNORECASE)),
        'has_map_separator': bool(re.search(r'=>', clean_content)),

        # Object structure features
        'has_object_block': bool(re.search(r'^\s*object\s+[^{]+\{', strip_member_bodies(clean_content), re.MULTILINE | re.IGNORECASE)),
        'has_diamond_shape': bool(re.search(r'\bdiamond\b', content_lower)),

        # Field assignments (concrete values)
        'has_field_assignment': bool(re.search(r'\w+\s*=\s*["\']?\w+', clean_content)),

        # Composite features (calculated below)
        'has_object_with_relationships': False,
        'has_map_with_separator': False,

        # Timing diagram features - Participant types (HIGHLY DISTINCTIVE)
        'has_robust_participant': bool(re.search(r'\brobust\b', content_lower)),
        'has_concise_participant': bool(re.search(r'\bconcise\b', content_lower)),
        'has_binary_participant': bool(re.search(r'\bbinary\b', content_lower)),
        'has_clock_participant': bool(re.search(r'\bclock\b', content_lower)),
        'has_analog_participant': bool(re.search(r'\banalog\b', content_lower)),

        # Time notation system (HIGHLY DISTINCTIVE)
        'has_at_time_notation': bool(re.search(r'@\d+|@\+\d+|@:', clean_content)),

        # State pre-definition (UNIQUE to timing diagrams)
        'has_has_keyword': bool(re.search(r'\bhas\b', content_lower)),

        # Time constraints (HIGHLY DISTINCTIVE)
        'has_time_constraint_arrow': bool(re.search(r'<->', clean_content)),

        # Time axis control (UNIQUE)
        'has_hide_time_axis': bool(re.search(r'\bhide\s+time-axis\b', content_lower)),

        # State assignment with 'is' keyword (context-dependent)
        'has_is_state_assignment': bool(re.search(r'\bis\s+\w+', content_lower)),

        # Clock parameters (timing-specific)
        'has_clock_parameters': bool(re.search(r'\bwith\s+period\b|\bpulse\b|\boffset\b', content_lower)),

        # Time range highlighting
        'has_highlight_command': bool(re.search(r'\bhighlight\b', content_lower)),

        # Time anchors (timing-specific pattern)
        'has_time_anchor': bool(re.search(r'@\d+\s+as\s+:', content_lower)),

        # Scale command (also in Gantt, but common in timing)
        'has_scale_command': bool(re.search(r'\bscale\b', content_lower)),

        # Composite features (calculated below in function)
        'has_timing_participant_types': False,  # Any timing participant type
        'has_at_with_is_pattern': False,       # @ notation + is keyword
        'has_timing_time_system': False,        # @ notation + time anchors/constraints

        # Count metrics
        'arrow_count': len(re.findall(r'-+>', clean_content)),
        'line_count': len([line for line in lines if line.strip()]),
        'total_keywords': 0  # Calculated below
    }

    # Calculate composite features
    # arrow_with_participant: arrows near participant declarations
    if features['has_participant'] and features['arrow_count'] > 0:
        features['arrow_with_participant'] = True

    # state_transition: state keyword with arrows
    if features['has_state_keyword'] and features['arrow_count'] > 0:
        features['has_state_transition'] = True

    # has_nested_states: Detect brace nesting depth >= 2
    # Check for state definitions with nested braces: state { ... state { ... } }
    nested_pattern = r'state\s+\w+\s*\{[^}]*state\s+\w+\s*\{'
    if re.search(nested_pattern, content_lower):
        features['has_nested_states'] = True

    # actor_with_usecase: actor + usecase markers or distinctive notations
    if (features['has_actor'] or features['has_actor_colons']) and \
       (features['has_usecase'] or features['has_usecase_parentheses']):
        features['actor_with_usecase'] = True

    # Calculate activity diagram composite features
    # has_activity_loop: any loop structure (repeat OR while)
    if features['has_repeat_while'] or features['has_while']:
        features['has_activity_loop'] = True

    # has_new_syntax_markers: any new syntax-specific feature
    if any([
        features['has_new_action_syntax'],
        features['has_fork_again'],
        features['has_end_fork'],
        features['has_split'],
        features['has_elseif'],
        features['has_backward']
    ]):
        features['has_new_syntax_markers'] = True

    # has_unique_activity_keywords: keywords ONLY found in activity diagrams
    if any([
        features['has_switch_case'],
        features['has_backward'],
        features['has_kill'],
        features['has_detach']
    ]):
        features['has_unique_activity_keywords'] = True

    # Calculate deployment diagram composite features
    # has_infrastructure_nodes: any physical hardware keyword
    if any([
        features['has_device'],
        features['has_storage'],
        features['has_server'],
        features['has_cloud'],
        features['has_database']
    ]):
        features['has_infrastructure_nodes'] = True

    # has_physical_deployment: artifact deployed to node or cloud
    if features['has_artifact'] and (features['has_node'] or features['has_cloud']):
        features['has_physical_deployment'] = True

    # has_deployment_nesting: nesting within infrastructure nodes
    if any([
        features['has_node_nesting'],
        features['has_cloud_nesting'],
        features['has_database_nesting'],
        features['has_storage_nesting'],
        features['has_device_nesting']
    ]):
        features['has_deployment_nesting'] = True

    # has_containerization: container with artifact/node (C4 deployment)
    if features['has_container'] and (features['has_artifact'] or features['has_node']):
        features['has_containerization'] = True

    # Calculate component diagram composite features
    # has_node_without_artifact: node without artifact favors Component over Deployment
    if features['has_node'] and not features['has_artifact']:
        features['has_node_without_artifact'] = True

    # has_component_with_bracket: both component keyword and bracket notation present
    if features['has_component'] and features['has_bracket_notation']:
        features['has_component_with_bracket'] = True

    # has_component_grouping: component with grouping keywords (organized architecture)
    if features['has_component'] and (features['has_package'] or
                                      features['has_database'] or
                                      features['has_folder']):
        features['has_component_grouping'] = True

    # has_interface_without_members: interface without member visibility favors Component over Class
    if features['has_interface'] and not features['has_member_visibility']:
        features['has_interface_without_members'] = True

    # Calculate object diagram composite features
    # has_object_with_relationships: object/map with relationship arrows
    if (features['has_object'] or features['has_map_keyword']) and features['arrow_count'] > 0:
        features['has_object_with_relationships'] = True

    # has_map_with_separator: both map keyword and => separator
    if features['has_map_keyword'] and features['has_map_separator']:
        features['has_map_with_separator'] = True

    # Calculate timing diagram composite features
    # has_timing_participant_types: any specialized timing participant
    if any([
        features['has_robust_participant'],
        features['has_concise_participant'],
        features['has_binary_participant'],
        features['has_clock_participant'],
        features['has_analog_participant']
    ]):
        features['has_timing_participant_types'] = True

    # has_at_with_is_pattern: @ time notation combined with is state assignment
    if features['has_at_time_notation'] and features['has_is_state_assignment']:
        features['has_at_with_is_pattern'] = True

    # has_timing_time_system: comprehensive time notation system usage
    if features['has_at_time_notation'] and \
       (features['has_time_anchor'] or features['has_time_constraint_arrow']):
        features['has_timing_time_system'] = True

    # Count total keywords
    features['total_keywords'] = sum(
        1 for key, value in features.items()
        if key.startswith('has_') and value is True
    )

    return features


# Hierarchical Feature Tier System
# Features organized by importance tier with base weights
FEATURE_TIERS = {
    'sequence': {
        'tier1': {
            # HIGHLY DISTINCTIVE - unique or nearly unique to sequence
            'has_sequence_message': 2.0,  # Name->Name : message pattern
            'has_lost_message': 2.0,
            'has_alt_loop': 2.0,
            'has_activation_shortcut': 1.8,
            'has_ref_over': 1.8,
            'arrow_with_participant': 1.8,
            'has_activate': 1.5,
            'has_lifecycle_create': 1.5,
            'has_lifecycle_destroy': 1.5,
        },
        'tier2': {
            # STRONG FEATURES
            'has_participant': 2.0,
            'has_autonumber': 1.5,
            'has_return_arrow': 1.5,
            'has_group': 1.2,
        },
        'tier3': {
            # MODERATE/WEAK
            'has_else': 0.8,
            'has_end': 0.5,
            'has_divider': 0.5,
            'has_delay': 0.6,
        },
        'tier4': {
            'has_actor': 0.4,
        }
    },
    'activity': {
        'tier1': {
            # UNIQUE KEYWORDS - only in activity diagrams
            'has_backward': 2.0,
            'has_kill': 1.8,
            'has_detach': 1.8,
            'has_switch_case': 2.0,
            'has_new_action_syntax': 1.8,
            'has_old_activity_syntax': 1.5,
            'has_swimlane': 1.3,
            'has_sync_bar': 1.2,
        },
        'tier2': {
            # STRONG ACTIVITY FEATURES
            'has_fork_again': 2.8,
            'has_end_fork': 2.8,
            'has_split': 2.5,
            'has_partition': 2.2,
            'has_start_stop': 2.0,
            'has_fork_join': 1.8,
            'has_activity_loop': 1.5,
        },
        'tier3': {
            # MODERATE FEATURES
            'has_elseif': 1.0,
            'has_if_then_else': 0.8,
            'has_while': 0.8,
            'has_end': 0.5,
        },
        'tier4': {}
    },
    'class': {
        'tier1': {
            'has_member_visibility': 2.0,
            'has_realization': 1.8,
            'has_inheritance': 1.5,
            'has_class': 1.4,
            'has_abstract': 1.2,
        },
        'tier2': {
            'has_composition': 1.2,
            'has_aggregation': 1.2,
            'has_enum': 1.0,
            'has_association_class': 1.5,
            'has_lollipop_interface': 1.0,
        },
        'tier3': {
            'has_interface': 0.5,
            'has_hide_empty_members': 0.8,
        },
        'tier4': {}
    },
    'component': {
        'tier1': {
            'has_portin': 2.0,
            'has_portout': 2.0,
            'has_port': 1.8,
            'has_component_style': 1.5,
            'has_component': 1.3,
        },
        'tier2': {
            'has_interface_connection': 2.8,
            'has_component_with_bracket': 2.5,
            'has_component_grouping': 2.2,
            'has_package': 2.0,
            'has_bracket_notation': 1.8,
            'has_interface_without_members': 1.5,
        },
        'tier3': {
            'has_interface': 0.5,
            'has_dotted_dependency': 1.2,
            'has_interface_symbol': 1.0,
            'has_database': 0.8,
            'has_folder': 0.8,
            'has_cloud': 0.8,
        },
        'tier4': {
            'has_node': 0.4,
        }
    },
    'deployment': {
        'tier1': {
            'has_physical_deployment': 2.0,
            'has_artifact': 1.8,
            'has_deployment': 1.5,
            'has_device': 1.4,
            'has_storage': 1.4,
            'has_deployment_stereotype': 1.3,
        },
        'tier2': {
            'has_deployment_nesting': 2.8,
            'has_containerization': 2.5,
            'has_infrastructure_nodes': 2.2,
            'has_server': 2.0,
            'has_node_nesting': 1.8,
            'has_cloud_nesting': 1.8,
        },
        'tier3': {
            'has_file': 1.2,
            'has_process': 1.2,
            'has_card': 1.0,
            'has_database': 1.0,
            'has_cloud': 1.2,
        },
        'tier4': {
            'has_node': 0.5,
            'has_stereotypes': 0.5,
        }
    },
    'state': {
        'tier1': {
            # UNIQUE/DECISIVE - if present, almost certainly state diagram
            'has_history_shallow': 2.0,
            'has_history_deep': 2.0,
            'has_choice_pseudo': 1.8,
            'has_fork_stereotype': 1.8,
            'has_join_stereotype': 1.8,
            'has_entrypoint_pseudo': 1.5,
            'has_exitpoint_pseudo': 1.5,
            'has_composite_state': 1.5,
        },
        'tier2': {
            # STRONG - very common in state diagrams, reasonably distinctive
            'has_state_keyword': 2.0,
            'has_state_markers': 2.0,
            'has_state_transition': 1.8,
            'has_nested_states': 1.5,
        },
        'tier3': {
            # MODERATE - supportive but less distinctive
            'has_transition_label': 1.2,
            'has_state_description': 1.2,
            'has_concurrency_separator': 1.0,
        },
        'tier4': {}
    },
    'usecase': {
        'tier1': {
            'has_extend_include': 2.0,
            'has_actor_colons': 1.8,
            'has_usecase_parentheses': 1.6,
            'has_usecase': 1.4,
            'actor_with_usecase': 1.3,
        },
        'tier2': {
            'has_dotted_arrow': 1.0,
            'has_rectangle': 1.0,
            'has_package': 0.8,
        },
        'tier3': {
            'has_actor': 1.2,
            'has_usecase_arrows': 0.5,
        },
        'tier4': {}
    },
    'object': {
        'tier1': {
            'has_map_keyword': 1.8,
            'has_map_separator': 1.6,
            'has_object': 1.4,
            'has_object_block': 1.3,
            'has_map_with_separator': 1.2,
        },
        'tier2': {
            'has_field_assignment': 1.0,
            'has_diamond_shape': 0.8,
            'has_object_with_relationships': 0.8,
        },
        'tier3': {
            'has_instance_notation': 1.0,
        },
        'tier4': {}
    },
    'timing': {
        'tier1': {
            'has_robust_participant': 2.0,
            'has_concise_participant': 2.0,
            'has_binary_participant': 2.0,
            'has_clock_participant': 1.8,
            'has_at_time_notation': 1.5,
            'has_has_keyword': 1.4,
            'has_hide_time_axis': 1.3,
        },
        'tier2': {
            'has_time_constraint_arrow': 2.5,
            'has_clock_parameters': 2.2,
            'has_at_with_is_pattern': 2.0,
            'has_highlight_command': 1.8,
            'has_timing_time_system': 1.5,
        },
        'tier3': {
            'has_time_anchor': 1.5,
            'has_is_state_assignment': 1.0,
            'has_scale_command': 1.2,
        },
        'tier4': {}
    },
}

# Context-aware adjustment rules for ambiguous features
CONTEXT_RULES = {
    'has_interface': {
        'class': lambda f: 2.8 if (f.get('has_class') or f.get('has_member_visibility')) else 0.5,
        'component': lambda f: 2.8 if (f.get('has_component') or f.get('has_interface_symbol')) else 0.5,
    },
    'has_node': {
        'deployment': lambda f: 2.0 if f.get('has_artifact') else 0.5,
        'component': lambda f: 1.8 if not f.get('has_artifact') else 0.3,
    },
    'has_cloud': {
        'deployment': lambda f: 1.2 if f.get('has_artifact') else 0.5,
        'component': lambda f: 0.8 if not f.get('has_artifact') else 0.3,
    },
    'has_database': {
        'deployment': lambda f: 1.0 if f.get('has_infrastructure_nodes') else 0.5,
        'component': lambda f: 0.8 if f.get('has_component') else 0.5,
    },
    'has_actor': {
        'usecase': lambda f: 1.2 if (f.get('has_usecase') or f.get('has_usecase_parentheses')) else 0.4,
        'sequence': lambda f: 1.0 if f.get('arrow_count', 0) > 5 else 0.4,
    },
}

# Hierarchical penalties for conflicting Tier 1/2 features
HIERARCHICAL_PENALTIES = {
    'sequence': [
        ('has_unique_activity_keywords', 0.3),
        ('has_new_action_syntax', 0.4),
        ('has_swimlane', 0.7),
    ],
    'activity': [
        ('arrow_with_participant', 0.5),
        ('has_activate', 0.6),
    ],
    'class': [
        ('has_portin', 0.5),
        ('has_portout', 0.5),
        ('has_component', 0.7),
    ],
    'component': [
        ('has_member_visibility', 0.6),
        ('has_physical_deployment', 0.6),
        ('has_artifact', 0.75),
        ('has_class', 0.5),       # 50% penalty when class keyword present
        ('has_abstract', 0.6),    # 40% penalty when abstract present
        ('has_node_nesting', 0.4),      # 60% penalty when nodes contain other nodes (deployment)
        ('has_deployment_nesting', 0.5),  # 50% penalty when deployment nesting detected
    ],
    'deployment': [
        ('has_portin', 0.7),
        ('has_portout', 0.7),
        ('has_component_style', 0.8),
    ],
    'state': [],
    'usecase': [
        ('has_activate', 0.3),           # 70% penalty - activate is sequence-only
        ('has_autonumber', 0.3),         # 70% penalty - autonumber is sequence-only
        ('has_sequence_message', 0.2),   # 80% penalty - "A -> B : msg" pattern
        ('has_alt_loop', 0.4),           # 60% penalty - alt/loop/opt/par
    ],
    'object': [],
    'timing': [
        ('has_participant', 0.8),
        ('has_activate', 0.85),
    ],
}


def apply_hierarchical_penalties(score: float, features: Dict[str, Any], dtype: str) -> float:
    """
    Apply penalties when conflicting Tier 1/2 features from other diagram types are detected.

    Args:
        score: Current score for diagram type
        features: Extracted features dictionary
        dtype: Diagram type being scored

    Returns:
        Penalized score
    """
    penalties = HIERARCHICAL_PENALTIES.get(dtype, [])
    for feature, penalty_factor in penalties:
        if features.get(feature, False):
            score *= penalty_factor
    return score


def calculate_scores(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate hierarchical weighted scores for each UML diagram type.

    Uses 4-tier system with exponential multipliers:
    - Tier 1 (Decisive): 100x multiplier
    - Tier 2 (Strong): 10x multiplier
    - Tier 3 (Moderate): 1x multiplier
    - Tier 4 (Weak): 0.1x multiplier

    Args:
        features: Extracted features dictionary

    Returns:
        Dictionary mapping diagram type to raw score
    """
    TIER_MULTIPLIERS = {
        'tier1': 100.0,
        'tier2': 10.0,
        'tier3': 1.0,
        'tier4': 0.1,
    }

    scores = {}

    # Process all diagram types with hierarchical scoring
    for dtype in ['sequence', 'class', 'activity', 'state', 'usecase',
                  'component', 'deployment', 'object', 'timing']:
        score = 0.0

        # Process each tier with exponential multipliers
        for tier_name, multiplier in TIER_MULTIPLIERS.items():
            tier_features = FEATURE_TIERS[dtype].get(tier_name, {})

            for feature, base_weight in tier_features.items():
                if not features.get(feature, False):
                    continue

                # Apply context-aware adjustment if needed
                adjusted_weight = base_weight
                if feature in CONTEXT_RULES and dtype in CONTEXT_RULES[feature]:
                    context_multiplier = CONTEXT_RULES[feature][dtype](features)
                    adjusted_weight = context_multiplier

                score += adjusted_weight * multiplier

        # Apply hierarchical penalties for conflicting features
        score = apply_hierarchical_penalties(score, features, dtype)

        scores[dtype] = score

    return scores


def classify_diagram(puml_content: str, threshold: float = 0.3, include_features: bool = False) -> Dict:
    """
    Classify PlantUML diagram into UML types with confidence scores.

    Args:
        puml_content: Raw PlantUML file content
        threshold: Minimum confidence for multi-label classification
        include_features: Include feature details in output

    Returns:
        Classification result dictionary
    """
    # Step 1: Detect non-UML types
    diagram_type = detect_diagram_type(puml_content)

    if diagram_type != 'uml':
        # Non-UML diagram
        result = {
            'diagram_type': diagram_type,
            'primary_type': None,
            'types': {},
            'confidence': None
        }
        if include_features:
            result['features'] = {}
        return result

    # Step 2: Preprocess content (strip comments, styling, sprites, notes)
    clean_content = preprocess_content(puml_content)

    # Step 3: Extract features
    features = extract_features(clean_content)

    # Step 4: Calculate scores
    raw_scores = calculate_scores(features)

    # Step 5: Normalize scores (sum to 1.0)
    total_score = sum(raw_scores.values())

    if total_score == 0:
        # No features detected - return unclassified
        result = {
            'diagram_type': 'uml',
            'primary_type': 'unclassified',
            'types': {},
            'confidence': 0.0
        }
        if include_features:
            result['features'] = features
        return result

    normalized_scores = {
        dtype: score / total_score
        for dtype, score in raw_scores.items()
    }

    # Step 6: Filter types with confidence >= threshold
    filtered_types = {
        dtype: conf
        for dtype, conf in normalized_scores.items()
        if conf >= threshold
    }

    # Step 7: Determine primary type (highest confidence)
    primary_type = max(normalized_scores, key=normalized_scores.get)
    primary_confidence = normalized_scores[primary_type]

    result = {
        'diagram_type': 'uml',
        'primary_type': primary_type,
        'types': filtered_types,
        'confidence': round(primary_confidence, 4)
    }

    if include_features:
        result['features'] = features

    return result


def generate_statistics(results: Dict, start_time: datetime, end_time: datetime) -> Dict:
    """
    Generate statistics from classification results.

    Args:
        results: Dictionary of classification results
        start_time: Processing start time
        end_time: Processing end time

    Returns:
        Statistics dictionary
    """
    total_files = len(results)
    failed = sum(1 for r in results.values() if r is None)
    successful = total_files - failed

    # Diagram type distribution
    diagram_type_dist = {}
    for result in results.values():
        if result is None:
            continue
        dtype = result['diagram_type']
        diagram_type_dist[dtype] = diagram_type_dist.get(dtype, 0) + 1

    # UML type distribution (primary classifications)
    uml_type_dist = {}
    for result in results.values():
        if result is None or result['diagram_type'] != 'uml':
            continue
        primary = result['primary_type']
        if primary:
            uml_type_dist[primary] = uml_type_dist.get(primary, 0) + 1

    # Multi-label count
    multi_label_count = sum(
        1 for result in results.values()
        if result and result['diagram_type'] == 'uml' and len(result['types']) > 1
    )

    # Average confidence (for UML diagrams only)
    uml_confidences = [
        result['confidence']
        for result in results.values()
        if result and result['diagram_type'] == 'uml' and result['confidence'] is not None
    ]
    avg_confidence = sum(uml_confidences) / len(uml_confidences) if uml_confidences else 0.0

    # Processing time
    duration = end_time - start_time
    processing_time = str(duration).split('.')[0]  # Remove microseconds

    return {
        'total_files': total_files,
        'successful': successful,
        'failed': failed,
        'diagram_type_distribution': diagram_type_dist,
        'uml_type_distribution': uml_type_dist,
        'multi_label_count': multi_label_count,
        'average_confidence': round(avg_confidence, 4),
        'processing_time': processing_time
    }


def process_directory(puml_dir: Path, output_file: Path, threshold: float, include_features: bool) -> Dict:
    """
    Process all PUML files in directory and generate classifications.

    Args:
        puml_dir: Directory containing .puml files
        output_file: Output JSON file path
        threshold: Multi-label classification threshold
        include_features: Include feature details in output

    Returns:
        Statistics dictionary
    """
    if not puml_dir.exists():
        print(f"Error: Directory '{puml_dir}' not found", file=sys.stderr)
        sys.exit(1)

    # Get all .puml files
    puml_files = list(puml_dir.glob("*.puml"))
    total_files = len(puml_files)

    print(f"Found {total_files:,} .puml files", file=sys.stderr)
    print("Processing...", file=sys.stderr)

    # Initialize results
    classifications = {}
    start_time = datetime.now()

    # Process files with progress bar
    if HAS_TQDM:
        iterator = tqdm(puml_files, desc="Classifying", unit="file")
    else:
        iterator = puml_files

    for idx, puml_file in enumerate(iterator, 1):
        try:
            # Read file content
            with open(puml_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Classify
            result = classify_diagram(content, threshold, include_features)
            classifications[puml_file.name] = result

        except Exception as e:
            print(f"Error processing {puml_file.name}: {e}", file=sys.stderr)
            classifications[puml_file.name] = None

        # Progress update (if no tqdm)
        if not HAS_TQDM and idx % 1000 == 0:
            percentage = (idx / total_files) * 100
            print(f"Processed {idx:,}/{total_files:,} ({percentage:.1f}%)", file=sys.stderr)

    end_time = datetime.now()

    # Generate statistics
    statistics = generate_statistics(classifications, start_time, end_time)

    # Prepare output
    output = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_files': total_files,
            'threshold': threshold,
            'script_version': VERSION
        },
        'statistics': statistics,
        'classifications': classifications
    }

    # Write JSON output
    print(f"\nWriting output to {output_file}...", file=sys.stderr)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Done!", file=sys.stderr)
    return statistics


def main():
    parser = argparse.ArgumentParser(
        description="Classify PlantUML diagrams into UML diagram types.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 classify_diagrams.py ./puml_validated/valid
  python3 classify_diagrams.py ./puml -o results.json -t 0.2
  python3 classify_diagrams.py ./puml --include-features

Output:
  JSON file with rich format including all types with confidence scores
        """
    )

    parser.add_argument(
        "puml_directory",
        help="Directory containing .puml files"
    )

    parser.add_argument(
        "-o", "--output",
        default="diagram_classifications.json",
        help="Output JSON file (default: diagram_classifications.json)"
    )

    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.3,
        help="Multi-label classification threshold (default: 0.3)"
    )

    parser.add_argument(
        "--include-features",
        action="store_true",
        help="Include feature details in output (for debugging)"
    )

    args = parser.parse_args()

    # Convert to Path objects
    puml_dir = Path(args.puml_directory).resolve()
    output_file = Path(args.output).resolve()

    print("=" * 60, file=sys.stderr)
    print("PlantUML Diagram Classification", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Input directory: {puml_dir}", file=sys.stderr)
    print(f"Output file: {output_file}", file=sys.stderr)
    print(f"Threshold: {args.threshold}", file=sys.stderr)
    print(f"Include features: {args.include_features}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Process directory
    statistics = process_directory(puml_dir, output_file, args.threshold, args.include_features)

    # Print summary
    print("\n" + "=" * 60, file=sys.stderr)
    print("Classification Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total files: {statistics['total_files']:,}", file=sys.stderr)
    print(f"Successful: {statistics['successful']:,}", file=sys.stderr)
    print(f"Failed: {statistics['failed']:,}", file=sys.stderr)
    print(f"\nDiagram Type Distribution:", file=sys.stderr)
    for dtype, count in sorted(statistics['diagram_type_distribution'].items()):
        percentage = (count / statistics['total_files']) * 100
        print(f"  {dtype}: {count:,} ({percentage:.2f}%)", file=sys.stderr)
    print(f"\nUML Type Distribution:", file=sys.stderr)
    for utype, count in sorted(statistics['uml_type_distribution'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / statistics['total_files']) * 100
        print(f"  {utype}: {count:,} ({percentage:.2f}%)", file=sys.stderr)
    print(f"\nMulti-label diagrams: {statistics['multi_label_count']:,}", file=sys.stderr)
    print(f"Average confidence: {statistics['average_confidence']:.4f}", file=sys.stderr)
    print(f"Processing time: {statistics['processing_time']}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()

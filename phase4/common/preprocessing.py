"""
Shared preprocessing utilities for PlantUML analysis scripts.

This module provides consistent content preprocessing across:
- classify_with_llm.py (diagram classification)
- count_elements.py (element counting)
- count_relationships.py (relationship counting)

All functions handle PlantUML-specific syntax for comments, styling,
sprites, and notes to avoid false positives in analysis.
"""

import re


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
                    # At end of line after whitespace -> comment
                    while result and result[-1] in (' ', '\t'):
                        result.pop()
                    break
                elif line[i + 1] in (' ', '\t'):
                    # Followed by space/tab -> comment
                    while result and result[-1] in (' ', '\t'):
                        result.pop()
                    break
                else:
                    # Preceded by space but not followed by space ('text' pattern)
                    result.append(char)
                    i += 1
            else:
                # In middle of word (e.g., "Alice's") -> NOT a comment
                result.append(char)
                i += 1

        # Normal character
        else:
            result.append(char)
            i += 1

    return ''.join(result)


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


def strip_styling_blocks(content: str) -> str:
    """
    Remove styling and configuration blocks to avoid false keyword detection.

    Removes:
    - skinparam blocks: skinparam Type { ... }
    - skinparam single-line: skinparam Type value
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

    # Remove skinparam single-line: skinparam Type value
    # Handles: skinparam Type value, skinparam Type<<stereotype>> value
    content = re.sub(
        r'^\s*skinparam\s+.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
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


def strip_preprocessor_directives(content: str) -> str:
    """
    Remove PlantUML preprocessor directives to avoid false keyword detection.

    These are meta-programming features for creating reusable components,
    not actual diagram content. Library files consisting only of these
    directives should not be classified as UML diagrams.

    Handles:
    - !define macro definitions
    - !include file inclusions
    - !procedure...!endprocedure blocks
    - !function...!endfunction blocks
    - !$variable assignments
    - !unquoted definitions

    Args:
        content: PlantUML content

    Returns:
        Content with preprocessor directives removed
    """
    # Remove !define lines (macro definitions)
    content = re.sub(
        r'^\s*!define\s+.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove !include lines (file inclusions)
    content = re.sub(
        r'^\s*!include\s+.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove !procedure...!endprocedure blocks
    content = re.sub(
        r'!procedure\b.*?!endprocedure',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove !function...!endfunction blocks
    content = re.sub(
        r'!function\b.*?!endfunction',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove !$variable assignments
    content = re.sub(
        r'^\s*!\$\w+\s*=.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    # Remove !unquoted definitions
    content = re.sub(
        r'^\s*!unquoted\s+.*$',
        '',
        content,
        flags=re.MULTILINE
    )

    return content


def strip_member_bodies(content: str) -> str:
    """
    Remove content inside class/interface/enum/struct body braces.

    Used to prevent false matches on method signatures when detecting
    actor patterns like :Name: creole syntax.

    Handles nested braces like {static} within class bodies by using
    brace depth counting instead of simple regex.

    Handles:
    - class Name { ... }
    - interface Name { ... }
    - enum Name { ... }
    - struct Name { ... }
    - abstract class Name { ... }

    Args:
        content: PlantUML content

    Returns:
        Content with member bodies replaced by empty braces
    """
    result = []
    i = 0
    class_pattern = re.compile(
        r'\b(?:abstract\s+)?(?:class|interface|enum|struct)\s+\S+',
        re.IGNORECASE
    )

    while i < len(content):
        match = class_pattern.match(content, i)
        if match:
            # Found class-like definition
            result.append(match.group())
            i = match.end()

            # Copy everything until opening brace (stereotypes, etc.)
            while i < len(content) and content[i] != '{':
                result.append(content[i])
                i += 1

            if i < len(content) and content[i] == '{':
                # Skip body content with proper brace depth tracking
                brace_depth = 1
                i += 1  # Skip opening brace

                while i < len(content) and brace_depth > 0:
                    if content[i] == '{':
                        brace_depth += 1
                    elif content[i] == '}':
                        brace_depth -= 1
                    i += 1

                result.append('{ }')  # Replace body with empty braces
        else:
            result.append(content[i])
            i += 1

    return ''.join(result)


def strip_notes(content: str) -> str:
    """
    Remove note blocks to avoid false keyword detection from note text.

    Handles:
    - Single-line notes: note left: text, note right of X: text
    - Multi-line notes: note left\\n...\\nend note
    - Floating notes: note "text" as N1

    IMPORTANT: Single-line notes are processed FIRST to prevent the
    multi-line regex from matching across unrelated note blocks.

    Args:
        content: PlantUML content

    Returns:
        Content with note blocks removed
    """
    # Step 1: Remove single-line notes FIRST (note ... : text on same line)
    # This prevents multi-line regex from incorrectly spanning across them
    content = re.sub(
        r'^\s*note\s+(?:left|right|top|bottom|over)(?:\s+of\s+\w+)?\s*:.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
    )

    # Step 2: Remove multi-line notes (note ... \n ... end note)
    # These start with note keyword followed by newline (no colon on same line)
    content = re.sub(
        r'\bnote\s+(?:left|right|top|bottom|over)?(?:\s+of\s+\w+)?\s*\n.*?\bend\s+note\b',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Step 3: Handle floating notes: note "text" as N1
    content = re.sub(
        r'^\s*note\s+"[^"]*"(?:\s+as\s+\w+)?.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
    )

    return content


def strip_footer_header(content: str) -> str:
    """
    Remove footer, header, title, legend, and caption blocks.

    These blocks often contain URLs, tool credits, and other text
    that can trigger false positive keyword detection.

    Handles:
    - Multi-line: header...endheader, footer...endfooter, legend...endlegend
    - Single-line: header/footer/title/caption with inline content
    - Positioned variants: left/right/center header/footer

    Args:
        content: PlantUML content

    Returns:
        Content with documentation blocks removed
    """
    # Remove multi-line header blocks
    content = re.sub(
        r'\b(left|right|center)?\s*header\b.*?\bendheader\b',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove multi-line footer blocks
    content = re.sub(
        r'\b(left|right|center)?\s*footer\b.*?\bendfooter\b',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove single-line header/footer
    content = re.sub(
        r'^\s*(left|right|center)?\s*(header|footer)\s+.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
    )

    # Remove title lines
    content = re.sub(
        r'^\s*title\s+.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
    )

    # Remove legend blocks
    content = re.sub(
        r'\blegend\b.*?\bendlegend\b',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )

    # Remove caption lines
    content = re.sub(
        r'^\s*caption\s+.*$',
        '',
        content,
        flags=re.MULTILINE | re.IGNORECASE
    )

    return content


def preprocess_content(content: str) -> str:
    """
    Full preprocessing pipeline for PlantUML content.

    Removes all non-structural content that could cause false positives:
    1. Comments (single-line, multi-line, inline)
    2. Styling blocks (skinparam, hide/show, style)
    3. Sprite definitions (hex/raster, SVG)
    4. Preprocessor directives (!define, !include, !procedure, !function)
    5. Note blocks (single-line, multi-line, floating)
    6. Footer/header/title/legend blocks (documentation, tool credits)

    Args:
        content: Raw PlantUML content

    Returns:
        Cleaned content ready for analysis
    """
    content = strip_comments(content)
    content = strip_styling_blocks(content)
    content = strip_sprite_blocks(content)
    content = strip_preprocessor_directives(content)
    content = strip_notes(content)
    content = strip_footer_header(content)
    return content

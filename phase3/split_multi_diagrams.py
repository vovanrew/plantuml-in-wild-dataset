#!/usr/bin/env python3
"""
Script to split PlantUML files containing multiple diagrams into separate files.
Each diagram (@startuml...@enduml block) will be saved to a new file with suffix _01, _02, etc.
Original files with multiple diagrams will be moved to phase3/many_pumls directory.
"""

import argparse
import os
import re
import shutil
from pathlib import Path


def extract_header_comments(lines):
    """
    Extract header comments from the beginning of the file.
    Stops at the first @start... tag (case-insensitive, with optional leading whitespace).
    """
    header = []
    start_pattern = re.compile(r'^\s*@start\w*', re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("'") or stripped == "":
            header.append(line)
        elif start_pattern.match(line):
            break
        else:
            # Non-comment, non-empty line before @start...
            break
    return header


def find_diagrams(content):
    """
    Find all @start...@end... blocks in the content.
    Handles case-insensitive tags, leading whitespace, typos, and all PlantUML diagram types.
    Examples: @startuml/@enduml, @startditaa/@endditaa, @startuml/@endum1, etc.
    """
    diagrams = []
    lines = content.splitlines(keepends=True)

    # Match @start followed by any word characters (catches all diagram types)
    start_pattern = re.compile(r'^\s*@start\w*', re.IGNORECASE)
    # Match @end followed by any word characters (catches typos like @endum, @endum1, etc.)
    end_pattern = re.compile(r'^\s*@end\w*', re.IGNORECASE)

    current_diagram = []
    in_diagram = False

    for line in lines:
        if start_pattern.match(line):
            in_diagram = True
            current_diagram = [line]
        elif end_pattern.match(line):
            if in_diagram:
                current_diagram.append(line)
                diagrams.append(''.join(current_diagram))
                current_diagram = []
                in_diagram = False
        elif in_diagram:
            current_diagram.append(line)

    return diagrams


def split_puml_file(file_path, output_dir, many_pumls_dir, dry_run=False):
    """
    Split a .puml file with multiple diagrams into separate files.

    Args:
        file_path: Path to the .puml file
        output_dir: Directory where split files will be created
        many_pumls_dir: Directory where original multi-diagram files will be moved
        dry_run: If True, only scan and report without making changes

    Returns:
        Number of diagrams found (0 if file has only 1 diagram or none)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    diagrams = find_diagrams(content)

    # Only process files with multiple diagrams
    if len(diagrams) <= 1:
        return 0

    if dry_run:
        # Just report what would happen
        base_name = Path(file_path).stem
        print(f"\n{file_path.name}:")
        print(f"  Would split into {len(diagrams)} diagrams:")
        for i in range(1, len(diagrams) + 1):
            new_filename = f"{base_name}_{i:02d}.puml"
            print(f"    - {new_filename}")
        print(f"  Would move original to: many_pumls/{file_path.name}")
        return len(diagrams)

    # Extract header comments
    lines = content.splitlines(keepends=True)
    header = extract_header_comments(lines)
    header_text = ''.join(header)

    # Get base filename without extension
    base_name = Path(file_path).stem

    # Create split files
    for i, diagram in enumerate(diagrams, 1):
        # Create new filename with suffix _01, _02, etc.
        new_filename = f"{base_name}_{i:02d}.puml"
        new_filepath = output_dir / new_filename

        # Write header + diagram to new file
        with open(new_filepath, 'w', encoding='utf-8') as f:
            f.write(header_text)
            if header_text and not header_text.endswith('\n'):
                f.write('\n')
            f.write(diagram)

        print(f"  Created: {new_filename}")

    # Move original file to many_pumls directory
    many_pumls_dir.mkdir(exist_ok=True)
    dest_path = many_pumls_dir / Path(file_path).name
    shutil.move(str(file_path), str(dest_path))
    print(f"  Moved original to: {dest_path}")

    return len(diagrams)


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Split PlantUML files containing multiple diagrams into separate files."
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without actually splitting or moving files'
    )
    args = parser.parse_args()

    # Setup directories
    script_dir = Path(__file__).parent
    puml_dir = script_dir / "puml"
    many_pumls_dir = script_dir / "many_pumls"

    if not puml_dir.exists():
        print(f"Error: {puml_dir} directory not found")
        return

    mode_str = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode_str}Scanning for .puml files with multiple diagrams...")
    print(f"Source directory: {puml_dir}")
    if not args.dry_run:
        print(f"Multi-diagram files will be moved to: {many_pumls_dir}")
    print("-" * 60)

    # Process all .puml files
    total_files = 0
    total_split = 0
    total_diagrams = 0

    for puml_file in sorted(puml_dir.glob("*.puml")):
        diagram_count = split_puml_file(puml_file, puml_dir, many_pumls_dir, dry_run=args.dry_run)

        if diagram_count > 0:
            total_files += 1
            total_split += diagram_count
            if not args.dry_run:
                print(f"\n{puml_file.name}: Split into {diagram_count} diagrams")
            total_diagrams += diagram_count

    print("\n" + "=" * 60)
    action_verb = "Would be" if args.dry_run else "Files"
    created_verb = "would be created" if args.dry_run else "created"
    moved_verb = "would be moved" if args.dry_run else "moved"

    print(f"Summary:")
    print(f"  {action_verb} with multiple diagrams: {total_files}")
    print(f"  Total diagrams extracted: {total_diagrams}")
    print(f"  New files {created_verb}: {total_split}")
    if not args.dry_run:
        print(f"  Original files {moved_verb} to: {many_pumls_dir}")


if __name__ == "__main__":
    main()

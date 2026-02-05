#!/usr/bin/env python3
"""Remove 'artifact' from classification results (not a valid UML type)."""

import json
import sys
from pathlib import Path


def fix_artifacts(input_path: str):
    path = Path(input_path)

    with open(path, 'r') as f:
        data = json.load(f)

    classifications = data['classifications']
    primary_fixed = 0
    secondary_removed = 0

    for filename, entry in classifications.items():
        # Fix primary_type
        if entry.get('primary_type') == 'artifact':
            entry['primary_type'] = 'deployment'
            primary_fixed += 1

        # Remove from types dict
        if 'artifact' in entry.get('types', {}):
            del entry['types']['artifact']
            secondary_removed += 1

    # Update statistics
    stats = data['statistics']['type_distribution']
    if 'artifact' in stats:
        artifact_count = stats.pop('artifact')
        stats['deployment'] = stats.get('deployment', 0) + artifact_count

    # Write back
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Fixed {primary_fixed} primary types")
    print(f"Removed {secondary_removed} secondary 'artifact' entries")


if __name__ == "__main__":
    fix_artifacts(sys.argv[1] if len(sys.argv) > 1
                  else 'phase4/llm-classify-results/final_merged_results.json')

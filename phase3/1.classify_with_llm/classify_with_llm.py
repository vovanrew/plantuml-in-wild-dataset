#!/usr/bin/env python3
"""
Script to classify PlantUML diagrams using Claude Haiku 4.5 via Message Batches API.

This script processes large collections of PlantUML files (163k+) efficiently using
Anthropic's batch API for cost-effective classification.

Usage:
    python3 classify_with_llm.py <puml_directory> [options]
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Script version
VERSION = "1.0.0"

# Configuration constants
MODEL_ID = "claude-haiku-4-5-20251001"
DEFAULT_BATCH_SIZE = 100_000
MAX_WORD_COUNT = 5000
TRUNCATE_WORD_COUNT = 4000  # Truncate large files to this many words instead of skipping
POLL_INTERVAL_SECONDS = 60

UML_TYPES = [
    "sequence", "class", "activity", "state", "usecase",
    "component", "deployment", "object", "timing", "unclassified"
]

# Classification prompt template
# Note: Double braces {{ }} are escaped for Python .format() - they render as single braces
CLASSIFICATION_PROMPT = """Classify this PlantUML diagram into UML diagram types.

TYPES (with confidence 0.0-1.0):
- sequence: interactions over time (participant, ->, activate, alt, loop)
- class: classes/interfaces with relationships (class, interface, extends)
- activity: workflow/process flow (start, stop, :action;, if/then/else)
- state: state machine ([*], state, -->)
- usecase: actors and use cases ((usecase), :actor:)
- component: system components ([component], interface, package)
- deployment: physical deployment (node, artifact, device, cloud)
- object: object instances (object, map, field = value)
- timing: timing constraints (@time, robust, concise)
- unclassified: not recognizable UML

OUTPUT FORMAT (JSON only, no other text):
{{
  "types": {{"<type>": <confidence>, ...}},
  "primary_type": "<highest_confidence_type>",
  "reasoning": "<1-sentence explanation>"
}}

EXAMPLE OUTPUT (JSON only, no other text):
{{
  "types": {{"class": 0.8, "sequence": 0.5}},
  "primary_type": "class",
  "reasoning": "This diagram primarily defines classes and their relationships."
}}

RULES:
1. Include types with confidence >= 0.5
2. If no UML patterns, return primary_type: "unclassified"

PlantUML DIAGRAM:
```
{content}
```"""

# Try to import required packages
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Import shared preprocessing utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.preprocessing import preprocess_content


def check_dependencies():
    """Check that required dependencies are installed."""
    if not HAS_ANTHROPIC:
        print("Error: anthropic package not installed.", file=sys.stderr)
        print("Install with: pip install anthropic>=0.40.0", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)


def count_words(content: str) -> int:
    """Count words in content (space-separated tokens)."""
    return len(content.split())


def truncate_to_words(content: str, max_words: int) -> str:
    """Truncate content to the first max_words words."""
    words = content.split()
    if len(words) <= max_words:
        return content
    return ' '.join(words[:max_words])


def discover_files(puml_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Discover all .puml files and analyze word counts.

    Args:
        puml_dir: Directory containing .puml files

    Returns:
        Dictionary with file info: {filename: {path, word_count, needs_truncation, content}}
    """
    files = {}
    puml_files = list(puml_dir.glob("*.puml"))

    print(f"Found {len(puml_files):,} .puml files", file=sys.stderr)
    print("Analyzing file sizes...", file=sys.stderr)

    if HAS_TQDM:
        iterator = tqdm(puml_files, desc="Scanning", unit="file")
    else:
        iterator = puml_files

    for puml_file in iterator:
        try:
            with open(puml_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            word_count = count_words(content)
            needs_truncation = word_count > MAX_WORD_COUNT

            files[puml_file.name] = {
                'path': str(puml_file),
                'word_count': word_count,
                'needs_truncation': needs_truncation,
                'content': content
            }
        except Exception as e:
            files[puml_file.name] = {
                'path': str(puml_file),
                'word_count': 0,
                'needs_truncation': False,
                'content': None
            }

    read_errors = sum(1 for f in files.values() if f['content'] is None)
    to_truncate = sum(1 for f in files.values() if f['needs_truncation'])
    print(f"Files to process: {len(files) - read_errors:,}", file=sys.stderr)
    print(f"Files to truncate (>{MAX_WORD_COUNT} words): {to_truncate:,}", file=sys.stderr)
    if read_errors > 0:
        print(f"Files with read errors: {read_errors:,}", file=sys.stderr)

    return files


def sanitize_custom_id(filename: str) -> str:
    """
    Sanitize filename to be a valid custom_id for the batch API.

    Requirements: ^[a-zA-Z0-9_-]{1,64}$
    """
    # Remove .puml extension
    name = filename.replace('.puml', '')
    # Replace any invalid characters with underscore
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    # Truncate to 64 characters
    return name[:64]


def create_batch_requests(files: Dict[str, Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, str], set]:
    """
    Create batch API requests for files that need classification.

    Args:
        files: Dictionary of file info from discover_files

    Returns:
        Tuple of (request list, id_to_filename mapping, set of truncated filenames)
    """
    requests = []
    id_to_filename = {}  # Maps custom_id -> original filename
    truncated_files = set()  # Track which files were truncated

    for filename, info in files.items():
        if info['content'] is None:
            continue

        # Preprocess content
        preprocessed = preprocess_content(info['content'])

        # Truncate if content exceeds word limit
        if info.get('needs_truncation'):
            preprocessed = truncate_to_words(preprocessed, TRUNCATE_WORD_COUNT)
            truncated_files.add(filename)

        # Create prompt with preprocessed content
        prompt = CLASSIFICATION_PROMPT.format(content=preprocessed)

        # Sanitize custom_id for API requirements
        custom_id = sanitize_custom_id(filename)
        id_to_filename[custom_id] = filename

        request = {
            "custom_id": custom_id,
            "params": {
                "model": MODEL_ID,
                "max_tokens": 256,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        }
        requests.append(request)

    return requests, id_to_filename, truncated_files


def split_into_batches(requests: List[Dict], batch_size: int) -> List[List[Dict]]:
    """Split requests into batches of specified size."""
    batches = []
    for i in range(0, len(requests), batch_size):
        batches.append(requests[i:i + batch_size])
    return batches


def load_state(state_file: Path) -> Optional[Dict]:
    """Load state from file if it exists."""
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    return None


def save_state(state_file: Path, state: Dict):
    """Save state to file."""
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def submit_batches(client: Anthropic, batches: List[List[Dict]], state_file: Path, existing_state: Optional[Dict] = None) -> Dict:
    """
    Submit batches to the API and return state with batch IDs.

    Args:
        client: Anthropic client
        batches: List of batch request lists
        state_file: Path to save state
        existing_state: Optional existing state for resume

    Returns:
        State dictionary with batch info
    """
    if existing_state:
        state = existing_state
    else:
        state = {
            'batches': [],
            'started_at': datetime.now().isoformat(),
            'processed_files': []
        }

    # Find which batches still need to be submitted
    submitted_count = len(state['batches'])

    for i, batch_requests in enumerate(batches[submitted_count:], start=submitted_count):
        print(f"\nSubmitting batch {i + 1}/{len(batches)} ({len(batch_requests):,} requests)...", file=sys.stderr)

        try:
            result = client.messages.batches.create(requests=batch_requests)

            state['batches'].append({
                'batch_id': result.id,
                'status': result.processing_status,
                'file_count': len(batch_requests),
                'submitted_at': datetime.now().isoformat()
            })

            print(f"  Batch ID: {result.id}", file=sys.stderr)
            print(f"  Status: {result.processing_status}", file=sys.stderr)

            # Save state after each submission
            save_state(state_file, state)

        except Exception as e:
            print(f"Error submitting batch {i + 1}: {e}", file=sys.stderr)
            save_state(state_file, state)
            raise

    return state


def poll_batches(client: Anthropic, state: Dict, state_file: Path) -> Dict:
    """
    Poll all batches until they complete.

    Args:
        client: Anthropic client
        state: Current state with batch info
        state_file: Path to save state

    Returns:
        Updated state with final statuses
    """
    print("\nPolling for batch completion...", file=sys.stderr)

    while True:
        all_ended = True
        total_succeeded = 0
        total_failed = 0
        total_processing = 0

        for batch_info in state['batches']:
            batch_id = batch_info['batch_id']

            try:
                result = client.messages.batches.retrieve(batch_id)
                batch_info['status'] = result.processing_status

                # Update counts from batch
                if hasattr(result, 'request_counts'):
                    counts = result.request_counts
                    batch_info['succeeded'] = counts.succeeded
                    batch_info['errored'] = counts.errored
                    batch_info['processing'] = counts.processing

                    total_succeeded += counts.succeeded
                    total_failed += counts.errored
                    total_processing += counts.processing

                if result.processing_status != "ended":
                    all_ended = False

            except Exception as e:
                print(f"Error polling batch {batch_id}: {e}", file=sys.stderr)
                all_ended = False

        # Save state after each poll
        save_state(state_file, state)

        # Print progress
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Progress: {total_succeeded:,} succeeded, {total_processing:,} processing, {total_failed:,} errored", file=sys.stderr)

        if all_ended:
            print("\nAll batches completed!", file=sys.stderr)
            break

        time.sleep(POLL_INTERVAL_SECONDS)

    return state


def extract_json_from_response(text: str) -> Optional[Dict]:
    """
    Extract JSON from LLM response, handling markdown code blocks.

    Args:
        text: Raw response text

    Returns:
        Parsed JSON or None if parsing fails
    """
    # Try direct JSON parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract from markdown code block
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find JSON object pattern
    json_match = re.search(r'\{[^{}]*"types"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def retrieve_results(client: Anthropic, state: Dict, id_to_filename: Dict[str, str]) -> Dict[str, Dict]:
    """
    Retrieve and parse results from all completed batches.

    Args:
        client: Anthropic client
        state: State with batch info
        id_to_filename: Mapping from custom_id to original filename

    Returns:
        Dictionary mapping filename to classification result
    """
    results = {}

    print("\nRetrieving results...", file=sys.stderr)

    for batch_info in state['batches']:
        batch_id = batch_info['batch_id']
        print(f"  Processing batch {batch_id}...", file=sys.stderr)

        try:
            for result in client.messages.batches.results(batch_id):
                custom_id = result.custom_id
                # Map back to original filename
                filename = id_to_filename.get(custom_id, custom_id + '.puml')

                if result.result.type == "succeeded":
                    # Extract text content
                    message = result.result.message
                    if message.content and len(message.content) > 0:
                        text = message.content[0].text

                        # Parse JSON response
                        parsed = extract_json_from_response(text)

                        if parsed:
                            results[filename] = {
                                'diagram_type': 'uml',
                                'primary_type': parsed.get('primary_type', 'unclassified'),
                                'types': parsed.get('types', {}),
                                'confidence': max(parsed.get('types', {}).values()) if parsed.get('types') else 0.0,
                                'reasoning': parsed.get('reasoning', '')
                            }
                        else:
                            # Parse error
                            results[filename] = {
                                'diagram_type': 'uml',
                                'primary_type': 'unclassified',
                                'types': {},
                                'confidence': None,
                                'parse_error': True,
                                'raw_response': text[:500]  # Truncate for debugging
                            }
                    else:
                        results[filename] = {
                            'diagram_type': 'uml',
                            'primary_type': 'unclassified',
                            'types': {},
                            'confidence': None,
                            'error': 'empty_response'
                        }
                else:
                    # API error
                    results[filename] = {
                        'diagram_type': 'uml',
                        'primary_type': 'unclassified',
                        'types': {},
                        'confidence': None,
                        'error': result.result.type
                    }

        except Exception as e:
            print(f"    Error retrieving batch {batch_id}: {e}", file=sys.stderr)

    print(f"  Retrieved {len(results):,} results", file=sys.stderr)
    return results


def generate_output(
    files: Dict[str, Dict],
    results: Dict[str, Dict],
    state: Dict,
    start_time: datetime,
    end_time: datetime,
    truncated_files: set = None
) -> Dict:
    """
    Generate final output JSON structure.

    Args:
        files: Original file info
        results: Classification results from API
        state: Batch state info
        start_time: Processing start time
        end_time: Processing end time
        truncated_files: Set of filenames that were truncated

    Returns:
        Complete output dictionary
    """
    if truncated_files is None:
        truncated_files = set()

    classifications = {}

    # Add results from API
    for filename, result in results.items():
        # Mark truncated files
        if filename in truncated_files:
            result['truncated'] = True
        classifications[filename] = result

    # Calculate statistics
    total_files = len(files)
    successful = sum(1 for c in classifications.values()
                    if c.get('diagram_type') == 'uml' and not c.get('error') and not c.get('parse_error'))
    truncated_count = sum(1 for c in classifications.values() if c.get('truncated'))
    errored = sum(1 for c in classifications.values() if c.get('error') or c.get('parse_error'))

    # Type distribution
    type_dist = {}
    confidences = []
    for c in classifications.values():
        if c.get('diagram_type') == 'uml' and c.get('primary_type'):
            ptype = c['primary_type']
            type_dist[ptype] = type_dist.get(ptype, 0) + 1
            if c.get('confidence') is not None:
                confidences.append(c['confidence'])

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Processing time
    duration = end_time - start_time
    processing_time = str(duration).split('.')[0]

    return {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'model': MODEL_ID,
            'batch_ids': [b['batch_id'] for b in state['batches']],
            'total_files': total_files,
            'word_limit': MAX_WORD_COUNT,
            'truncate_word_count': TRUNCATE_WORD_COUNT,
            'script_version': VERSION
        },
        'statistics': {
            'total_files': total_files,
            'successful': successful,
            'truncated': truncated_count,
            'errored': errored,
            'type_distribution': type_dist,
            'average_confidence': round(avg_confidence, 4),
            'processing_time': processing_time
        },
        'classifications': classifications
    }


def main():
    parser = argparse.ArgumentParser(
        description="Classify PlantUML diagrams using Claude Haiku 4.5 via Message Batches API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 classify_with_llm.py ./puml_validated/valid
  python3 classify_with_llm.py ./puml -o results.json --batch-size 10000
  python3 classify_with_llm.py ./puml --resume

Environment Variables:
  ANTHROPIC_API_KEY    Required API key for Claude
        """
    )

    parser.add_argument(
        "puml_directory",
        help="Directory containing .puml files"
    )

    parser.add_argument(
        "-o", "--output",
        default="llm_classifications.json",
        help="Output JSON file (default: llm_classifications.json)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Requests per batch (default: {DEFAULT_BATCH_SIZE:,}, use smaller for testing)"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved state file"
    )

    args = parser.parse_args()

    # Check dependencies
    check_dependencies()

    # Convert to Path objects
    puml_dir = Path(args.puml_directory).resolve()
    output_file = Path(args.output).resolve()
    state_file = output_file.with_suffix('.json_state.json')

    if not puml_dir.exists():
        print(f"Error: Directory '{puml_dir}' not found", file=sys.stderr)
        sys.exit(1)

    print("=" * 60, file=sys.stderr)
    print("PlantUML LLM Classification", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Model: {MODEL_ID}", file=sys.stderr)
    print(f"Input directory: {puml_dir}", file=sys.stderr)
    print(f"Output file: {output_file}", file=sys.stderr)
    print(f"Batch size: {args.batch_size:,}", file=sys.stderr)
    print(f"Word limit: {MAX_WORD_COUNT:,}", file=sys.stderr)
    print(f"Resume mode: {args.resume}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Initialize client
    client = Anthropic()

    start_time = datetime.now()

    # Check for existing state
    existing_state = None
    if args.resume:
        existing_state = load_state(state_file)
        if existing_state:
            print(f"\nResuming from state file ({len(existing_state['batches'])} batches submitted)", file=sys.stderr)
        else:
            print("\nNo state file found, starting fresh", file=sys.stderr)

    # Discover and analyze files
    files = discover_files(puml_dir)

    # Create batch requests (needed for id_to_filename mapping)
    print("\nPreparing batch requests...", file=sys.stderr)
    requests, id_to_filename, truncated_files = create_batch_requests(files)
    print(f"Total requests to submit: {len(requests):,}", file=sys.stderr)
    if truncated_files:
        print(f"Files truncated to {TRUNCATE_WORD_COUNT} words: {len(truncated_files):,}", file=sys.stderr)

    # Track truncated files in state and save id_to_filename mapping
    if not existing_state:
        existing_state = {
            'batches': [],
            'started_at': datetime.now().isoformat(),
            'truncated_files': list(truncated_files),
            'processed_files': [],
            'id_to_filename': id_to_filename  # Save mapping for resume
        }
    else:
        # Resuming: use saved mapping if available, otherwise use freshly generated
        if 'id_to_filename' in existing_state:
            id_to_filename = existing_state['id_to_filename']
            print(f"  Loaded {len(id_to_filename):,} file mappings from state", file=sys.stderr)
        else:
            # Backwards compatibility: save mapping to existing state
            existing_state['id_to_filename'] = id_to_filename
            print(f"  Added {len(id_to_filename):,} file mappings to state", file=sys.stderr)

    # Save state with mapping immediately (before batch submission)
    save_state(state_file, existing_state)

    # Split into batches
    batches = split_into_batches(requests, args.batch_size)
    print(f"Batches: {len(batches)}", file=sys.stderr)

    if not requests:
        print("\nNo files to process!", file=sys.stderr)
        sys.exit(0)

    # Submit batches
    state = submit_batches(client, batches, state_file, existing_state)

    # Poll for completion
    state = poll_batches(client, state, state_file)

    # Retrieve results
    results = retrieve_results(client, state, id_to_filename)

    end_time = datetime.now()

    # Generate output
    output = generate_output(files, results, state, start_time, end_time, truncated_files)

    # Write output
    print(f"\nWriting output to {output_file}...", file=sys.stderr)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    stats = output['statistics']
    print("\n" + "=" * 60, file=sys.stderr)
    print("Classification Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total files: {stats['total_files']:,}", file=sys.stderr)
    print(f"Successful: {stats['successful']:,}", file=sys.stderr)
    print(f"Truncated: {stats['truncated']:,}", file=sys.stderr)
    print(f"Errored: {stats['errored']:,}", file=sys.stderr)
    print(f"\nType Distribution:", file=sys.stderr)
    for utype, count in sorted(stats['type_distribution'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_files']) * 100 if stats['total_files'] > 0 else 0
        print(f"  {utype}: {count:,} ({percentage:.2f}%)", file=sys.stderr)
    print(f"\nAverage confidence: {stats['average_confidence']:.4f}", file=sys.stderr)
    print(f"Processing time: {stats['processing_time']}", file=sys.stderr)
    print(f"Batch IDs: {', '.join(output['metadata']['batch_ids'])}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Keep state file for debugging (don't delete)
    print(f"\nState file preserved: {state_file}", file=sys.stderr)

    print("\nDone!", file=sys.stderr)


if __name__ == "__main__":
    main()

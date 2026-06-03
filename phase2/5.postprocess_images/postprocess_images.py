#!/usr/bin/env python3
"""Post-process PlantUML PNG renders for the Data in Brief ML image-dataset policy.

For each PNG in the input directory:
  1. If either dimension is below 512 px, pad on a centred canvas so the
     shorter side reaches 512. The pad colour is sampled from pixel (0, 0)
     of the rendered image so custom-background diagrams (dark themes,
     skinparam backgroundColor) keep a uniform background instead of
     gaining a white frame; for the common white-background case the
     sample is (255, 255, 255) and behaviour is unchanged. The original
     rendered pixels are preserved as-is (no scaling, no cropping). The
     canvas size is (max(w, 512), max(h, 512)) so an image that is small
     on one axis but already tall (or wide) on the other is also handled
     without cropping. In the common case where both dimensions are below
     512 the output is exactly 512x512.
  2. Convert to RGB so the dataset has a single uniform colour model. The
     current renders are a mix of palette / RGB / RGBA.
  3. Save back over the input file. Filenames and extensions are preserved
     because phase 3 metadata is keyed by filename. Writes go through a
     temp file + atomic rename so a killed run cannot leave a half-written
     PNG in place of the original.

The script is idempotent: a PNG that already has both dimensions >= 512 and
mode RGB is left on disk unchanged.

Usage:
    python3 postprocess_images.py <input-dir>
"""

import argparse
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter("ignore", Image.DecompressionBombWarning)


MIN_SIDE = 512
PROGRESS_EVERY = 5000


def _fmt_secs(s: float) -> str:
    s = int(s)
    return f"{s // 60}m{s % 60:02d}s"


def _atomic_save(img: Image.Image, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    img.save(tmp, format="PNG")
    os.replace(tmp, path)


def _detect_bg(img: Image.Image) -> tuple[int, int, int]:
    """Sample pixel (0, 0) as the diagram's page background.

    PlantUML always renders with margins, so the top-left pixel is reliably
    the page background, not a diagram element. For default-styled diagrams
    this returns (255, 255, 255); for themed or skinparam-customised diagrams
    it returns the actual background, avoiding a mismatched white pad frame.
    """
    return img.convert("RGB").getpixel((0, 0))


def postprocess_one(path: Path) -> str:
    """Process one PNG in place. Returns one of: 'padded', 'converted', 'unchanged'."""
    with Image.open(path) as img:
        w, h = img.size
        mode = img.mode

        # Fast path: already conformant. Header is parsed by Image.open() without
        # decoding pixels, so we can skip the expensive .load() entirely.
        if w >= MIN_SIDE and h >= MIN_SIDE and mode == "RGB":
            return "unchanged"

        img.load()

        if w < MIN_SIDE or h < MIN_SIDE:
            new_w = max(w, MIN_SIDE)
            new_h = max(h, MIN_SIDE)
            canvas = Image.new("RGB", (new_w, new_h), _detect_bg(img))
            canvas.paste(img.convert("RGB"), ((new_w - w) // 2, (new_h - h) // 2))
            _atomic_save(canvas, path)
            return "padded"

        _atomic_save(img.convert("RGB"), path)
        return "converted"


def _process_one_worker(path_str: str) -> tuple[str, str | None, str | None]:
    """ProcessPoolExecutor worker entry point.

    Takes a string (cheaper than pickling a Path) and returns
    (path, result, error_repr) where exactly one of result/error is None.
    """
    try:
        return (path_str, postprocess_one(Path(path_str)), None)
    except Exception as e:
        return (path_str, None, repr(e))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pad small PNGs so the shorter side reaches 512 px and "
                    "convert every PNG to RGB, in place.",
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory of PNG files to post-process in place.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="Number of parallel worker processes (default: all CPU cores).",
    )
    args = parser.parse_args()

    in_dir: Path = args.input_dir
    if not in_dir.is_dir():
        print(f"Error: not a directory: {in_dir}", file=sys.stderr)
        return 1

    files = sorted(in_dir.glob("*.png"))
    n = len(files)
    workers = max(1, args.workers)
    print(f"Scanning {n} PNG files in {in_dir} with {workers} workers", flush=True)

    counts = {"padded": 0, "converted": 0, "unchanged": 0}
    errors: list[str] = []
    t0 = time.monotonic()

    paths_str = [str(p) for p in files]
    # chunksize 8 keeps per-task IPC low while letting the OS scheduler still
    # interleave the long-tail large files across workers.
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (path_str, result, err) in enumerate(
            ex.map(_process_one_worker, paths_str, chunksize=8), start=1
        ):
            if err is not None:
                errors.append(f"{Path(path_str).name}: {err}")
            else:
                counts[result] += 1
            if i % PROGRESS_EVERY == 0:
                dt = time.monotonic() - t0
                rate = i / dt if dt > 0 else 0.0
                eta = (n - i) / rate if rate > 0 else 0.0
                print(
                    f"  {i}/{n}  elapsed {_fmt_secs(dt)}  "
                    f"rate {rate:.0f} f/s  ETA {_fmt_secs(eta)}",
                    file=sys.stderr,
                    flush=True,
                )

    total_dt = time.monotonic() - t0
    modified = counts["padded"] + counts["converted"]
    print()
    print(f"Total scanned:  {n}  in {_fmt_secs(total_dt)}")
    print(f"Files modified: {modified} ({100 * modified / n:.2f}%)" if n else "Files modified: 0")
    print(f"  Padded to >= {MIN_SIDE} px (also RGB):       {counts['padded']}")
    print(f"  Converted to RGB only (size already OK):    {counts['converted']}")
    print(f"  Already conformant, left untouched on disk: {counts['unchanged']}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for line in errors[:10]:
            print(f"    {line}")
        if len(errors) > 10:
            print(f"    ... ({len(errors) - 10} more)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Convert cProfile .prof files to speedscope JSON format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import pstats
import sys
from typing import Any


def convert_prof_to_speedscope(prof_path: str) -> dict[str, Any]:
    """Convert a cProfile .prof file to speedscope JSON format."""
    stats = pstats.Stats(prof_path)

    frames, frame_index = _build_frames(stats)

    samples, weights = _build_samples(stats, frame_index)

    # Build speedscope JSON structure
    return {
        "$schema": "https://www.speedscope.app/file-format-schema.json",
        "version": "0.0.1",
        "shared": {
            "frames": frames,
        },
        "profiles": [
            {
                "type": "sampled",
                "name": Path(prof_path).stem,
                "unit": "microseconds",
                "startValue": 0,
                "endValue": sum(weights),
                "samples": samples,
                "weights": weights,
            },
        ],
    }


def _build_frames(
    stats: pstats.Stats,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Build frame list and name->index mapping."""
    frames: list[dict[str, str]] = []
    frame_index: dict[str, int] = {}

    for filename, line, func in stats.stats:
        frame_name = f"{func} ({Path(filename).name}:{line})"
        if frame_name not in frame_index:
            frame_index[frame_name] = len(frames)
            frames.append(
                {
                    "name": func,
                    "file": filename,
                    "line": line,
                },
            )

    return frames, frame_index


def _build_samples(
    stats: pstats.Stats,
    frame_index: dict[str, int],
) -> tuple[list[list[int]], list[float]]:
    """Build samples and weights from pstats."""
    samples: list[list[int]] = []
    weights: list[float] = []

    for (filename, line, func), (
        _cc,
        _nc,
        _tt,
        ct,
        callers,
    ) in stats.stats.items():
        frame_name = f"{func} ({Path(filename).name}:{line})"
        idx = frame_index[frame_name]

        stack = _build_stack(callers, frame_index, idx)

        samples.append(stack[::-1])  # Reverse for proper order
        weights.append(ct * 1_000_000)  # Convert to microseconds

    return samples, weights


def _build_stack(
    callers: Any,
    frame_index: dict[str, int],
    leaf_idx: int,
) -> list[int]:
    stack = [leaf_idx]
    for caller_filename, caller_line, caller_func in callers:
        caller_name = (
            f"{caller_func} ({Path(caller_filename).name}:{caller_line})"
        )
        idx = frame_index.get(caller_name)
        if idx is not None:
            stack.append(idx)
    return stack


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Convert cProfile .prof to speedscope JSON",
    )
    parser.add_argument("input", help="Input .prof file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file (default: input.speedscope.json)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(1)

    output_path = args.output or str(
        input_path.with_suffix(".speedscope.json"),
    )

    speedscope_data = convert_prof_to_speedscope(str(input_path))

    with Path(output_path).open("w", encoding="utf-8") as f:
        json.dump(speedscope_data, f)


if __name__ == "__main__":
    main()

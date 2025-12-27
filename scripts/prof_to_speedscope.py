#!/usr/bin/env python3
"""Convert cProfile .prof files to speedscope JSON format."""
from __future__ import annotations

import argparse
import json
import pstats
import sys
from pathlib import Path
from typing import Any


def convert_prof_to_speedscope(prof_path: str) -> dict[str, Any]:
    """Convert a cProfile .prof file to speedscope JSON format."""
    stats = pstats.Stats(prof_path)
    
    # Build frame list and index mapping
    frames: list[dict[str, str]] = []
    frame_index: dict[str, int] = {}
    
    for (filename, line, func), (cc, nc, tt, ct, callers) in stats.stats.items():
        frame_name = f"{func} ({Path(filename).name}:{line})"
        if frame_name not in frame_index:
            frame_index[frame_name] = len(frames)
            frames.append({
                "name": func,
                "file": filename,
                "line": line,
            })
    
    # Build samples from stats
    samples: list[list[int]] = []
    weights: list[float] = []
    
    for (filename, line, func), (cc, nc, tt, ct, callers) in stats.stats.items():
        frame_name = f"{func} ({Path(filename).name}:{line})"
        idx = frame_index[frame_name]
        
        # Build stack from callers
        stack = [idx]
        for caller_key in callers:
            caller_filename, caller_line, caller_func = caller_key
            caller_name = f"{caller_func} ({Path(caller_filename).name}:{caller_line})"
            if caller_name in frame_index:
                stack.append(frame_index[caller_name])
        
        samples.append(stack[::-1])  # Reverse for proper order
        weights.append(ct * 1_000_000)  # Convert to microseconds
    
    # Build speedscope JSON structure
    speedscope_data = {
        "$schema": "https://www.speedscope.app/file-format-schema.json",
        "version": "0.0.1",
        "shared": {
            "frames": frames
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
            }
        ],
    }
    
    return speedscope_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert cProfile .prof to speedscope JSON"
    )
    parser.add_argument("input", help="Input .prof file")
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: input.speedscope.json)"
    )
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)
    
    output_path = args.output or str(input_path.with_suffix(".speedscope.json"))
    
    speedscope_data = convert_prof_to_speedscope(str(input_path))
    
    with open(output_path, "w") as f:
        json.dump(speedscope_data, f)
    
    print(f"Converted: {input_path} -> {output_path}")
    print(f"Open https://www.speedscope.app/ and load {output_path}")


if __name__ == "__main__":
    main()

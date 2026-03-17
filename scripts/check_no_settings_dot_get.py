#!/usr/bin/env python3
"""Fail if settings is read via .get() or getattr(). Only settings.SECTION.KEY allowed (AGENTS.md §7)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# settings.get( anything
PATTERN_GET = re.compile(r"settings\.get\s*\(")
# getattr(settings, ...) or getattr(settings.SECTION, ...)
PATTERN_GETATTR = re.compile(
    r"getattr\s*\(\s*settings(\s*,\s*|\.[A-Za-z_][A-Za-z0-9_]*\s*,\s*)",
)

ROOTS = ("src", "tests")


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    found: list[tuple[str, int, str]] = []
    for root in ROOTS:
        dir_path = repo / root
        if not dir_path.is_dir():
            continue
        for path in dir_path.rglob("*.py"):
            text = path.read_text()
            for i, line in enumerate(text.splitlines(), start=1):
                if PATTERN_GET.search(line) or PATTERN_GETATTR.search(line):
                    found.append((str(path.relative_to(repo)), i, line.strip()))
    if not found:
        return 0
    print(
        "Forbidden: only settings.SECTION.KEY allowed. No .get() or getattr(settings...). See AGENTS.md §7.",
        file=sys.stderr,
    )
    for filepath, lineno, line in found:
        print(f"  {filepath}:{lineno}: {line[:79]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

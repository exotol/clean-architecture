"""Check Dynaconf settings usage.

Fails if code reads Dynaconf settings via ``settings.get(...)`` or
``getattr(...)``.
Allowed form only: ``settings.SECTION.KEY`` (see ``AGENTS.md`` §7).
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator


PATTERN_GET = re.compile(r"settings\.get\s*\(")
PATTERN_GETATTR = re.compile(
    r"getattr\s*\(\s*settings(\s*,\s*|\.[A-Za-z_][A-Za-z0-9_]*\s*,\s*)",
)

ROOTS = ("src", "tests")


def _iter_python_files(repo_root: Path) -> Iterator[Path]:
    """Yield all Python files under selected roots."""
    for root in ROOTS:
        dir_path = repo_root / root
        if not dir_path.is_dir():
            continue
        yield from dir_path.rglob("*.py")


def _collect_violations(repo_root: Path) -> list[tuple[str, int, str]]:
    """Collect forbidden settings access lines."""
    violations: list[tuple[str, int, str]] = []
    for path in _iter_python_files(repo_root):
        text = path.read_text(encoding="utf-8")
        relpath = str(path.relative_to(repo_root))
        for lineno, line in enumerate(text.splitlines(), start=1):
            if PATTERN_GET.search(line) or PATTERN_GETATTR.search(line):
                violations.append((relpath, lineno, line.strip()))
    return violations


def main() -> int:
    """Run the check and return 0 on success, 1 on violations."""
    repo_root = Path(__file__).resolve().parent.parent
    violations = _collect_violations(repo_root)
    if not violations:
        return 0

    for _filepath, _lineno, _line in violations:
        pass
    return 1


if __name__ == "__main__":
    sys.exit(main())

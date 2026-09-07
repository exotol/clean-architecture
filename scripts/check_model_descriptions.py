"""Combined linter runner for BaseModel and dataclass field descriptions."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from scripts.check_basemodel_descriptions import (
    run_checks as run_basemodel_checks,
)
from scripts.check_dataclass_descriptions import (
    run_checks as run_dataclass_checks,
)


if TYPE_CHECKING:
    from scripts.linter_utils import Violation


def run_all_checks(
    paths: list[str] | tuple[str, ...],
    *,
    include_tests: bool = False,
) -> list[Violation]:
    """Run both BaseModel and dataclass description checks."""
    violations: list[Violation] = []
    violations.extend(run_basemodel_checks(paths, include_tests=include_tests))
    violations.extend(run_dataclass_checks(paths, include_tests=include_tests))
    return violations


def main() -> int:
    """CLI entrypoint for all model and dataclass description checks."""
    args = sys.argv[1:]
    include_tests = "--include-tests" in args
    targets = [arg for arg in args if not arg.startswith("--")]

    violations = run_all_checks(targets, include_tests=include_tests)
    if not violations:
        return 0

    for violation in violations:
        sys.stderr.write(f"{violation.format()}\n")

    sys.stderr.write(
        f"\nFound {len(violations)} total description violation(s).\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

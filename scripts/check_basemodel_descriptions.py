"""Linter to verify that all Pydantic BaseModel fields have descriptions.

Rule BM001: Every field in a Pydantic BaseModel must have a non-empty
'description' defined via Field(description="...") or
Annotated[Type, Field(description="...")].
"""

from __future__ import annotations

import ast
import sys
from typing import TYPE_CHECKING

from scripts.linter_utils import Violation
from scripts.linter_utils import has_annotated_description
from scripts.linter_utils import has_field_call_description
from scripts.linter_utils import is_class_var
from scripts.linter_utils import iter_python_files


if TYPE_CHECKING:
    from pathlib import Path


IGNORED_FIELD_NAMES = {"model_config", "Config"}
BASEMODEL_NAMES = {"BaseModel", "BaseSettings"}


def _is_basemodel_class(node: ast.ClassDef, known_models: set[str]) -> bool:
    """Check if class inherits from BaseModel or another known model."""
    for base in node.bases:
        if isinstance(base, ast.Name) and (
            base.id in BASEMODEL_NAMES or base.id in known_models
        ):
            return True
        if isinstance(base, ast.Attribute) and (
            base.attr in BASEMODEL_NAMES or base.attr in known_models
        ):
            return True
    return False


def _is_ignored_field(stmt: ast.AnnAssign) -> bool:
    """Check if statement is not a model field or should be skipped."""
    if not isinstance(stmt.target, ast.Name):
        return True
    field_name = stmt.target.id
    if field_name.startswith("_") or field_name in IGNORED_FIELD_NAMES:
        return True
    return is_class_var(stmt.annotation)


def _check_basemodel_field(
    stmt: ast.AnnAssign,
    class_node: ast.ClassDef,
    file_path: str,
) -> Violation | None:
    """Check single field statement in BaseModel for description."""
    if _is_ignored_field(stmt):
        return None

    field_name = stmt.target.id if isinstance(stmt.target, ast.Name) else ""
    has_desc = has_field_call_description(
        stmt.value,
    ) or has_annotated_description(stmt.annotation)
    if not has_desc:
        return Violation(
            file_path=file_path,
            line=stmt.lineno,
            col=stmt.col_offset,
            class_name=class_node.name,
            field_name=field_name,
            code="BM001",
            message=(
                "Field is missing a non-empty 'description' parameter "
                "in Field(...)."
            ),
        )

    return None


def _check_basemodel_class(
    node: ast.ClassDef,
    file_path: str,
) -> list[Violation]:
    """Check all fields in a BaseModel class definition."""
    violations: list[Violation] = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign):
            violation = _check_basemodel_field(stmt, node, file_path)
            if violation is not None:
                violations.append(violation)
    return violations


def _parse_source_file(file_path: Path) -> ast.Module | Violation:
    """Parse python source file into AST module or return syntax Violation."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as err:
        return Violation(
            file_path=str(file_path),
            line=getattr(err, "lineno", 1) or 1,
            col=getattr(err, "offset", 0) or 0,
            class_name="<module>",
            field_name="<syntax>",
            code="BM000",
            message=f"Could not parse file: {err}",
        )


def check_file(file_path: Path) -> list[Violation]:
    """Inspect Python file and return list of BaseModel field violations."""
    tree = _parse_source_file(file_path)
    if isinstance(tree, Violation):
        return [tree]

    violations: list[Violation] = []
    known_models: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and _is_basemodel_class(
            node,
            known_models,
        ):
            known_models.add(node.name)
            violations.extend(_check_basemodel_class(node, str(file_path)))

    return violations


def run_checks(
    paths: list[str] | tuple[str, ...],
    *,
    include_tests: bool = False,
) -> list[Violation]:
    """Run BaseModel description checks on target files or default root."""
    files = iter_python_files(
        paths,
        default_root="src",
        include_tests=include_tests,
    )
    violations: list[Violation] = []
    for file_path in files:
        violations.extend(check_file(file_path))
    return violations


def main() -> int:
    """CLI entrypoint for BaseModel description linter."""
    args = sys.argv[1:]
    include_tests = "--include-tests" in args
    targets = [arg for arg in args if not arg.startswith("--")]

    violations = run_checks(targets, include_tests=include_tests)
    if not violations:
        return 0

    for violation in violations:
        sys.stderr.write(f"{violation.format()}\n")

    sys.stderr.write(
        f"\nFound {len(violations)} BaseModel description violation(s).\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

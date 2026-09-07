"""Linter to verify that all dataclass fields have descriptions.

Rule DC001: Every field in a dataclass must have a description via:
- field(metadata={"description": "..."}) or field(doc="...")
- Field(description="...")
- Annotated[Type, Field(description="...")] or Annotated[Type, "description"]
- Attribute docstring immediately below the field
- Documented under Attributes: or Args: in the class docstring
"""

from __future__ import annotations

import ast
import sys
from typing import TYPE_CHECKING

from scripts.linter_utils import Violation
from scripts.linter_utils import has_annotated_description
from scripts.linter_utils import has_dataclass_field_metadata_description
from scripts.linter_utils import has_field_call_description
from scripts.linter_utils import is_class_var
from scripts.linter_utils import is_kw_only
from scripts.linter_utils import is_non_empty_str
from scripts.linter_utils import iter_python_files
from scripts.linter_utils import parse_docstring_attributes


if TYPE_CHECKING:
    from pathlib import Path


DATACLASS_DECORATOR_NAMES = {"dataclass"}


def _is_dataclass(node: ast.ClassDef) -> bool:
    """Check if class is decorated with @dataclass."""
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if (
            isinstance(target, ast.Name)
            and target.id in DATACLASS_DECORATOR_NAMES
        ):
            return True
        if (
            isinstance(target, ast.Attribute)
            and target.attr in DATACLASS_DECORATOR_NAMES
        ):
            return True
    return False


def _has_attribute_docstring(body: list[ast.stmt], current_index: int) -> bool:
    """Check if statement immediately following field is docstring."""
    next_index = current_index + 1
    if next_index >= len(body):
        return False
    next_stmt = body[next_index]
    return isinstance(next_stmt, ast.Expr) and is_non_empty_str(
        next_stmt.value,
    )


def _is_ignored_dataclass_field(stmt: ast.AnnAssign) -> bool:
    """Check if statement is not a dataclass field or should be skipped."""
    if not isinstance(stmt.target, ast.Name):
        return True
    name = stmt.target.id
    if name.startswith("_") or name == "_":
        return True
    return is_class_var(stmt.annotation) or is_kw_only(stmt.annotation)


def _is_described_dataclass_field(
    stmt: ast.AnnAssign,
    stmt_index: int,
    class_node: ast.ClassDef,
    docstring_attributes: set[str],
) -> bool:
    """Check whether dataclass field has any valid description."""
    if has_dataclass_field_metadata_description(stmt.value):
        return True
    if has_field_call_description(stmt.value):
        return True
    if has_annotated_description(stmt.annotation):
        return True
    if _has_attribute_docstring(class_node.body, stmt_index):
        return True
    field_name = stmt.target.id if isinstance(stmt.target, ast.Name) else ""
    return field_name in docstring_attributes


def _check_dataclass_field(
    stmt: ast.AnnAssign,
    stmt_index: int,
    class_node: ast.ClassDef,
    docstring_attributes: set[str],
    file_path: str,
) -> Violation | None:
    """Check single dataclass field for presence of description."""
    if _is_ignored_dataclass_field(stmt):
        return None

    if _is_described_dataclass_field(
        stmt,
        stmt_index,
        class_node,
        docstring_attributes,
    ):
        return None

    field_name = stmt.target.id if isinstance(stmt.target, ast.Name) else ""
    return Violation(
        file_path=file_path,
        line=stmt.lineno,
        col=stmt.col_offset,
        class_name=class_node.name,
        field_name=field_name,
        code="DC001",
        message=(
            "Dataclass field is missing a description (use "
            "field(metadata={'description': ...}), Field(description=...), "
            "attribute docstring, or class docstring Attributes: section)."
        ),
    )


def _check_dataclass_class(
    node: ast.ClassDef,
    file_path: str,
) -> list[Violation]:
    """Check single dataclass node for field violations."""
    docstring = ast.get_docstring(node)
    docstring_attributes = parse_docstring_attributes(docstring)
    violations: list[Violation] = []
    for idx, stmt in enumerate(node.body):
        if isinstance(stmt, ast.AnnAssign):
            violation = _check_dataclass_field(
                stmt=stmt,
                stmt_index=idx,
                class_node=node,
                docstring_attributes=docstring_attributes,
                file_path=file_path,
            )
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
            code="DC000",
            message=f"Could not parse file: {err}",
        )


def check_file(file_path: Path) -> list[Violation]:
    """Inspect Python file and return list of dataclass field violations."""
    tree = _parse_source_file(file_path)
    if isinstance(tree, Violation):
        return [tree]

    violations: list[Violation] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and _is_dataclass(node):
            violations.extend(_check_dataclass_class(node, str(file_path)))
    return violations


def run_checks(
    paths: list[str] | tuple[str, ...],
    *,
    include_tests: bool = False,
) -> list[Violation]:
    """Run dataclass description checks on target files or default root."""
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
    """CLI entrypoint for dataclass description linter."""
    args = sys.argv[1:]
    include_tests = "--include-tests" in args
    targets = [arg for arg in args if not arg.startswith("--")]

    violations = run_checks(targets, include_tests=include_tests)
    if not violations:
        return 0

    for violation in violations:
        sys.stderr.write(f"{violation.format()}\n")

    sys.stderr.write(
        f"\nFound {len(violations)} dataclass description violation(s).\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

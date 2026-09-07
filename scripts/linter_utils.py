"""Shared AST utilities and data structures for model description linters."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re


DOCSTRING_SECTION_RE = re.compile(
    r"^(?:Args|Arguments|Attributes|Fields):\s*$",
    re.IGNORECASE,
)
ATTRIBUTE_NAME_RE = re.compile(
    r"^\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\s*\([^)]*\))?:\s*(?P<desc>\S.*)$",
)


@dataclass(frozen=True)
class Violation:
    """Represents a linter violation for missing description."""

    file_path: str
    line: int
    col: int
    class_name: str
    field_name: str
    code: str
    message: str

    def format(self) -> str:
        """Format violation in standard compiler/linter error style."""
        return (
            f"{self.file_path}:{self.line}:{self.col}: "
            f"[{self.code}] Field '{self.field_name}' in class "
            f"'{self.class_name}': {self.message}"
        )


@dataclass(frozen=True)
class CodeViolation:
    """Represents a general code or test standard violation."""

    file_path: str
    line: int
    col: int
    code: str
    message: str

    def format(self) -> str:
        """Format violation in standard compiler/linter error style."""
        return (
            f"{self.file_path}:{self.line}:{self.col}: "
            f"[{self.code}] {self.message}"
        )


def _is_test_path(path: Path) -> bool:
    """Check whether a path points to test directory or test file."""
    parts = set(path.parts)
    if "tests" in parts:
        return True
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _collect_file_path(
    path: Path,
    *,
    include_tests: bool,
    result: list[Path],
) -> None:
    """Collect single Python file if allowed."""
    if path.suffix == ".py" and (include_tests or not _is_test_path(path)):
        result.append(path)


def _collect_dir_paths(
    dir_path: Path,
    *,
    include_tests: bool,
    result: list[Path],
) -> None:
    """Collect Python files from directory recursively."""
    paths = (
        path
        for path in sorted(dir_path.rglob("*.py"))
        if include_tests or not _is_test_path(path)
    )
    result.extend(paths)


def iter_python_files(
    targets: list[str] | tuple[str, ...],
    default_root: str = "src",
    *,
    include_tests: bool = False,
) -> list[Path]:
    """Collect Python files from targets or default root directory."""
    raw_targets = list(targets) if targets else [default_root]
    result: list[Path] = []
    for item in raw_targets:
        target_path = Path(item)
        if target_path.is_file():
            _collect_file_path(
                target_path,
                include_tests=include_tests,
                result=result,
            )
        elif target_path.is_dir():
            _collect_dir_paths(
                target_path,
                include_tests=include_tests,
                result=result,
            )
    return result


def is_class_var(annotation: ast.AST | None) -> bool:
    """Check if type annotation is ClassVar or typing.ClassVar."""
    if annotation is None:
        return False
    if isinstance(annotation, ast.Subscript):
        return _is_name_or_attr(annotation.value, "ClassVar")
    return _is_name_or_attr(annotation, "ClassVar")


def is_kw_only(annotation: ast.AST | None) -> bool:
    """Check if type annotation is KW_ONLY or dataclasses.KW_ONLY."""
    if annotation is None:
        return False
    return _is_name_or_attr(annotation, "KW_ONLY")


def _is_name_or_attr(node: ast.AST, expected_name: str) -> bool:
    """Check if node matches expected name directly or via attribute."""
    if isinstance(node, ast.Name):
        return node.id == expected_name
    if isinstance(node, ast.Attribute):
        return node.attr == expected_name
    return False


def is_non_empty_str(node: ast.AST | None) -> bool:
    """Check if AST node represents a non-empty string expression."""
    if node is None:
        return False
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(node.value.strip())
    if isinstance(node, ast.JoinedStr):
        return bool(node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return is_non_empty_str(node.left) or is_non_empty_str(node.right)
    return False


def get_call_kwarg(call: ast.Call, kwarg_name: str) -> ast.AST | None:
    """Find and return value node for given keyword argument in call."""
    for kw in call.keywords:
        if kw.arg == kwarg_name:
            return kw.value
    return None


def is_call_to(node: ast.AST | None, expected_func_names: set[str]) -> bool:
    """Check if node is call to one of the expected function names."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in expected_func_names
    if isinstance(func, ast.Attribute):
        return func.attr in expected_func_names
    return False


def has_field_call_description(node: ast.AST | None) -> bool:
    """Check if node is Field(...) call with non-empty description."""
    if not is_call_to(node, {"Field"}) or not isinstance(node, ast.Call):
        return False
    desc_val = get_call_kwarg(node, "description")
    return is_non_empty_str(desc_val)


def _is_desc_element(elem: ast.AST) -> bool:
    """Check if slice element provides description."""
    return has_field_call_description(elem) or is_non_empty_str(elem)


def has_annotated_description(annotation: ast.AST | None) -> bool:
    """Check if annotation is Annotated with Field(description=...)."""
    if not isinstance(annotation, ast.Subscript):
        return False
    if not _is_name_or_attr(annotation.value, "Annotated"):
        return False

    elements = (
        list(annotation.slice.elts)
        if isinstance(annotation.slice, ast.Tuple)
        else [annotation.slice]
    )
    return any(_is_desc_element(elem) for elem in elements[1:])


def _extract_section_lines(docstring: str) -> list[str]:
    """Extract lines belonging to the Attributes or Args section."""
    lines = docstring.splitlines()
    in_section = False
    section_lines: list[str] = []
    for line in lines:
        trimmed = line.strip()
        if DOCSTRING_SECTION_RE.match(trimmed):
            in_section = True
            continue
        if not in_section:
            continue
        if trimmed and not line.startswith((" ", "\t")):
            break
        section_lines.append(line)
    return section_lines


def parse_docstring_attributes(docstring: str | None) -> set[str]:
    """Parse documented attribute names from Google/Sphinx style docstring."""
    if not docstring:
        return set()

    attributes: set[str] = set()
    for line in _extract_section_lines(docstring):
        match = ATTRIBUTE_NAME_RE.match(line)
        if match:
            attributes.add(match.group("name"))
    return attributes


def _has_dict_description_entry(metadata_node: ast.Dict) -> bool:
    """Check if metadata dictionary contains non-empty description."""
    for key_node, val_node in zip(
        metadata_node.keys,
        metadata_node.values,
        strict=False,
    ):
        if (
            isinstance(key_node, ast.Constant)
            and key_node.value == "description"
            and is_non_empty_str(val_node)
        ):
            return True
    return False


def has_dataclass_field_metadata_description(value: ast.AST | None) -> bool:
    """Check if value is field(metadata={'description': ...})."""
    if not is_call_to(value, {"field"}) or not isinstance(value, ast.Call):
        return False

    doc_arg = get_call_kwarg(value, "doc")
    if is_non_empty_str(doc_arg):
        return True

    metadata_node = get_call_kwarg(value, "metadata")
    if isinstance(metadata_node, ast.Dict):
        return _has_dict_description_entry(metadata_node)

    return False

"""Linter enforcing test-writing standards from docs/testing.md.

Rules enforced across test suites (unit, integration, e2e):
- TST001: Missing '# Arrange' comment in test function.
- TST002: Missing '# Act' comment in test function.
- TST003: Missing '# Assert' comment in test function.
- TST004: Incorrect AAA comment order (Arrange < Act < Assert).
- TST005: Bare 'assert' statement without message or with empty message.
- TST006: Parametrize case missing explicit non-empty id in pytest.param.
- TST007: Parametrize argument names must follow ('entity', 'expected').
- TST008: Test function missing verification (assert or pytest.raises).
"""

from __future__ import annotations

import ast
import io
from pathlib import Path
import re
import sys
import tokenize

from scripts.linter_utils import CodeViolation


ARRANGE_RE = re.compile(r"^#\s*Arrange\b", re.IGNORECASE)
ACT_RE = re.compile(r"^#\s*Act\b", re.IGNORECASE)
ASSERT_RE = re.compile(r"^#\s*Assert\b", re.IGNORECASE)
PARAMETRIZE_NAMES = {
    "parametrize",
    "pytest.mark.parametrize",
    "mark.parametrize",
}
EXPECTED_PARAM_NAMES = {("entity", "expected")}
EXPECTED_PARAM_STRS = {"entity, expected", "entity,expected"}


MIN_PARAMETRIZE_ARGS = 2


def _get_call_name(node: ast.AST) -> str:
    """Resolve dotted call name from AST node."""
    if isinstance(node, ast.Call):
        return _get_call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _has_valid_aaa_order(
    arrange_lines: list[int],
    act_lines: list[int],
    assert_lines: list[int],
) -> bool:
    """Check if there is a valid Arrange < Act < Assert line sequence."""
    for arr in arrange_lines:
        for act in act_lines:
            for ass in assert_lines:
                if arr < act < ass:
                    return True
    return False


def _check_aaa_comments(
    comments: list[tuple[int, str]],
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
) -> list[CodeViolation]:
    """Verify presence and order of Arrange, Act, Assert comments."""
    start_line = node.lineno
    end_line = getattr(node, "end_lineno", start_line)
    func_comments = [c for c in comments if start_line <= c[0] <= end_line]

    arrange_lines = [
        line_no for line_no, c in func_comments if ARRANGE_RE.search(c)
    ]
    act_lines = [line_no for line_no, c in func_comments if ACT_RE.search(c)]
    assert_lines = [
        line_no for line_no, c in func_comments if ASSERT_RE.search(c)
    ]

    violations: list[CodeViolation] = []
    if not arrange_lines:
        violations.append(
            CodeViolation(
                file_path=file_path,
                line=start_line,
                col=node.col_offset,
                code="TST001",
                message=f"Test function '{node.name}' is missing '# Arrange'.",
            ),
        )
    if not act_lines:
        violations.append(
            CodeViolation(
                file_path=file_path,
                line=start_line,
                col=node.col_offset,
                code="TST002",
                message=f"Test function '{node.name}' is missing '# Act'.",
            ),
        )
    if not assert_lines:
        violations.append(
            CodeViolation(
                file_path=file_path,
                line=start_line,
                col=node.col_offset,
                code="TST003",
                message=f"Test function '{node.name}' is missing '# Assert'.",
            ),
        )

    if (
        arrange_lines
        and act_lines
        and assert_lines
        and not _has_valid_aaa_order(arrange_lines, act_lines, assert_lines)
    ):
        violations.append(
            CodeViolation(
                file_path=file_path,
                line=start_line,
                col=node.col_offset,
                code="TST004",
                message=(
                    f"Invalid AAA sequence in '{node.name}': "
                    "'# Arrange' must precede '# Act', and "
                    "'# Act' must precede '# Assert'."
                ),
            ),
        )

    return violations


def _check_assert_node(
    assert_node: ast.Assert,
    func_name: str,
    file_path: str,
) -> CodeViolation | None:
    """Validate a single assert statement has a non-empty message."""
    if assert_node.msg is None:
        return CodeViolation(
            file_path=file_path,
            line=assert_node.lineno,
            col=assert_node.col_offset,
            code="TST005",
            message=(
                f"Bare 'assert' statement without message in '{func_name}'. "
                "Always provide a descriptive explanation "
                "(actual vs expected)."
            ),
        )
    if isinstance(assert_node.msg, ast.Constant) and not bool(
        str(assert_node.msg.value).strip(),
    ):
        return CodeViolation(
            file_path=file_path,
            line=assert_node.lineno,
            col=assert_node.col_offset,
            code="TST005",
            message=(
                f"Empty assert message in '{func_name}'. "
                "Provide a descriptive explanation (actual vs expected)."
            ),
        )
    return None


def _check_assert_messages(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
) -> list[CodeViolation]:
    """Ensure all assert statements in the test function have messages."""
    violations: list[CodeViolation] = []
    for inner in ast.walk(node):
        if isinstance(inner, ast.Assert):
            violation = _check_assert_node(inner, node.name, file_path)
            if violation is not None:
                violations.append(violation)
    return violations


def _is_valid_param_names(arg: ast.AST) -> bool:
    """Check if parametrize argument names follow standard."""
    if isinstance(arg, (ast.Tuple, ast.List)):
        names = tuple(
            elt.value for elt in arg.elts if isinstance(elt, ast.Constant)
        )
        return names in EXPECTED_PARAM_NAMES
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value.strip() in EXPECTED_PARAM_STRS
    return False


def _check_param_case(
    elt: ast.AST,
    func_name: str,
    file_path: str,
) -> CodeViolation | None:
    """Verify that a parametrize case has pytest.param with non-empty id."""
    if isinstance(elt, ast.Call):
        call_name = _get_call_name(elt.func)
        if call_name in {"pytest.param", "param"}:
            for kw in elt.keywords:
                if (
                    kw.arg == "id"
                    and isinstance(kw.value, ast.Constant)
                    and bool(str(kw.value.value).strip())
                ):
                    return None
    return CodeViolation(
        file_path=file_path,
        line=elt.lineno,
        col=elt.col_offset,
        code="TST006",
        message=(
            f"Parametrize case in '{func_name}' must use "
            "pytest.param(..., id='...') with a non-empty identifier."
        ),
    )


def _check_parametrize_decorator(
    dec: ast.Call,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
) -> list[CodeViolation]:
    """Validate argument names and id parameter in pytest.mark.parametrize."""
    violations: list[CodeViolation] = []
    if len(dec.args) >= 1 and not _is_valid_param_names(dec.args[0]):
        violations.append(
            CodeViolation(
                file_path=file_path,
                line=dec.lineno,
                col=dec.col_offset,
                code="TST007",
                message=(
                    f"Parametrize argument names in '{node.name}' must be "
                    "('entity', 'expected')."
                ),
            ),
        )

    if len(dec.args) >= MIN_PARAMETRIZE_ARGS and isinstance(
        dec.args[1],
        (ast.List, ast.Tuple),
    ):
        for elt in dec.args[1].elts:
            violation = _check_param_case(elt, node.name, file_path)
            if violation is not None:
                violations.append(violation)

    return violations


def _is_verification_node(inner: ast.AST) -> bool:
    """Check if AST node represents an assertion, pytest.raises, or helper."""
    if isinstance(inner, ast.Assert):
        return True
    if isinstance(inner, ast.With):
        return any(
            "raises" in _get_call_name(it.context_expr) for it in inner.items
        )
    if isinstance(inner, ast.Call):
        name = _get_call_name(inner.func)
        return name.startswith(("assert_", "_assert_"))
    return False


def _check_test_verification(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
) -> list[CodeViolation]:
    """Ensure test function body contains verification (assert or raises)."""
    has_assert = any(_is_verification_node(inner) for inner in ast.walk(node))
    if not has_assert:
        return [
            CodeViolation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code="TST008",
                message=(
                    f"Test function '{node.name}' does not contain any "
                    "assertions, pytest.raises block, or assert helpers."
                ),
            ),
        ]
    return []


def _check_test_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    comments: list[tuple[int, str]],
    file_path: str,
) -> list[CodeViolation]:
    """Run all test writing standard checks on a single test function."""
    violations: list[CodeViolation] = []
    violations.extend(_check_aaa_comments(comments, node, file_path))
    violations.extend(_check_assert_messages(node, file_path))

    for dec in node.decorator_list:
        if (
            isinstance(dec, ast.Call)
            and _get_call_name(dec.func) in PARAMETRIZE_NAMES
        ):
            violations.extend(
                _check_parametrize_decorator(dec, node, file_path),
            )

    violations.extend(_check_test_verification(node, file_path))
    return violations


def _extract_comments(code: str) -> list[tuple[int, str]]:
    """Extract comment tokens with line numbers from source code."""
    comments: list[tuple[int, str]] = []
    stream = io.StringIO(code).readline
    try:
        tokens = tokenize.generate_tokens(stream)
        comments.extend(
            (tok.start[0], tok.string.strip())
            for tok in tokens
            if tok.type == tokenize.COMMENT
        )
    except tokenize.TokenError:
        pass
    return comments


def check_source(
    code: str,
    file_path: str = "<string>",
) -> list[CodeViolation]:
    """Check test source code string for testing standard violations."""
    comments = _extract_comments(code)
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError as exc:
        return [
            CodeViolation(
                file_path=file_path,
                line=exc.lineno or 1,
                col=exc.offset or 0,
                code="TST000",
                message=f"Syntax error in test file: {exc.msg}",
            ),
        ]

    violations: list[CodeViolation] = []
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ) and node.name.startswith("test_"):
            violations.extend(
                _check_test_function(node, comments, file_path),
            )

    return violations


def check_file(file_path: Path) -> list[CodeViolation]:
    """Check a Python test file for test standard violations."""
    try:
        code = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            CodeViolation(
                file_path=str(file_path),
                line=1,
                col=0,
                code="TST000",
                message=f"Could not read test file: {exc}",
            ),
        ]
    return check_source(code, str(file_path))


def _is_test_file(path: Path) -> bool:
    """Check if file is a test module and not fixture or schema."""
    if path.suffix != ".py":
        return False
    parts = set(path.parts)
    if "schemas" in parts or "performance" in parts:
        return False
    if path.name == "conftest.py" or path.name.startswith("__"):
        return False
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _resolve_target_paths(targets: list[str]) -> list[Path]:
    """Resolve test file paths from CLI targets or default test directories."""
    default_roots = ("tests/unit", "tests/integration", "tests/e2e")
    roots = targets or list(default_roots)
    collected: list[Path] = []
    for item in roots:
        path = Path(item)
        if path.is_file() and _is_test_file(path):
            collected.append(path)
        elif path.is_dir():
            collected.extend(
                p for p in sorted(path.rglob("*.py")) if _is_test_file(p)
            )
    return collected


def run_checks(targets: list[str] | tuple[str, ...]) -> list[CodeViolation]:
    """Run test writing standard checks on specified paths or test suite."""
    files = _resolve_target_paths(list(targets))
    violations: list[CodeViolation] = []
    for file_path in files:
        violations.extend(check_file(file_path))
    return violations


def main() -> int:
    """CLI entrypoint for test writing standard linter."""
    targets = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    violations = run_checks(targets)

    if not violations:
        return 0

    for violation in violations:
        sys.stderr.write(f"{violation.format()}\n")

    sys.stderr.write(
        f"\nFound {len(violations)} test standard violation(s).\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

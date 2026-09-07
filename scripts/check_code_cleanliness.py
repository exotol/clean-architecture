"""Linter enforcing project-wide cleanliness rules.

Rules enforced across the entire project (src/, tests/, scripts/):
- CLN001: Prohibition of '# noqa' suppression comments.
- CLN002: Prohibition of '# type: ignore' or '# pyright: ignore' comments.
- CLN003: Prohibition of other check suppressions (# pragma: no cover, etc.).
- CLN004: Prohibition of nested functions (except decorators returning inner).
"""

from __future__ import annotations

import ast
import io
from pathlib import Path
import re
import sys
import tokenize

from scripts.linter_utils import CodeViolation


NOQA_RE = re.compile(r"^#\s*(?:noqa|flake8:\s*noqa)\b", re.IGNORECASE)
TYPE_IGNORE_RE = re.compile(
    r"^#\s*(?:type:\s*ignore|pyright:\s*ignore)\b",
    re.IGNORECASE,
)
OTHER_SUPPRESSION_RE = re.compile(
    r"^#\s*(?:pragma:\s*no cover|pylint:\s*disable)\b",
    re.IGNORECASE,
)


def _check_suppression_token(
    tok: tokenize.TokenInfo,
    file_path: str,
) -> CodeViolation | None:
    """Check a single comment token for forbidden suppression directives."""
    text = tok.string.strip()
    if NOQA_RE.search(text):
        return CodeViolation(
            file_path=file_path,
            line=tok.start[0],
            col=tok.start[1],
            code="CLN001",
            message=(
                "Suppression directive '# noqa' is strictly forbidden. "
                "Fix the issue in code instead of suppressing it."
            ),
        )
    if TYPE_IGNORE_RE.search(text):
        return CodeViolation(
            file_path=file_path,
            line=tok.start[0],
            col=tok.start[1],
            code="CLN002",
            message=(
                "Type suppression directive "
                "('# type: ignore' / '# pyright: ignore') is strictly "
                "forbidden. Fix the typing issue in code instead."
            ),
        )
    if OTHER_SUPPRESSION_RE.search(text):
        return CodeViolation(
            file_path=file_path,
            line=tok.start[0],
            col=tok.start[1],
            code="CLN003",
            message=(
                f"Suppression directive '{text}' is strictly forbidden. "
                "Fix the underlying issue in code instead."
            ),
        )
    return None


def _check_suppressions(code: str, file_path: str) -> list[CodeViolation]:
    """Inspect comments in code for any forbidden suppression directives."""
    violations: list[CodeViolation] = []
    stream = io.StringIO(code).readline
    try:
        tokens = tokenize.generate_tokens(stream)
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                violation = _check_suppression_token(tok, file_path)
                if violation is not None:
                    violations.append(violation)
    except tokenize.TokenError:
        pass
    return violations


def _return_expression_matches(value: ast.AST | None, inner_name: str) -> bool:
    """Check whether a return expression references the inner function name."""
    if value is None:
        return False
    if isinstance(value, ast.Name) and value.id == inner_name:
        return True
    if isinstance(value, ast.Call):
        for arg in value.args:
            if isinstance(arg, ast.Name) and arg.id == inner_name:
                return True
    return False


def _collect_parent_returns(
    node: ast.AST,
    inner_node: ast.AST,
    results: list[ast.Return],
) -> None:
    """Collect Return nodes in parent skipping descendants of inner_node."""
    if node is inner_node:
        return
    if isinstance(node, ast.Return):
        results.append(node)
    for child in ast.iter_child_nodes(node):
        _collect_parent_returns(child, inner_node, results)


def _is_decorator_inner_function(
    parent: ast.FunctionDef | ast.AsyncFunctionDef,
    inner: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Verify if parent function returns the inner function as decorator."""
    returns: list[ast.Return] = []
    for stmt in parent.body:
        _collect_parent_returns(stmt, inner, returns)

    for ret in returns:
        if _return_expression_matches(ret.value, inner.name):
            return True
    return False


def _check_nested_functions_in_node(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
    violations: list[CodeViolation],
) -> None:
    """Check if function node contains any forbidden nested functions."""
    violations.extend(
        CodeViolation(
            file_path=file_path,
            line=child.lineno,
            col=child.col_offset,
            code="CLN004",
            message=(
                f"Nested function '{child.name}' is forbidden. "
                "Move logic to module or class level (only "
                "decorators returning inner functions are allowed)."
            ),
        )
        for child in node.body
        if isinstance(
            child,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and not _is_decorator_inner_function(node, child)
    )


def _check_ast_nodes(
    tree: ast.Module,
    file_path: str,
) -> list[CodeViolation]:
    """Traverse AST module and check for nested function violations."""
    violations: list[CodeViolation] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_nested_functions_in_node(node, file_path, violations)
    return violations


def check_source(
    code: str,
    file_path: str = "<string>",
) -> list[CodeViolation]:
    """Check source code string for cleanliness violations."""
    violations = _check_suppressions(code, file_path)
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError as exc:
        violations.append(
            CodeViolation(
                file_path=file_path,
                line=exc.lineno or 1,
                col=exc.offset or 0,
                code="CLN000",
                message=f"Syntax error: {exc.msg}",
            ),
        )
        return violations

    violations.extend(_check_ast_nodes(tree, file_path))
    return violations


def check_file(file_path: Path) -> list[CodeViolation]:
    """Check Python file for cleanliness violations."""
    try:
        code = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            CodeViolation(
                file_path=str(file_path),
                line=1,
                col=0,
                code="CLN000",
                message=f"Could not read file: {exc}",
            ),
        ]
    return check_source(code, str(file_path))


def _resolve_target_paths(targets: list[str]) -> list[Path]:
    """Resolve file paths from CLI targets or project default directories."""
    default_roots = ("src", "tests", "scripts")
    roots = targets or list(default_roots)
    collected: list[Path] = []
    for item in roots:
        path = Path(item)
        if path.is_file() and path.suffix == ".py":
            collected.append(path)
        elif path.is_dir():
            collected.extend(sorted(path.rglob("*.py")))
    return collected


def run_checks(targets: list[str] | tuple[str, ...]) -> list[CodeViolation]:
    """Run code cleanliness checks on specified paths or entire repository."""
    files = _resolve_target_paths(list(targets))
    violations: list[CodeViolation] = []
    for file_path in files:
        violations.extend(check_file(file_path))
    return violations


def main() -> int:
    """CLI entrypoint for code cleanliness linter."""
    targets = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    violations = run_checks(targets)

    if not violations:
        return 0

    for violation in violations:
        sys.stderr.write(f"{violation.format()}\n")

    sys.stderr.write(
        f"\nFound {len(violations)} code cleanliness violation(s).\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

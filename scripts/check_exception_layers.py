"""Linter enforcing exception usage rules across Clean Architecture layers.

Rules enforced across the codebase (primarily src/app/):
- EXC001: Prohibition of HTTPException outside the presentation layer.
- EXC002: Prohibition of InfrastructureError in domain/application layers.
- EXC003: Prohibition of bare 'raise Exception(...)' in application source.
- EXC004: Prohibition of external I/O imports in domain/application layers.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

from scripts.linter_utils import CodeViolation


FORBIDDEN_IO_LIBRARIES = frozenset(
    {"httpx", "asyncpg", "sqlalchemy", "redis", "aiohttp", "requests"},
)

HTTP_EXCEPTION_NAMES = frozenset({"HTTPException"})


def _is_in_layer(file_path: str, layer_prefix: str) -> bool:
    """Check if file path belongs to a specific architecture layer."""
    normalized = file_path.replace("\\", "/")
    return f"/{layer_prefix}/" in normalized or normalized.startswith(
        f"{layer_prefix}/",
    )


def _check_http_exception_node(
    node: ast.AST,
    file_path: str,
) -> CodeViolation | None:
    """Check if HTTPException is imported outside presentation layer."""
    if _is_in_layer(file_path, "presentation"):
        return None

    if isinstance(node, ast.ImportFrom):
        for alias in node.names:
            if alias.name in HTTP_EXCEPTION_NAMES:
                return CodeViolation(
                    file_path=file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    code="EXC001",
                    message=(
                        f"HTTPException ('{alias.name}') is forbidden outside "
                        "presentation layer. Use domain/app exceptions."
                    ),
                )
    return None


def _check_infra_error_node(
    node: ast.AST,
    file_path: str,
) -> CodeViolation | None:
    """Check if InfrastructureError is imported in domain or application."""
    is_domain = _is_in_layer(file_path, "domain")
    is_application = _is_in_layer(file_path, "application")
    if not (is_domain or is_application):
        return None

    if isinstance(node, ast.ImportFrom):
        for alias in node.names:
            if alias.name == "InfrastructureError":
                layer = "domain" if is_domain else "application"
                return CodeViolation(
                    file_path=file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    code="EXC002",
                    message=(
                        f"InfrastructureError is forbidden in {layer} layer. "
                        "Raise BusinessError or domain-specific exceptions."
                    ),
                )
    return None


def _check_bare_exception_node(
    node: ast.AST,
    file_path: str,
) -> CodeViolation | None:
    """Check for forbidden bare 'raise Exception(...)' in app source."""
    normalized = file_path.replace("\\", "/")
    if not ("/src/app/" in normalized or normalized.startswith("src/app/")):
        return None

    if isinstance(node, ast.Raise) and node.exc is not None:
        target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(target, ast.Name) and target.id == "Exception":
            return CodeViolation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code="EXC003",
                message=(
                    "Bare 'raise Exception(...)' is forbidden. Use AppError "
                    "subclasses or standard validation errors."
                ),
            )
    return None


def _check_import_io_package(
    node: ast.Import,
    layer: str,
    file_path: str,
) -> CodeViolation | None:
    """Check standard import statement for forbidden external I/O packages."""
    for alias in node.names:
        top_pkg = alias.name.split(".")[0]
        if top_pkg in FORBIDDEN_IO_LIBRARIES:
            return CodeViolation(
                file_path=file_path,
                line=node.lineno,
                col=node.col_offset,
                code="EXC004",
                message=(
                    f"Import of external I/O library '{alias.name}' is "
                    f"forbidden in {layer} layer."
                ),
            )
    return None


def _check_import_from_io_package(
    node: ast.ImportFrom,
    layer: str,
    file_path: str,
) -> CodeViolation | None:
    """Check import-from statement for forbidden external I/O packages."""
    if not node.module:
        return None
    top_pkg = node.module.split(".")[0]
    if top_pkg in FORBIDDEN_IO_LIBRARIES:
        return CodeViolation(
            file_path=file_path,
            line=node.lineno,
            col=node.col_offset,
            code="EXC004",
            message=(
                f"Import from external I/O library '{node.module}' is "
                f"forbidden in {layer} layer."
            ),
        )
    return None


def _check_io_library_node(
    node: ast.AST,
    file_path: str,
) -> CodeViolation | None:
    """Check if external I/O libraries are imported in domain/application."""
    is_domain = _is_in_layer(file_path, "domain")
    is_application = _is_in_layer(file_path, "application")
    if not (is_domain or is_application):
        return None

    layer = "domain" if is_domain else "application"
    if isinstance(node, ast.Import):
        return _check_import_io_package(node, layer, file_path)
    if isinstance(node, ast.ImportFrom):
        return _check_import_from_io_package(node, layer, file_path)
    return None


def _inspect_node(node: ast.AST, file_path: str) -> CodeViolation | None:
    """Check a single AST node against all exception boundary rules."""
    return (
        _check_http_exception_node(node, file_path)
        or _check_infra_error_node(node, file_path)
        or _check_bare_exception_node(node, file_path)
        or _check_io_library_node(node, file_path)
    )


def check_source(
    code: str,
    file_path: str = "<string>",
) -> list[CodeViolation]:
    """Check source code for exception layer violations."""
    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError as exc:
        return [
            CodeViolation(
                file_path=file_path,
                line=exc.lineno or 1,
                col=exc.offset or 0,
                code="EXC000",
                message=f"Syntax error: {exc.msg}",
            ),
        ]

    violations: list[CodeViolation] = []
    for node in ast.walk(tree):
        v = _inspect_node(node, file_path)
        if v is not None:
            violations.append(v)
    return violations


def check_file(file_path: Path) -> list[CodeViolation]:
    """Check a Python file for exception layer violations."""
    try:
        code = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            CodeViolation(
                file_path=str(file_path),
                line=1,
                col=0,
                code="EXC000",
                message=f"Could not read file: {exc}",
            ),
        ]
    return check_source(code, str(file_path))


def _resolve_target_paths(targets: list[str]) -> list[Path]:
    """Resolve file paths from CLI targets or default directories."""
    default_roots = ("src/app",)
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
    """Run exception layer checks on specified paths or app directory."""
    files = _resolve_target_paths(list(targets))
    violations: list[CodeViolation] = []
    for file_path in files:
        violations.extend(check_file(file_path))
    return violations


def main() -> int:
    """CLI entrypoint for exception layer linter."""
    targets = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    violations = run_checks(targets)

    if not violations:
        return 0

    for violation in violations:
        sys.stderr.write(f"{violation.format()}\n")

    sys.stderr.write(
        f"\nFound {len(violations)} exception layer violation(s).\n",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

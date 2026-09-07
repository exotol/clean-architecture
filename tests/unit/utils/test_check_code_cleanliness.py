"""Unit tests for code cleanliness linter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from scripts.check_code_cleanliness import check_file
from scripts.check_code_cleanliness import check_source
from scripts.check_code_cleanliness import main
from scripts.check_code_cleanliness import run_checks

from tests.schemas.unit.utils.code_cleanliness_linter import (
    CleanlinessExpected,
)
from tests.schemas.unit.utils.code_cleanliness_linter import (
    CleanlinessSnippetEntity,
)


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            CleanlinessSnippetEntity(
                code=("def add(a: int, b: int) -> int:\n    return a + b\n"),
            ),
            CleanlinessExpected(is_valid=True),
            id="clean_function_valid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code=(
                    "def my_decorator(func):\n"
                    "    def wrapper(*args, **kwargs):\n"
                    "        return func(*args, **kwargs)\n"
                    "    return wrapper\n"
                ),
            ),
            CleanlinessExpected(is_valid=True),
            id="decorator_returning_wrapper_valid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code=(
                    "def factory(prefix: str):\n"
                    "    def decorator(func):\n"
                    "        def wrapper(*args, **kwargs):\n"
                    "            return func(*args, **kwargs)\n"
                    "        return wrapper\n"
                    "    return decorator\n"
                ),
            ),
            CleanlinessExpected(is_valid=True),
            id="decorator_factory_valid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code="x = 1  # noqa\n",
            ),
            CleanlinessExpected(
                is_valid=False,
                expected_violation_code="CLN001",
            ),
            id="noqa_suppression_invalid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code="x = 1  # type: ignore[assignment]\n",
            ),
            CleanlinessExpected(
                is_valid=False,
                expected_violation_code="CLN002",
            ),
            id="type_ignore_suppression_invalid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code="x = 1  # pyright: ignore[reportMissingImports]\n",
            ),
            CleanlinessExpected(
                is_valid=False,
                expected_violation_code="CLN002",
            ),
            id="pyright_ignore_suppression_invalid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code="def uncovered():  # pragma: no cover\n    pass\n",
            ),
            CleanlinessExpected(
                is_valid=False,
                expected_violation_code="CLN003",
            ),
            id="pragma_suppression_invalid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code=(
                    "def outer():\n"
                    "    def helper():\n"
                    "        return 42\n"
                    "    return helper()\n"
                ),
            ),
            CleanlinessExpected(
                is_valid=False,
                expected_violation_code="CLN004",
            ),
            id="nested_helper_not_decorator_invalid",
        ),
        pytest.param(
            CleanlinessSnippetEntity(
                code=(
                    "def outer():\n"
                    "    async def async_helper():\n"
                    "        return 1\n"
                    "    return 0\n"
                ),
            ),
            CleanlinessExpected(
                is_valid=False,
                expected_violation_code="CLN004",
            ),
            id="nested_async_not_decorator_invalid",
        ),
    ],
)
def test_code_cleanliness_snippets(
    entity: CleanlinessSnippetEntity,
    expected: CleanlinessExpected,
) -> None:
    # Arrange

    # Act
    violations = check_source(entity.code, entity.file_path)

    # Assert
    if expected.is_valid:
        assert len(violations) == 0, (
            f"Expected 0 violations for valid snippet, got: {violations}"
        )
    else:
        assert len(violations) > 0, (
            f"Expected violations for snippet: {entity.code!r}, got 0"
        )
        codes = [v.code for v in violations]
        assert expected.expected_violation_code in codes, (
            f"Expected code '{expected.expected_violation_code}' in {codes}"
        )


def test_code_cleanliness_syntax_error() -> None:
    # Arrange
    bad_code = "def syntax_broken(:"

    # Act
    violations = check_source(bad_code, "broken.py")

    # Assert
    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    assert violations[0].code == "CLN000", (
        f"Expected CLN000, got {violations[0].code}"
    )


def test_code_cleanliness_file_helpers(tmp_path: Path) -> None:
    # Arrange
    test_file = tmp_path / "valid.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    # Act
    file_violations = check_file(test_file)
    run_violations = run_checks([str(tmp_path)])

    # Assert
    assert len(file_violations) == 0, (
        f"Expected 0 violations, got {len(file_violations)}"
    )
    assert len(run_violations) == 0, (
        f"Expected 0 run violations, got {len(run_violations)}"
    )


def test_code_cleanliness_file_not_found(tmp_path: Path) -> None:
    # Arrange
    missing_file = tmp_path / "missing.py"

    # Act
    violations = check_file(missing_file)

    # Assert
    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    assert violations[0].code == "CLN000", (
        f"Expected CLN000, got {violations[0].code}"
    )


def test_code_cleanliness_main_entrypoint(tmp_path: Path) -> None:
    # Arrange
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("def ok(): pass\n", encoding="utf-8")
    dirty_file = tmp_path / "dirty.py"
    dirty_file.write_text("x = 1 # noqa\n", encoding="utf-8")

    # Act & Assert
    # Act
    with patch("sys.argv", ["check_code_cleanliness", str(clean_file)]):
        clean_code = main()

    with patch("sys.argv", ["check_code_cleanliness", str(dirty_file)]):
        dirty_code = main()

    # Assert
    assert clean_code == 0, f"Expected exit code 0, got {clean_code}"
    assert dirty_code == 1, f"Expected exit code 1, got {dirty_code}"

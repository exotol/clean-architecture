"""Unit tests for exception layers linter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from scripts.check_exception_layers import check_file
from scripts.check_exception_layers import check_source
from scripts.check_exception_layers import main
from scripts.check_exception_layers import run_checks

from tests.schemas.unit.utils.exception_layers_linter import (
    ExceptionLayersExpected,
)
from tests.schemas.unit.utils.exception_layers_linter import (
    ExceptionLayersSnippetEntity,
)


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            ExceptionLayersSnippetEntity(
                code=(
                    "from app.core.exceptions import BusinessError\n\n"
                    "def execute() -> None:\n"
                    "    raise BusinessError('Something is wrong')\n"
                ),
                file_path="src/app/application/service.py",
            ),
            ExceptionLayersExpected(is_valid=True),
            id="valid_application_code",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code=(
                    "from fastapi import HTTPException\n\n"
                    "def get_item() -> None:\n"
                    "    raise HTTPException("
                    "status_code=404, detail='Not found'"
                    ")\n"
                ),
                file_path="src/app/presentation/api/v1/endpoints/item.py",
            ),
            ExceptionLayersExpected(is_valid=True),
            id="valid_presentation_http_exception",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code=(
                    "import httpx\n"
                    "from app.core.exceptions import InfrastructureError\n\n"
                    "def fetch() -> None:\n"
                    "    raise InfrastructureError('Network failure')\n"
                ),
                file_path="src/app/infrastructure/client.py",
            ),
            ExceptionLayersExpected(is_valid=True),
            id="valid_infrastructure_io_import",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code="from fastapi import HTTPException\n",
                file_path="src/app/domain/models.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC001",
            ),
            id="exc001_http_exception_in_domain",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code="from starlette.exceptions import HTTPException\n",
                file_path="src/app/application/use_case.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC001",
            ),
            id="exc001_http_exception_in_application",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code="from app.core.exceptions import InfrastructureError\n",
                file_path="src/app/domain/entities.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC002",
            ),
            id="exc002_infra_error_in_domain",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code="from app.core.exceptions import InfrastructureError\n",
                file_path="src/app/application/order_service.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC002",
            ),
            id="exc002_infra_error_in_application",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code=(
                    "def process() -> None:\n"
                    "    raise Exception('Generic failure')\n"
                ),
                file_path="src/app/application/order_service.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC003",
            ),
            id="exc003_bare_raise_exception",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code="import httpx\n",
                file_path="src/app/domain/service.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC004",
            ),
            id="exc004_io_import_in_domain",
        ),
        pytest.param(
            ExceptionLayersSnippetEntity(
                code="from sqlalchemy.orm import Session\n",
                file_path="src/app/application/service.py",
            ),
            ExceptionLayersExpected(
                is_valid=False,
                expected_violation_code="EXC004",
            ),
            id="exc004_io_import_from_in_application",
        ),
    ],
)
def test_exception_layers_snippets(
    entity: ExceptionLayersSnippetEntity,
    expected: ExceptionLayersExpected,
) -> None:
    # Arrange
    code = entity.code
    file_path = entity.file_path

    # Act
    violations = check_source(code, file_path=file_path)

    # Assert
    if expected.is_valid:
        assert len(violations) == 0, (
            f"Expected 0 violations for {file_path}, got {len(violations)}: "
            f"{[v.format() for v in violations]}"
        )
    else:
        assert len(violations) > 0, (
            f"Expected violations for {file_path}, got 0"
        )
        codes = [v.code for v in violations]
        assert expected.expected_violation_code in codes, (
            f"Expected {expected.expected_violation_code} in {codes}"
        )


def test_exception_layers_syntax_error() -> None:
    # Arrange
    invalid_syntax = "def invalid_syntax(:\n"

    # Act
    violations = check_source(invalid_syntax)

    # Assert
    assert len(violations) == 1, (
        f"Expected 1 violation for syntax error, got {len(violations)}"
    )
    assert violations[0].code == "EXC000", (
        f"Expected EXC000 violation, got {violations[0].code}"
    )


def test_exception_layers_file_helpers(tmp_path: Path) -> None:
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


def test_exception_layers_file_not_found(tmp_path: Path) -> None:
    # Arrange
    missing_file = tmp_path / "missing.py"

    # Act
    violations = check_file(missing_file)

    # Assert
    assert len(violations) == 1, (
        f"Expected 1 violation for missing file, got {len(violations)}"
    )
    assert violations[0].code == "EXC000", (
        f"Expected EXC000, got {violations[0].code}"
    )


def test_exception_layers_main_entrypoint(tmp_path: Path) -> None:
    # Arrange
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("def ok(): pass\n", encoding="utf-8")
    dirty_file = tmp_path / "src" / "app" / "domain" / "dirty.py"
    dirty_file.parent.mkdir(parents=True, exist_ok=True)
    dirty_file.write_text("import httpx\n", encoding="utf-8")

    # Act
    with patch("sys.argv", ["check_exception_layers", str(clean_file)]):
        clean_code = main()

    with patch("sys.argv", ["check_exception_layers", str(dirty_file)]):
        dirty_code = main()

    # Assert
    assert clean_code == 0, f"Expected exit code 0, got {clean_code}"
    assert dirty_code == 1, f"Expected exit code 1, got {dirty_code}"

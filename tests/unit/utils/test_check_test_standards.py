"""Unit tests for test writing standards linter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from scripts.check_test_standards import check_file
from scripts.check_test_standards import check_source
from scripts.check_test_standards import main
from scripts.check_test_standards import run_checks

from tests.schemas.unit.utils.test_standards_linter import StandardsExpected
from tests.schemas.unit.utils.test_standards_linter import (
    StandardsSnippetEntity,
)


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "@pytest.mark.parametrize(\n"
                    "    ('entity', 'expected'),\n"
                    "    [\n"
                    "        pytest.param(1, 2, id='valid_case'),\n"
                    "    ],\n"
                    ")\n"
                    "def test_valid(entity: int, expected: int) -> None:\n"
                    "    # Arrange\n"
                    "    x = entity\n"
                    "    # Act\n"
                    "    res = x + 1\n"
                    "    # Assert\n"
                    "    assert res == expected, (\n"
                    "        f'Expected {expected}, got {res}'\n"
                    "    )\n"
                ),
            ),
            StandardsExpected(is_valid=True),
            id="valid_standard_test",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "async def test_valid_async() -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    with pytest.raises(ValueError):\n"
                    "        raise ValueError('boom')\n"
                    "    # Assert\n"
                    "    assert True, 'Success'\n"
                ),
            ),
            StandardsExpected(is_valid=True),
            id="valid_async_raises_test",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_missing_arrange() -> None:\n"
                    "    # Act\n"
                    "    res = 1\n"
                    "    # Assert\n"
                    "    assert res == 1, 'OK'\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST001",
            ),
            id="missing_arrange_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_missing_act() -> None:\n"
                    "    # Arrange\n"
                    "    res = 1\n"
                    "    # Assert\n"
                    "    assert res == 1, 'OK'\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST002",
            ),
            id="missing_act_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_missing_assert() -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    res = 1\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST003",
            ),
            id="missing_assert_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_bad_order() -> None:\n"
                    "    # Act\n"
                    "    res = 1\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Assert\n"
                    "    assert res == 1, 'OK'\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST004",
            ),
            id="bad_aaa_order_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_bare_assert() -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    res = 1\n"
                    "    # Assert\n"
                    "    assert res == 1\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST005",
            ),
            id="bare_assert_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_empty_assert_msg() -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    res = 1\n"
                    "    # Assert\n"
                    "    assert res == 1, ''\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST005",
            ),
            id="empty_assert_msg_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "@pytest.mark.parametrize(\n"
                    "    ('entity', 'expected'),\n"
                    "    [\n"
                    "        (1, 2),\n"
                    "    ],\n"
                    ")\n"
                    "def test_param_without_id(entity, expected) -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    res = entity + 1\n"
                    "    # Assert\n"
                    "    assert res == expected, 'OK'\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST006",
            ),
            id="parametrize_missing_id_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "@pytest.mark.parametrize(\n"
                    "    ('val', 'exp'),\n"
                    "    [\n"
                    "        pytest.param(1, 2, id='c1'),\n"
                    "    ],\n"
                    ")\n"
                    "def test_bad_param_names(val, exp) -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    res = val + 1\n"
                    "    # Assert\n"
                    "    assert res == exp, 'OK'\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST007",
            ),
            id="bad_param_names_invalid",
        ),
        pytest.param(
            StandardsSnippetEntity(
                code=(
                    "def test_no_assertions() -> None:\n"
                    "    # Arrange\n"
                    "    pass\n"
                    "    # Act\n"
                    "    x = 1\n"
                    "    # Assert\n"
                    "    print(x)\n"
                ),
            ),
            StandardsExpected(
                is_valid=False,
                expected_violation_code="TST008",
            ),
            id="no_assertions_invalid",
        ),
    ],
)
def test_test_standards_snippets(
    entity: StandardsSnippetEntity,
    expected: StandardsExpected,
) -> None:
    # Arrange

    # Act
    violations = check_source(entity.code, entity.file_path)

    # Assert
    if expected.is_valid:
        assert len(violations) == 0, (
            f"Expected 0 violations for valid test snippet, got: {violations}"
        )
    else:
        assert len(violations) > 0, (
            f"Expected violations for snippet: {entity.code!r}, got 0"
        )
        codes = [v.code for v in violations]
        assert expected.expected_violation_code in codes, (
            f"Expected code '{expected.expected_violation_code}' in {codes}"
        )


def test_test_standards_syntax_error() -> None:
    # Arrange
    bad_code = "def test_broken(:"

    # Act
    violations = check_source(bad_code, "test_broken.py")

    # Assert
    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    assert violations[0].code == "TST000", (
        f"Expected TST000, got {violations[0].code}"
    )


def test_test_standards_file_helpers(tmp_path: Path) -> None:
    # Arrange
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_ok():\n"
        "    # Arrange\n"
        "    pass\n"
        "    # Act\n"
        "    res = 1\n"
        "    # Assert\n"
        "    assert res == 1, 'OK'\n",
        encoding="utf-8",
    )

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


def test_test_standards_file_not_found(tmp_path: Path) -> None:
    # Arrange
    missing_file = tmp_path / "missing_test.py"

    # Act
    violations = check_file(missing_file)

    # Assert
    assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
    assert violations[0].code == "TST000", (
        f"Expected TST000, got {violations[0].code}"
    )


def test_test_standards_main_entrypoint(tmp_path: Path) -> None:
    # Arrange
    clean_file = tmp_path / "test_clean.py"
    clean_file.write_text(
        "def test_ok():\n"
        "    # Arrange\n"
        "    pass\n"
        "    # Act\n"
        "    x = 1\n"
        "    # Assert\n"
        "    assert x == 1, 'OK'\n",
        encoding="utf-8",
    )
    dirty_file = tmp_path / "test_dirty.py"
    dirty_file.write_text(
        "def test_bad():\n    assert 1 == 1\n",
        encoding="utf-8",
    )

    # Act
    with patch("sys.argv", ["check_test_standards", str(clean_file)]):
        clean_code = main()

    with patch("sys.argv", ["check_test_standards", str(dirty_file)]):
        dirty_code = main()

    # Assert
    assert clean_code == 0, f"Expected exit code 0, got {clean_code}"
    assert dirty_code == 1, f"Expected exit code 1, got {dirty_code}"

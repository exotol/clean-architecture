"""Unit tests for check_basemodel_descriptions linter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts.check_basemodel_descriptions import check_file
from scripts.check_basemodel_descriptions import run_checks

from tests.schemas.unit.utils.descriptions_linter import LinterExpected
from tests.schemas.unit.utils.descriptions_linter import LinterSnippetEntity


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel, Field\n"
                    "class SearchSchema(BaseModel):\n"
                    "    query: str = Field(..., description='Query string')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_model_with_field_description",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel, Field\n"
                    "class Pagination(BaseModel):\n"
                    "    limit: int = Field(10, description='Items limit')\n"
                    "    offset: int = Field(0, description='Items offset')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_model_with_default_and_description",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from typing import Annotated\n"
                    "from pydantic import BaseModel, Field\n"
                    "class AuthToken(BaseModel):\n"
                    "    token: Annotated[\n"
                    "        str, Field(description='JWT token')\n"
                    "    ]\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_model_with_annotated_field_description",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel\n"
                    "class EmptyModel(BaseModel):\n"
                    "    '''An empty model without fields.'''\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_empty_model",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from typing import ClassVar\n"
                    "from pydantic import BaseModel, Field\n"
                    "class SecretModel(BaseModel):\n"
                    "    PUBLIC_MAX: ClassVar[int] = 100\n"
                    "    _cached_value: str = 'cache'\n"
                    "    id: int = Field(..., description='ID record')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_model_with_classvar_and_private_attr",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel, ConfigDict, Field\n"
                    "class ConfiguredModel(BaseModel):\n"
                    "    model_config = ConfigDict(populate_by_name=True)\n"
                    "    name: str = Field(..., description='User name')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_model_with_model_config",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel, Field\n"
                    "class ParentModel(BaseModel):\n"
                    "    parent_id: int = Field(\n"
                    "        ..., description='Parent ID'\n"
                    "    )\n"
                    "class ChildModel(ParentModel):\n"
                    "    child_id: int = Field(..., description='Child ID')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_inherited_models",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel\n"
                    "class BrokenModel(BaseModel):\n"
                    "    missing_field: str\n"
                ),
            ),
            LinterExpected(
                is_valid=False,
                violations_count=1,
                first_violating_field="missing_field",
                error_code="BM001",
            ),
            id="invalid_model_missing_field_call",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel, Field\n"
                    "class BrokenFieldModel(BaseModel):\n"
                    "    field_without_desc: int = Field(default=42)\n"
                ),
            ),
            LinterExpected(
                is_valid=False,
                violations_count=1,
                first_violating_field="field_without_desc",
                error_code="BM001",
            ),
            id="invalid_model_field_call_without_description",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from pydantic import BaseModel, Field\n"
                    "class BlankDescModel(BaseModel):\n"
                    "    blank_desc: str = Field(..., description='   ')\n"
                ),
            ),
            LinterExpected(
                is_valid=False,
                violations_count=1,
                first_violating_field="blank_desc",
                error_code="BM001",
            ),
            id="invalid_model_field_blank_description",
        ),
    ],
)
def test_basemodel_descriptions_snippets(
    tmp_path: Path,
    entity: LinterSnippetEntity,
    expected: LinterExpected,
) -> None:
    # Arrange
    temp_file = tmp_path / "snippet.py"
    temp_file.write_text(entity.code, encoding="utf-8")

    # Act
    violations = check_file(temp_file)

    # Assert
    assert (len(violations) == 0) == expected.is_valid, (
        f"Expected validity {expected.is_valid}, got {len(violations)} "
        f"violations: {[v.format() for v in violations]}"
    )
    assert len(violations) == expected.violations_count, (
        f"Expected {expected.violations_count} violations, "
        f"got {len(violations)}"
    )
    if expected.first_violating_field is not None:
        assert violations[0].field_name == expected.first_violating_field, (
            f"Expected violating field {expected.first_violating_field}, "
            f"got {violations[0].field_name}"
        )
    if expected.error_code is not None:
        assert violations[0].code == expected.error_code, (
            f"Expected error code {expected.error_code}, "
            f"got {violations[0].code}"
        )


def test_basemodel_run_checks_syntax_error(tmp_path: Path) -> None:
    # Arrange
    broken_file = tmp_path / "syntax_error.py"
    broken_file.write_text("def broken_syntax(:\n", encoding="utf-8")

    # Act
    violations = run_checks([str(broken_file)])

    # Assert
    assert len(violations) == 1, (
        f"Expected 1 violation for syntax error, got {len(violations)}"
    )
    assert violations[0].code == "BM000", (
        f"Expected code BM000 for syntax error, got {violations[0].code}"
    )

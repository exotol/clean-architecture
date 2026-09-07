"""Unit tests for check_dataclass_descriptions linter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts.check_dataclass_descriptions import check_file
from scripts.check_dataclass_descriptions import run_checks

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
                    "from dataclasses import dataclass, field\n"
                    "@dataclass\n"
                    "class Item:\n"
                    "    name: str = field(\n"
                    "        metadata={'description': 'Item name'}\n"
                    "    )\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_field_metadata",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass\n"
                    "from pydantic import Field\n"
                    "@dataclass\n"
                    "class ConfigItem:\n"
                    "    timeout: float = Field(description='Timeout value')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_field_call_description",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass, field\n"
                    "@dataclass\n"
                    "class Document:\n"
                    "    content: str = field(doc='Document content')\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_doc_arg",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass\n"
                    "from typing import Annotated\n"
                    "@dataclass\n"
                    "class User:\n"
                    "    user_id: Annotated[int, 'User identifier']\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_annotated_description",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass\n"
                    "@dataclass\n"
                    "class Product:\n"
                    "    sku: str\n"
                    "    '''Unique SKU code of the product.'''\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_attribute_docstring",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass\n"
                    "@dataclass\n"
                    "class Order:\n"
                    "    '''Order information.\n\n"
                    "    Attributes:\n"
                    "        order_id: Unique order identifier.\n"
                    "    '''\n"
                    "    order_id: int\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_class_docstring_attributes",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass, KW_ONLY\n"
                    "from typing import ClassVar\n"
                    "@dataclass\n"
                    "class Special:\n"
                    "    GLOBAL_ID: ClassVar[int] = 1\n"
                    "    _: KW_ONLY\n"
                    "    _secret: str = 'hidden'\n"
                    "    public_id: int\n"
                    "    '''Public identifier.'''\n"
                ),
            ),
            LinterExpected(is_valid=True, violations_count=0),
            id="valid_dataclass_with_kw_only_and_classvar",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass\n"
                    "@dataclass\n"
                    "class BrokenDataclass:\n"
                    "    missing_desc_field: str\n"
                ),
            ),
            LinterExpected(
                is_valid=False,
                violations_count=1,
                first_violating_field="missing_desc_field",
                error_code="DC001",
            ),
            id="invalid_dataclass_missing_all_descriptions",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass, field\n"
                    "@dataclass\n"
                    "class BadMetaDataclass:\n"
                    "    item_val: int = field(metadata={'author': 'admin'})\n"
                ),
            ),
            LinterExpected(
                is_valid=False,
                violations_count=1,
                first_violating_field="item_val",
                error_code="DC001",
            ),
            id="invalid_dataclass_metadata_without_description_key",
        ),
        pytest.param(
            LinterSnippetEntity(
                code=(
                    "from dataclasses import dataclass, field\n"
                    "@dataclass\n"
                    "class BlankDescDataclass:\n"
                    "    blank_meta: str = field(\n"
                    "        metadata={'description': '   '}\n"
                    "    )\n"
                ),
            ),
            LinterExpected(
                is_valid=False,
                violations_count=1,
                first_violating_field="blank_meta",
                error_code="DC001",
            ),
            id="invalid_dataclass_empty_metadata_description",
        ),
    ],
)
def test_dataclass_descriptions_snippets(
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


def test_dataclass_run_checks_syntax_error(tmp_path: Path) -> None:
    # Arrange
    broken_file = tmp_path / "syntax_error.py"
    broken_file.write_text(
        "class BrokenDataclass:\n  @dataclass\n",
        encoding="utf-8",
    )

    # Act
    violations = run_checks([str(broken_file)])

    # Assert
    assert len(violations) == 1, (
        f"Expected 1 violation for syntax error, got {len(violations)}"
    )
    assert violations[0].code == "DC000", (
        f"Expected code DC000 for syntax error, got {violations[0].code}"
    )

"""Unit tests for linter_utils AST helper functions."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest
from scripts.linter_utils import Violation
from scripts.linter_utils import has_annotated_description
from scripts.linter_utils import has_dataclass_field_metadata_description
from scripts.linter_utils import has_field_call_description
from scripts.linter_utils import is_class_var
from scripts.linter_utils import is_kw_only
from scripts.linter_utils import is_non_empty_str
from scripts.linter_utils import iter_python_files
from scripts.linter_utils import parse_docstring_attributes

from tests.schemas.unit.utils.descriptions_linter import LinterExpected
from tests.schemas.unit.utils.descriptions_linter import LinterSnippetEntity


if TYPE_CHECKING:
    from pathlib import Path


def test_violation_format() -> None:
    # Arrange
    violation = Violation(
        file_path="src/model.py",
        line=10,
        col=4,
        class_name="User",
        field_name="name",
        code="BM001",
        message="Missing description",
    )

    # Act
    formatted = violation.format()

    # Assert
    expected_msg = (
        "src/model.py:10:4: [BM001] "
        "Field 'name' in class 'User': Missing description"
    )
    assert formatted == expected_msg, (
        f"Unexpected formatted string: {formatted}"
    )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LinterSnippetEntity(code="ClassVar[int]"),
            LinterExpected(is_valid=True),
            id="is_class_var_simple",
        ),
        pytest.param(
            LinterSnippetEntity(code="typing.ClassVar[str]"),
            LinterExpected(is_valid=True),
            id="is_class_var_attribute",
        ),
        pytest.param(
            LinterSnippetEntity(code="int"),
            LinterExpected(is_valid=False),
            id="not_class_var",
        ),
        pytest.param(
            LinterSnippetEntity(code="KW_ONLY"),
            LinterExpected(is_valid=True),
            id="is_kw_only_simple",
        ),
        pytest.param(
            LinterSnippetEntity(code="dataclasses.KW_ONLY"),
            LinterExpected(is_valid=True),
            id="is_kw_only_attribute",
        ),
        pytest.param(
            LinterSnippetEntity(code="str"),
            LinterExpected(is_valid=False),
            id="not_kw_only",
        ),
        pytest.param(
            LinterSnippetEntity(code="'non empty text'"),
            LinterExpected(is_valid=True),
            id="is_non_empty_str_valid",
        ),
        pytest.param(
            LinterSnippetEntity(code="''"),
            LinterExpected(is_valid=False),
            id="is_non_empty_str_empty",
        ),
        pytest.param(
            LinterSnippetEntity(code="'prefix ' + 'suffix'"),
            LinterExpected(is_valid=True),
            id="is_non_empty_str_binop",
        ),
    ],
)
def test_linter_utils_expression_helpers(
    entity: LinterSnippetEntity,
    expected: LinterExpected,
) -> None:
    # Arrange
    expr_node = ast.parse(entity.code, mode="eval").body

    # Act
    if "ClassVar" in entity.code or entity.code == "int":
        result = is_class_var(expr_node)
    elif "KW_ONLY" in entity.code or entity.code == "str":
        result = is_kw_only(expr_node)
    else:
        result = is_non_empty_str(expr_node)

    # Assert
    assert result == expected.is_valid, (
        f"Expected is_valid={expected.is_valid}, got {result}"
    )


def test_parse_docstring_attributes_extraction() -> None:
    # Arrange
    docstring = """Component description.

    Attributes:
        first_attr: First attribute description.
        second_attr (int): Second attribute with type.
        third_attr: Third attribute.
    """

    # Act
    attributes = parse_docstring_attributes(docstring)

    # Assert
    assert attributes == {"first_attr", "second_attr", "third_attr"}, (
        f"Attributes parsed incorrectly: {attributes}"
    )


def test_parse_docstring_attributes_empty() -> None:
    # Arrange
    empty_doc = None

    # Act
    attributes = parse_docstring_attributes(empty_doc)

    # Assert
    assert attributes == set(), f"Expected empty set, got {attributes}"


def test_has_field_call_description_helpers() -> None:
    # Arrange
    valid_call = ast.parse("Field(..., description='desc')", mode="eval").body
    invalid_call = ast.parse("Field(default=1)", mode="eval").body
    not_call = ast.parse("42", mode="eval").body

    # Act
    res_valid = has_field_call_description(valid_call)
    res_invalid = has_field_call_description(invalid_call)
    res_not_call = has_field_call_description(not_call)

    # Assert
    assert res_valid, "Expected valid field call to return True"
    assert not res_invalid, "Expected call without description to return False"
    assert not res_not_call, "Expected non-call node to return False"


def test_has_annotated_description_helpers() -> None:
    # Arrange
    valid_annotated = ast.parse(
        "Annotated[int, Field(description='desc')]",
        mode="eval",
    ).body
    valid_text_annotated = ast.parse(
        "Annotated[str, 'simple description']",
        mode="eval",
    ).body
    invalid_annotated = ast.parse("Annotated[int, '']", mode="eval").body

    # Act
    res_valid = has_annotated_description(valid_annotated)
    res_text = has_annotated_description(valid_text_annotated)
    res_invalid = has_annotated_description(invalid_annotated)

    # Assert
    assert res_valid, "Expected Annotated with Field to return True"
    assert res_text, "Expected Annotated with text to return True"
    assert not res_invalid, (
        "Expected Annotated with empty text to return False"
    )


def test_has_dataclass_field_metadata_description_helpers() -> None:
    # Arrange
    valid_meta = ast.parse(
        "field(metadata={'description': 'Item desc'})",
        mode="eval",
    ).body
    valid_doc = ast.parse("field(doc='Doc string')", mode="eval").body
    bad_meta = ast.parse("field(metadata={'foo': 'bar'})", mode="eval").body

    # Act
    res_valid = has_dataclass_field_metadata_description(valid_meta)
    res_doc = has_dataclass_field_metadata_description(valid_doc)
    res_bad = has_dataclass_field_metadata_description(bad_meta)

    # Assert
    assert res_valid, "Expected valid metadata to return True"
    assert res_doc, "Expected doc argument to return True"
    assert not res_bad, "Expected metadata without description to return False"


def test_iter_python_files_filtering(tmp_path: Path) -> None:
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    file_src = src_dir / "app.py"
    file_src.write_text("x = 1\n", encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    file_test = tests_dir / "test_app.py"
    file_test.write_text("assert True\n", encoding="utf-8")

    # Act
    files_no_tests = iter_python_files([str(tmp_path)], include_tests=False)
    files_with_tests = iter_python_files([str(tmp_path)], include_tests=True)

    # Assert
    assert file_src in files_no_tests, "Expected app.py in files_no_tests"
    assert file_test not in files_no_tests, (
        "Expected test_app.py excluded from files_no_tests"
    )
    assert file_test in files_with_tests, (
        "Expected test_app.py in files_with_tests"
    )

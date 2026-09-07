"""Unit tests for commit message validation script."""

from __future__ import annotations

import pytest
from scripts.validate_commit_message_ru import validate_commit_message

from tests.schemas.unit.utils.commit_message import CommitValidationEntity
from tests.schemas.unit.utils.commit_message import CommitValidationExpected


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            CommitValidationEntity(
                message="feat(api): добавить новый эндпоинт поиска",
            ),
            CommitValidationExpected(is_valid=True),
            id="valid_concise_feature_commit",
        ),
        pytest.param(
            CommitValidationEntity(
                message=(
                    "docs(commits): зафиксировать правило длины "
                    "сообщений коммитов не более двадцати слов для "
                    "всех участников команды разработки проекта"
                ),
            ),
            CommitValidationExpected(is_valid=True),
            id="valid_exact_20_words_commit",
        ),
        pytest.param(
            CommitValidationEntity(
                message=(
                    "feat(api): изменить ответ\n\n"
                    "BREAKING CHANGE: изменение формата"
                ),
            ),
            CommitValidationExpected(is_valid=True),
            id="valid_with_breaking_change_marker",
        ),
        pytest.param(
            CommitValidationEntity(
                message="   \n\n# git comment\n  ",
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="не может быть пустым",
            ),
            id="invalid_empty_or_comments_only",
        ),
        pytest.param(
            CommitValidationEntity(
                message=(
                    "feat(api): один два три четыре пять шесть семь восемь "
                    "девять десять одиннадцать двенадцать тринадцать "
                    "четырнадцать пятнадцать шестнадцать семнадцать "
                    "восемнадцать девятнадцать двадцать"
                ),
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="максимум допускается 20 слов",
            ),
            id="invalid_exceeds_20_words",
        ),
        pytest.param(
            CommitValidationEntity(
                message="произвольный коммит без типа Conventional Commits",
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="Conventional Commits",
            ),
            id="invalid_missing_conventional_prefix",
        ),
        pytest.param(
            CommitValidationEntity(
                message="custom(api): неподдерживаемый тип коммита",
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="Conventional Commits",
            ),
            id="invalid_disallowed_type",
        ),
        pytest.param(
            CommitValidationEntity(
                message="fix(core): english description in commit",
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="русский текст",
            ),
            id="invalid_latin_only_description",
        ),
        pytest.param(
            CommitValidationEntity(
                message="fix(core): русский заголовок с english словом",
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="только на русском",
            ),
            id="invalid_mixed_description",
        ),
        pytest.param(
            CommitValidationEntity(
                message="fix(core): русский заголовок\n\nenglish body line",
            ),
            CommitValidationExpected(
                is_valid=False,
                error_message_substring="только на русском",
            ),
            id="invalid_latin_in_body",
        ),
    ],
)
def test_validate_commit_message(
    entity: CommitValidationEntity,
    expected: CommitValidationExpected,
) -> None:
    """Test strict commit message validation under various scenarios."""
    # Arrange
    caught_exception: ValueError | None = None

    # Act
    try:
        validate_commit_message(entity.message)
    except ValueError as exc:
        caught_exception = exc

    # Assert
    if expected.is_valid:
        assert caught_exception is None, (
            f"Expected commit message to be valid, but got: {caught_exception}"
        )
    else:
        assert caught_exception is not None, (
            f"Expected ValueError for message {entity.message!r}, "
            f"but validation passed"
        )
        if expected.error_message_substring:
            assert expected.error_message_substring in str(caught_exception), (
                f"Expected substring {expected.error_message_substring!r} "
                f"in error message, got {str(caught_exception)!r}"
            )

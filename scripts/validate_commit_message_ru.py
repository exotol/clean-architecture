from __future__ import annotations

from pathlib import Path
import re
import sys


MAX_COMMIT_WORDS = 20

ALLOWED_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

FIRST_LINE_RE = re.compile(
    r"^(?P<type>" + "|".join(ALLOWED_TYPES) + r")"
    r"(?P<context>\([^)]*\))?"
    r":\s*(?P<desc>.+?)\s*$",
)


MIN_PATH_ARGS = 1
MIN_MESSAGE_ARGS = 2


def read_commit_message() -> str:
    """Read the commit message from arguments, file or stdin."""
    if len(sys.argv) > MIN_MESSAGE_ARGS and sys.argv[1] in {"-m", "--message"}:
        return sys.argv[2]

    if len(sys.argv) > MIN_PATH_ARGS and not sys.argv[1].startswith("-"):
        path = Path(sys.argv[1])
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")

    commit_editmsg = Path(".git") / "COMMIT_EDITMSG"
    if commit_editmsg.exists():
        return commit_editmsg.read_text(encoding="utf-8", errors="replace")

    return sys.stdin.read()


def extract_non_comment_words(message: str) -> list[str]:
    """Extract list of words excluding git comments and empty lines."""
    words: list[str] = []
    for line in message.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        words.extend(stripped.split())
    return words


def contains_latin_letters(text: str) -> bool:
    """Check if text contains latin letters."""
    return bool(re.search(r"[A-Za-z]", text))


def validate_word_count(words: list[str]) -> None:
    """Validate that total words do not exceed maximum limit."""
    word_count = len(words)
    if word_count == 0:
        raise ValueError("Сообщение коммита не может быть пустым.")
    if word_count > MAX_COMMIT_WORDS:
        raise ValueError(
            f"Сообщение коммита содержит {word_count} слов "
            f"(максимум допускается {MAX_COMMIT_WORDS} слов). "
            "Огромные тексты запрещены.",
        )


def validate_description_is_russian(desc: str) -> None:
    """Validate that description contains Cyrillic and no Latin letters."""
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", desc))
    if not has_cyrillic:
        raise ValueError("Описание коммита должно содержать русский текст.")
    if contains_latin_letters(desc):
        raise ValueError(
            "Описание коммита должно быть только на русском (без латиницы).",
        )


def validate_body_has_no_latin(message: str) -> None:
    """Validate body has no Latin letters except BREAKING CHANGE:."""
    for line in message.splitlines()[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("BREAKING CHANGE:"):
            continue
        if contains_latin_letters(stripped):
            raise ValueError(
                "Тело коммита должно быть только на русском (без латиницы).",
            )


def validate_commit_message(message: str) -> None:
    """Strict validation of commit message."""
    words = extract_non_comment_words(message)
    validate_word_count(words)

    lines = [
        ln.strip()
        for ln in message.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    first_non_empty = lines[0] if lines else ""

    m = FIRST_LINE_RE.match(first_non_empty)
    if not m:
        allowed = ", ".join(ALLOWED_TYPES)
        raise ValueError(
            "Сообщение коммита должно соответствовать Conventional Commits: "
            f"<тип>[(контекст)]: <описание>. Допустимые типы: {allowed}.",
        )

    desc = m.group("desc")
    validate_description_is_russian(desc)
    validate_body_has_no_latin(message)


def main() -> None:
    """Main entrypoint for commit-msg hook."""
    message = read_commit_message().replace("\r\n", "\n")
    validate_commit_message(message)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.stderr.write(f"ОШИБКА: {exc}\n")
        sys.exit(1)

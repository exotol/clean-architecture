from __future__ import annotations

from pathlib import Path
import re
import sys


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
    r"^(?P<type>"
    + "|".join(ALLOWED_TYPES)
    + r")"
    r"(?P<context>\([^)]*\))?"
    r":\s*(?P<desc>.+?)\s*$",
)


def _read_commit_message() -> str:
    """Read the commit message for commit-msg hooks.

    pre-commit usually passes a filename; as a fallback we try
    .git/COMMIT_EDITMSG and then stdin.
    """
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")

    # Fallback for environments where the hook doesn't pass a filename.
    commit_editmsg = Path(".git") / "COMMIT_EDITMSG"
    if commit_editmsg.exists():
        return commit_editmsg.read_text(encoding="utf-8", errors="replace")

    return sys.stdin.read()


def _contains_latin_letters(text: str) -> bool:
    # Latin letters only (A-Z / a-z). We intentionally allow those in prefix
    # types (feat/fix/...), which we remove before checking.
    return bool(re.search(r"[A-Za-z]", text))


def _validate_description_is_russian(desc: str) -> None:
    # Must contain at least one Cyrillic character.
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", desc))
    if not has_cyrillic:
        raise ValueError("Описание коммита должно содержать русский текст.")
    if _contains_latin_letters(desc):
        raise ValueError(
            "Описание коммита должно быть только на русском (без латиницы).",
        )


def _validate_body_has_no_latin(message: str) -> None:
    # Conventional Commits footer may include BREAKING CHANGE: (in english).
    # We keep the check strict only for lines other than that footer marker.
    for line in message.splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("BREAKING CHANGE:"):
            continue
        if _contains_latin_letters(stripped):
            raise ValueError(
                "Тело/комментарии коммита должны быть только на русском.",
            )


def main() -> None:
    """Validate commit message language for Conventional Commits."""
    message = _read_commit_message().replace("\r\n", "\n")
    lines = message.splitlines()

    # pre-commit/commit-msg can still pass empty messages in edge cases.
    first_non_empty = next(
        (ln for ln in lines if ln.strip()),
        "",
    )
    m = FIRST_LINE_RE.match(first_non_empty)
    if not m:
        # Let conventional-commits hook handle formatting; we only enforce
        # language.
        # Still, if it can't be parsed, do not block here.
        return

    desc = m.group("desc")
    _validate_description_is_russian(desc)
    _validate_body_has_no_latin(message)

    # For debugging in CI logs, keep output minimal.
    sys.exit(0)


if __name__ == "__main__":
    # Ensure hook never writes to stdout/stderr on success.
    try:
        main()
    except ValueError:
        # Print a short message for the developer.
        sys.exit(1)

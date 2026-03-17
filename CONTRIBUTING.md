# Contributing to EVA

## Principles

- **Do not break the system**: every change must keep the project runnable and testable.
- **LEAN**: smallest possible change that solves the task; avoid “bonus refactors”.
- **No mutable globals**: state through DI (`app.core.containers`, FastAPI `Depends()`), constants only in `app.core.constants`.
- **No suppression of checks**: `# noqa` and `# type: ignore` are **forbidden** in code; fix the code instead. Do not add new ignore rules in `pyproject.toml`; every issue must be **solved**, not suppressed.

## Local setup

```bash
uv sync
```

## Quality gate (Definition of Done)

Before opening a PR, you must pass:

```bash
make check
```

This runs:
- Ruff lint (`make ruff.check`)
- mypy strict (`make mypy.check`)
- unit tests + coverage threshold (`make run.unit.cov`, fail-under 95%)

Optional, but recommended:

```bash
make run.pytest
```

## Pre-commit hooks

Install:

```bash
make install.pre-commit
```

Run on all files (optional):

```bash
uv run pre-commit run --all-files
```

## Testing rules

- **Unit tests**: `tests/unit/` (no real external services).
- **Integration/E2E**: add when behavior crosses boundaries (API, persistence, external services).
- **Data-driven**: prefer `tests/schemas/` + `@pytest.mark.parametrize(..., id=...)`.

See `docs/testing.md` for structure and examples.

## Architecture rules

The project follows **Clean Architecture**.

- Domain: `src/app/domain/` (no infra dependencies)
- Application: `src/app/application/` (use-cases)
- Infrastructure: `src/app/infrastructure/` (external world, implementations)
- Presentation: `src/app/presentation/` (FastAPI endpoints, schemas)

See `docs/architecture.md` and `docs/structure.md`.


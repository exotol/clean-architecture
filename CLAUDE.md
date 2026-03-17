# EVA — агенту (Claude Code / Codex / Cursor)

## Goal

**Never break the system.** Make the smallest safe change that solves the task, fully validated by lint/type/tests.

## Mandatory commands

Run this before saying “done”:

```bash
make check
```

If the change touches public API behavior, also run:

```bash
make run.pytest
```

## Non-negotiables

- **No mutable globals** (no module-level state; no `global` writes). Use DI only.
- **Tests required** for new/changed behavior; keep coverage ≥95%.
- **Ruff + mypy strict** must pass. **No suppression:** `# noqa` and `# type: ignore` are **forbidden** in code; fix the underlying issue instead. Do not add new ignore rules in `pyproject.toml`; solve problems in code.
- **No “drive-by refactors”** (LEAN).
- **No secrets in repo**. Use Dynaconf configs and examples only.

## Where to look

- Rules: `AGENTS.md` (full), `.cursor/rules/` (Cursor)
- Architecture: `docs/architecture.md`, `docs/structure.md`
- Testing: `docs/testing.md`
- Commits: `docs/commits.md` (Conventional Commits)
- Tooling: `pyproject.toml`, `Makefile`


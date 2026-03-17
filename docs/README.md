# EVA Project Documentation

Comprehensive documentation for the EVA project - a Clean Architecture Python application template.

## Non-negotiables (for everyone, including agents)

- **Do not suppress checks in code**: `# noqa`, `# type: ignore`, and similar directives are not allowed.
- **Do not add ignore rules to `pyproject.toml` on your own** (for example `extend-per-file-ignores`, `ignore`, etc.).
- **Fix problems, don’t hide them** by suppressing lint/type checks.

## Table of Contents

| Document | Description |
|----------|-------------|
| [Concept](concept.md) | Project philosophy and Clean Architecture principles |
| [Architecture](architecture.md) | Detailed architectural overview and layer descriptions |
| [Project Structure](structure.md) | Directory layout and file organization |
| [Testing](testing.md) | Test structure, approach, and execution |
| [Profiling](profiling.md) | Performance profiling and optimization tools |
| [Docker](docker.md) | Docker build, optimizations, and deployment |
| [Makefile Commands](makefile.md) | All available automation commands |
| [Configuration](configuration.md) | Settings and environment configuration |
| [Commits](commits.md) | Conventional Commits standard and examples |

## Quick Start

```bash
# Install dependencies
uv sync

# Run the application
python src/app/main.py

# Run tests
make run.pytest
```

## License

See [LICENSE](../LICENSE) for details.

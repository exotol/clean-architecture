from __future__ import annotations

from app.domain.interfaces.readiness import IReadinessChecker


class DefaultReadinessChecker(IReadinessChecker):
    """Default readiness: always ready.

    Can be replaced with a checker that pings DB, search backend, etc.
    """

    async def is_ready(self) -> bool:
        """Return True (no dependency checks for now)."""
        _ = self  # Reserve for future dependency checks
        return True

from __future__ import annotations

import cProfile
from datetime import datetime
import io
import logging
from pathlib import Path
import pstats
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint


if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request
    from starlette.responses import Response

    from app.utils.configs import ProfilingConfig

logger = logging.getLogger(__name__)


class ProfilingMiddleware(BaseHTTPMiddleware):
    """Middleware that profiles each request using cProfile.

    Saves profile stats to files and logs top functions.
    """

    def __init__(self, app: FastAPI, config: ProfilingConfig) -> None:
        super().__init__(app)
        self.config = config
        self._ensure_output_dir()
        logger.info(
            "Profiling enabled. Profiles will be saved to: %s",
            config.output_dir,
        )

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Profile the request and save stats."""
        if not self.config.enabled:
            return await call_next(request)

        profiler = cProfile.Profile()
        profiler.enable()

        try:
            response = await call_next(request)
        finally:
            profiler.disable()

        # Generate stats
        self._log_stats(profiler, request)
        self._save_stats(profiler, request)

        return response

    def _log_stats(self, profiler: cProfile.Profile, request: Request) -> None:
        """Log top functions to console."""
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats(self.config.sort_by)
        stats.print_stats(self.config.top_n)

        logger.info(
            "Profile for %s %s:\n%s",
            request.method,
            request.url.path,
            stream.getvalue(),
        )

    def _save_stats(
        self,
        profiler: cProfile.Profile,
        request: Request,
    ) -> None:
        """Save profile stats to file."""
        timestamp = datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S_%f")
        path_safe = request.url.path.replace("/", "_").strip("_") or "root"
        filename = f"{timestamp}_{request.method}_{path_safe}.prof"
        filepath = Path(self.config.output_dir) / filename

        profiler.dump_stats(str(filepath))
        logger.debug("Profile saved to %s", filepath)

"""cProfile middleware for FastAPI."""
from __future__ import annotations

import cProfile
import io
import pstats
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.utils.configs import ProfilingConfig


class ProfilingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that profiles each request using cProfile.
    
    Saves profile stats to files and logs top functions.
    """

    def __init__(self, app: FastAPI, config: ProfilingConfig) -> None:
        super().__init__(app)
        self.config = config
        self._ensure_output_dir()
        logger.info(
            "Profiling enabled. Profiles will be saved to: {output}".format(
                output=config.output_dir
            )
        )

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
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

    def _save_stats(self, profiler: cProfile.Profile, request: Request) -> None:
        """Save profile stats to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path_safe = request.url.path.replace("/", "_").strip("_") or "root"
        filename = f"{timestamp}_{request.method}_{path_safe}.prof"
        filepath = Path(self.config.output_dir) / filename

        profiler.dump_stats(str(filepath))
        logger.debug("Profile saved to %s", filepath)



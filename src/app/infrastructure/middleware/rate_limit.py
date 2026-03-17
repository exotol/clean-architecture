from __future__ import annotations

import asyncio
from collections import defaultdict
import logging
import time
from typing import TYPE_CHECKING
from typing import Any
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.constants import TRACE_ID
from app.core.exceptions import ProblemDetail
from app.core.exceptions import Reasons


if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

    from app.utils.configs import RateLimitConfig

logger = logging.getLogger(__name__)


class RateLimitStore:
    """In-memory sliding-window store for rate limiting.

    State is held in instance (injected via DI), not module-level.
    """

    def __init__(self) -> None:
        self._key_timestamps: defaultdict[str, list[float]] = defaultdict(list)
        self._lock: asyncio.Lock = asyncio.Lock()

    async def check_and_record(
        self,
        key: str,
        limit: int,
        window_seconds: float,
    ) -> tuple[bool, float]:
        """Check if key is under limit and record the request.

        Returns:
            (allowed, retry_after_seconds).
            retry_after_seconds is 0 if allowed.
        """
        now = time.monotonic()
        async with self._lock:
            timestamps = self._key_timestamps[key]
            cutoff = now - window_seconds
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= limit:
                oldest = min(timestamps) if timestamps else now
                retry_after = max(0.0, oldest + window_seconds - now)
                return False, retry_after
            timestamps.append(now)
            return True, 0.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limit per client key (IP or header)."""

    def __init__(
        self,
        app: Any,
        config: RateLimitConfig,
        store: RateLimitStore,
    ) -> None:
        super().__init__(app)
        self._config = config
        self._store = store

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Enforce rate limit and pass through or return 429."""
        if not self._config.enabled:
            return await call_next(request)

        key = self._get_client_key(request)
        allowed, retry_after = await self._store.check_and_record(
            key,
            limit=self._config.requests_per_window,
            window_seconds=self._config.window_seconds,
        )
        if not allowed:
            return self._rate_limit_response(request, retry_after)
        return await call_next(request)

    def _get_client_key(self, request: Request) -> str:
        """Derive client key from header or IP."""
        if self._config.key_header:
            value = request.headers.get(self._config.key_header)
            if value:
                return value.strip()
        client = request.client
        if client:
            return client.host or "unknown"
        return "unknown"

    @staticmethod
    def _rate_limit_response(
        request: Request,
        retry_after: float,
    ) -> JSONResponse:
        """Build 429 response with RFC 7807 body and Retry-After header."""
        return _build_rate_limit_response(request, retry_after)


def _build_rate_limit_response(
    request: Request,
    retry_after: float,
) -> JSONResponse:
    """Build 429 response with RFC 7807 body and Retry-After header."""
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID)
        or str(uuid.uuid4())
    )
    retry_after_int = max(1, int(retry_after))
    problem = ProblemDetail(
        urn_type_error=Reasons.rate_limit_exceeded.urn_type_error,
        title=Reasons.rate_limit_exceeded.title,
        status=429,
        reason=Reasons.rate_limit_exceeded.code,
        detail=Reasons.rate_limit_exceeded.message,
        instance=request.url.path,
        trace_id=trace_id,
        invalid_params=None,
    )
    return JSONResponse(
        status_code=429,
        content=problem.model_dump(by_alias=True, exclude_none=True),
        headers={"Retry-After": str(retry_after_int)},
    )

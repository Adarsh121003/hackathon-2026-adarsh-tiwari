"""FastAPI middleware: CORS and request correlation logging."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.config import settings

logger = logging.getLogger(__name__)


def add_cors(app) -> None:
    """Attach CORS middleware with configured origins."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with duration and correlation ID."""

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())[:8]
        start = time.monotonic()
        logger.info("→ %s %s [%s]", request.method, request.url.path, req_id)
        response = await call_next(request)
        ms = (time.monotonic() - start) * 1000
        logger.info(
            "← %s %s [%s] %dms",
            request.method,
            request.url.path,
            req_id,
            int(ms),
        )
        response.headers["X-Request-ID"] = req_id
        return response

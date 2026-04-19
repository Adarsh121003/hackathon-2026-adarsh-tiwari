"""FastAPI application factory for Sentinel.

Startup sequence:
  1. setup_logging()
  2. settings.validate()  — fail fast if env is misconfigured
  3. datastore.load()     — parse all fixture JSON files
  4. build KB index       — TF-IDF over knowledge base
  5. init_db()            — create SQLite tables
  6. mount routes + SSE stream + middleware
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from backend.api.middleware import RequestLoggingMiddleware, add_cors
from backend.api.routes import router as api_router
from backend.api.streams import router as stream_router
from backend.audit.store import init_db
from backend.core.config import settings
from backend.core.logging_setup import setup_logging
from backend.tools import datastore as ds_module
from backend.tools import kb_search

setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sentinel — Autonomous Support Agent",
        description="ShopWave support ticket resolution via LLM-driven ReAct loop",
        version="1.0.0",
    )

    add_cors(app)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(api_router)
    app.include_router(stream_router, prefix="/api")

    @app.on_event("startup")
    async def startup():
        settings.validate()
        ds_module.store.load()
        kb_search.build_index(ds_module.store.kb_text)
        await init_db()
        logger.info(
            "Sentinel started: provider=%s model=%s",
            settings.llm_provider,
            settings.groq_model if settings.llm_provider == "groq" else settings.anthropic_model,
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )

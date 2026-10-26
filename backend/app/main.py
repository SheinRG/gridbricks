import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as v1_router
from app.config import Settings, get_settings
from app.data_store import get_store
from app.logging import configure_logging

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Load data at startup so the first request is not slow; /health reports failures.
        try:
            get_store()
        except FileNotFoundError:
            logger.exception("data not loaded at startup")
        yield

    app = FastAPI(
        title="UK Wind Forecast Monitor",
        version="0.1.0",
        description="Day-ahead wind forecast vs actual generation for GB, January 2026.",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        # Historical data never changes, so successful data responses can be cached (CDN too).
        path = request.url.path
        if response.status_code == 200 and path.startswith("/api/v1/") and path != "/api/v1/health":
            response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=86400"
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status": response.status_code,
                "duration_ms": round(elapsed_ms, 1),
            },
        )
        return response

    app.include_router(v1_router, prefix="/api/v1")

    # Production image: serve the built SPA from the same origin as the API.
    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="spa")

    return app


app = create_app()

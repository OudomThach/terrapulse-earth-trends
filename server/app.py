"""FastAPI application factory: routers, compression, timing headers, error mapping and the built web app."""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from terrapulse import __version__
from terrapulse.climate import FIRST_YEAR, LAST_YEAR, PLACES, ClimateDataError
from terrapulse.config import ROOT
from terrapulse.questions import QUESTIONS
from terrapulse.variables import GROUPS, VARIABLES

from . import proposal, routes_risk, routes_trends
from .serialize import place_dict, question_dict, variable_dict

WEB_DIST = Path(os.environ.get("TERRAPULSE_WEB", ROOT / "web" / "dist"))


def create_app() -> FastAPI:
    """Build the application. Used by uvicorn (``--factory``) and by the tests."""
    app = FastAPI(title="TerraPulse API", version=__version__,
                  description="Trend Detective and Risk Lab: trends, forecasts and wildfire simulation.")
    app.add_middleware(GZipMiddleware, minimum_size=800)

    @app.middleware("http")
    async def timing(request: Request, call_next):
        """Report how long each request took, so the interface can show real latency."""
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - t0) * 1000
        response.headers["X-Response-Time-ms"] = f"{ms:.1f}"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ClimateDataError)
    async def climate_error(_: Request, exc: ClimateDataError):
        """The record could not be loaded (offline and not cached)."""
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(ValueError)
    async def value_error(_: Request, exc: ValueError):
        """Invalid scenario or parameters that passed schema validation."""
        return JSONResponse({"detail": str(exc)}, status_code=422)

    app.include_router(routes_trends.router)
    app.include_router(routes_risk.router)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        """Liveness probe used by Docker."""
        return {"status": "ok", "version": __version__}

    @app.get("/api/meta", tags=["meta"])
    def meta() -> dict:
        """Everything the interface needs to start: places, variables, questions and project status."""
        return {
            "version": __version__, "years": {"first": FIRST_YEAR, "last": LAST_YEAR},
            "places": [place_dict(p) for p in PLACES.values()],
            "groups": GROUPS, "variables": [variable_dict(v) for v in VARIABLES.values()],
            "questions": [question_dict(q) for q in QUESTIONS],
            "feedback": proposal.FEEDBACK, "requirements": proposal.REQUIREMENTS,
        }

    _mount_web(app)
    return app


def _mount_web(app: FastAPI) -> None:
    """Serve the built single-page app (if present) with long-lived caching for hashed assets."""
    index = WEB_DIST / "index.html"
    if not index.exists():
        @app.get("/", include_in_schema=False)
        def no_web() -> JSONResponse:
            """Tell the developer how to build the front end."""
            return JSONResponse({"message": "API is running. Build the web app with 'npm run build' in web/, "
                                             "or open /docs for the API."})
        return

    class ImmutableFiles(StaticFiles):
        """Hashed build assets never change, so browsers may cache them for a year."""

        async def get_response(self, path, scope):
            """Serve the file, then mark it cacheable for a year."""
            response = await super().get_response(path, scope)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return response

    app.mount("/assets", ImmutableFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Static files at the root (favicon, ...) or the app shell for client-side routes."""
        candidate = (WEB_DIST / path).resolve()
        if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

"""FastAPI service and optional locally built React application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.analysis import Runtime, router as analysis_router
from backend.routes import router
from backend.quality import router as quality_router, load_quality
from backend.services import load_health
from backend.silver import load_silver, router as silver_router
from src.pipeline import active_output

ROOT = Path(__file__).resolve().parents[1]


def create_app(outputs: Path = ROOT / "outputs", dist: Path = ROOT / "frontend" / "dist") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        active = active_output(outputs)
        app.state.outputs = active
        app.state.output_root = outputs
        app.state.health = load_health(active)
        app.state.quality, app.state.quality_error = load_quality(active, app.state.health.snapshot_id)
        app.state.silver, app.state.silver_error = load_silver(active, app.state.health.snapshot_id)
        app.state.analysis = Runtime(outputs)
        yield

    app = FastAPI(title="GreenOps Copilot", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    app.include_router(quality_router)
    app.include_router(silver_router)
    app.include_router(analysis_router)

    # Guard the API namespace before the frontend; typos must never return HTML.
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def missing_api(path: str):
        raise HTTPException(404, detail={"code": "not_found", "message": "Unknown API route"})

    if (dist / "index.html").is_file():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def home(request: Request):
            query = request.url.query
            return RedirectResponse(f"/dashboard?{query}" if query else "/dashboard")

        @app.get("/dashboard", include_in_schema=False)
        @app.get("/data-explorer", include_in_schema=False)
        @app.get("/analysis", include_in_schema=False)
        def frontend():
            return FileResponse(dist / "index.html")

    return app


app = create_app()

"""FastAPI service and optional locally built React application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routes import router
from backend.quality import router as quality_router, load_quality
from backend.services import load_health

ROOT = Path(__file__).resolve().parents[1]


def create_app(outputs: Path = ROOT / "outputs", dist: Path = ROOT / "frontend" / "dist") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.health = load_health(outputs)
        app.state.quality, app.state.quality_error = load_quality(outputs, app.state.health.snapshot_id)
        yield

    app = FastAPI(title="GreenOps Copilot", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    app.include_router(quality_router)

    # Guard the API namespace before the frontend; typos must never return HTML.
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def missing_api(path: str):
        raise HTTPException(404, detail={"code": "not_found", "message": "Unknown API route"})

    if (dist / "index.html").is_file():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def frontend():
            return FileResponse(dist / "index.html")

    return app


app = create_app()

import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.api.routes import router as api_router, engine
from backend.core.settings import load_settings
from backend.services.scheduler import start_alert_daemon


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    daemon_task = None
    if settings.alerts.enabled:
        daemon_task = asyncio.create_task(
            start_alert_daemon(engine, run_immediately=False)
        )
    yield
    if daemon_task and not daemon_task.done():
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Cheap Flight Finder API",
    description="Google Flights-style finder for Wizz Air and Ryanair with Open-Jaw support for BUD, DEB, and BTS",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Static files for frontend build if present
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "name": "Cheap Flight Finder API",
            "status": "running",
            "docs": "/docs",
            "info": "Frontend dist not built yet. Run frontend dev server or build frontend."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.core.config import settings

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)
app.include_router(router)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the single-page web UI (client-side routing via the URL hash)."""

    return FileResponse(WEB_DIR / "index.html")

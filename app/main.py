from fastapi import FastAPI

from app.api.router import router
from app.core.config import settings
from app.frontend import mount_frontend

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)
app.include_router(router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Registered last: the SPA catch-all must not shadow API routes.
mount_frontend(app)

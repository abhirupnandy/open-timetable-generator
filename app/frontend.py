"""Serve the built React frontend (``frontend/dist``) from FastAPI.

Static build assets are served from ``/assets``. Every other non-API GET
path returns ``index.html`` so client-side routes (``/timetable``,
``/data/rooms``, ...) work on reload. If the frontend has not been built,
``/`` explains how to build it.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

DEFAULT_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

# Paths owned by the backend; never answered with index.html.
_BACKEND_PREFIXES = ("api/", "docs", "redoc", "openapi.json", "health", "assets/")

_NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Frontend not built</title>
<body style="font-family:system-ui;max-width:40rem;margin:4rem auto;line-height:1.5">
<h1>Frontend not built</h1>
<p>Build the React app once:</p>
<pre>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</pre>
<p>or run the dev server with hot reload: <code>cd frontend &amp;&amp; npm run dev</code>
(proxies <code>/api</code> to this server) and open <a href="http://localhost:5173">localhost:5173</a>.</p>
<p>The API is available at <a href="/docs">/docs</a>.</p></body>"""


def mount_frontend(app: FastAPI, dist_dir: Path = DEFAULT_DIST) -> None:
    dist_dir = Path(dist_dir)
    index = dist_dir / "index.html"

    if (dist_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith(_BACKEND_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")

        if not index.exists():
            return HTMLResponse(_NOT_BUILT, status_code=503)

        # Top-level files from the build (favicon.svg, ...).
        candidate = (dist_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist_dir.resolve()):
            return FileResponse(candidate)

        return FileResponse(index)

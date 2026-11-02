"""Application logging: console plus a rotating file in ``<output_dir>/logs``."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(output_dir: str | Path, level: str = "INFO") -> Path:
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root = logging.getLogger("timetable")
    root.setLevel(level.upper())

    if not any(getattr(handler, "_timetable", False) for handler in root.handlers):
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        console = logging.StreamHandler()
        for handler in (file_handler, console):
            handler.setFormatter(logging.Formatter(FORMAT))
            handler._timetable = True  # type: ignore[attr-defined]
            root.addHandler(handler)
        root.propagate = False

    return log_file

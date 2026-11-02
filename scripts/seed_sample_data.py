"""Seed the development database with the sample data set.

Thin wrapper kept for backwards compatibility; the seed itself lives in
``app/db/seed.py`` (``uv run python -m app.db.seed`` works too).
"""

from app.db.seed import seed

if __name__ == "__main__":
    seed()

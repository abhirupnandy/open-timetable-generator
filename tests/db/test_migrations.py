import os
import subprocess
from pathlib import Path


def run_alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}
    return subprocess.run(
        ["alembic", "-c", str(Path("alembic.ini").resolve()), *args],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
    )


def test_alembic_upgrade_downgrade_restore(tmp_path):
    db_path = tmp_path / "migration.db"
    result = run_alembic(db_path, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    result = run_alembic(db_path, "downgrade", "-1")
    assert result.returncode == 0, result.stderr
    result = run_alembic(db_path, "upgrade", "head")
    assert result.returncode == 0, result.stderr

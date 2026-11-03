"""Command-line access to the data workbook.

uv run python -m app.data_io template timetable_template.xlsx
uv run python -m app.data_io export current_data.xlsx
uv run python -m app.data_io import filled_in.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.data_io.importer import import_workbook
from app.data_io.workbook import build_workbook, export_rows, workbook_bytes
from app.db.session import SessionLocal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.data_io")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("template", "write a blank data workbook"),
        ("export", "write the current database contents"),
        ("import", "replace all data with a filled-in workbook"),
    ):
        commands.add_parser(name, help=text).add_argument("path", type=Path)
    args = parser.parse_args(argv)

    if args.command == "template":
        args.path.write_bytes(workbook_bytes(build_workbook()))
        print(f"Template written to {args.path}")
        return 0

    with SessionLocal() as db:
        if args.command == "export":
            args.path.write_bytes(workbook_bytes(build_workbook(export_rows(db))))
            print(f"Data exported to {args.path}")
            return 0

        result = import_workbook(db, args.path.read_bytes())

    if not result.ok:
        print(
            f"Import rejected ({len(result.issues)} issue(s)); nothing was changed:",
            file=sys.stderr,
        )
        for issue in result.issues:
            print(f"  {issue}", file=sys.stderr)
        return 1

    print("Imported: " + ", ".join(f"{name} {count}" for name, count in result.counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

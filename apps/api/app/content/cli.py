"""Content commands.

  python -m app.content.cli validate [CONTENT_DIR]   check every file and cross-reference
  python -m app.content.cli import [CONTENT_DIR]     one-time import of drafted content

Course content is authored in the application. `import` exists so the drafted YAML in content/
can be brought in once; it only creates missing records and never overwrites edits made in the app.

`import` connects with MIGRATION_DATABASE_URL (table owner). CONTENT_DIR defaults to the
CONTENT_DIR environment variable, then ./content.
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401  (registers all tables, e.g. "user" for module.created_by)
from app.core.config import get_settings
from app.modules.catalog.content import ContentError, read_bundle
from app.modules.catalog.loader import import_bundle


def _root(args: list[str]) -> Path:
    return Path(args[0] if args else os.environ.get("CONTENT_DIR", "content"))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in {"validate", "import"}:
        print(__doc__)
        return 2
    command, root = args[0], _root(args[1:])

    try:
        bundle = read_bundle(root)
    except ContentError as exc:
        print(f"Content in {root} is not valid:")
        for error in exc.errors:
            print(f"  - {error}")
        return 1
    print(
        f"Content valid: {len(bundle.courses)} courses, "
        f"{sum(len(c.milestones) for c in bundle.courses.values())} milestones, "
        f"{len(bundle.tasks)} tasks, {len(bundle.rubrics)} rubrics"
    )
    if command == "validate":
        return 0

    engine = create_engine(get_settings().migration_database_url)
    try:
        with Session(engine) as db, db.begin():
            summary = import_bundle(db, bundle)
    except ContentError as exc:
        for error in exc.errors:
            print(f"  - {error}")
        return 1
    print(
        f"Imported. Created: {summary.created or 'none'}. Already present, left unchanged: {summary.skipped or 'none'}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

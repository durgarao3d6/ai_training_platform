"""Regression: the catalog models must work without the rest of the app being imported.

`python -m app.content.cli import` loads only the catalog. module.created_by references the user
table, so the identity models must be registered by the catalog itself, or every flush fails with
NoReferencedTableError. Runs in a fresh interpreter so other tests' imports cannot hide the bug.
"""

import subprocess
import sys

CODE = """
from sqlalchemy.orm import configure_mappers
from app.modules.catalog.models import Module
configure_mappers()
fk = next(iter(Module.__table__.c.created_by.foreign_keys))
assert fk.column.table.name == "user", fk.column.table.name
"""


def test_catalog_models_resolve_user_fk_in_isolation() -> None:
    result = subprocess.run(
        [sys.executable, "-c", CODE], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr

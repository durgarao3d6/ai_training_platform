"""Print dependencies from a pyproject.toml, one per line.

Usage: python python-deps.py pyproject.toml [extra]
Lets Dockerfiles install dependencies without needing the source tree (cache friendly).
"""

import sys
import tomllib

with open(sys.argv[1], "rb") as handle:
    project = tomllib.load(handle)["project"]

deps = list(project.get("dependencies", []))
if len(sys.argv) > 2:
    deps += project.get("optional-dependencies", {}).get(sys.argv[2], [])
print("\n".join(deps))

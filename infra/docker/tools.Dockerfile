# Build context: repository root.
# One image for lint, type check, content validation and client generation.
# Python tools (ruff, mypy, import-linter, pytest) and Node tools (eslint, tsc,
# openapi-typescript). Source is bind-mounted at /work by compose.
FROM python:3.12.8-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates make xz-utils \
 && curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz \
    | tar -xJ -C /usr/local --strip-components=1 --exclude=CHANGELOG.md --exclude=LICENSE --exclude=README.md \
 && rm -rf /var/lib/apt/lists/*

COPY infra/docker/python-deps.py /tmp/python-deps.py
COPY apps/api/pyproject.toml /tmp/api.toml
COPY apps/worker/pyproject.toml /tmp/worker.toml
RUN { python /tmp/python-deps.py /tmp/api.toml dev; python /tmp/python-deps.py /tmp/worker.toml dev; } \
      | sort -u > /tmp/req.txt \
 && pip install -r /tmp/req.txt \
 && pip install "jsonschema==4.23.0" "pyyaml==6.0.2" \
 && npm install -g openapi-typescript@7.4.4

WORKDIR /work

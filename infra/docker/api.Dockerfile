# Build context: repository root.  Targets: dev, prod
FROM python:3.12.8-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY infra/docker/python-deps.py /tmp/python-deps.py
COPY apps/api/pyproject.toml ./pyproject.toml

FROM base AS dev
RUN python /tmp/python-deps.py pyproject.toml dev > /tmp/req.txt && pip install -r /tmp/req.txt
COPY apps/api/ ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod-deps
RUN python /tmp/python-deps.py pyproject.toml > /tmp/req.txt && pip install -r /tmp/req.txt

FROM python:3.12.8-slim-bookworm AS prod
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --no-create-home aitms
WORKDIR /srv
COPY --from=prod-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=prod-deps /usr/local/bin /usr/local/bin
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./alembic.ini
COPY content /content
COPY packages/contracts /contracts
ENV CONTENT_DIR=/content CONTRACTS_DIR=/contracts
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Build context: repository root.  Targets: dev, prod
FROM python:3.12.8-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY infra/docker/python-deps.py /tmp/python-deps.py
COPY apps/worker/pyproject.toml ./pyproject.toml

FROM base AS dev
RUN python /tmp/python-deps.py pyproject.toml dev > /tmp/req.txt && pip install -r /tmp/req.txt
COPY apps/worker/ ./
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=INFO", "-Q", "eval-light,eval-sandbox,eval-llm"]

FROM base AS prod-deps
RUN python /tmp/python-deps.py pyproject.toml > /tmp/req.txt && pip install -r /tmp/req.txt

FROM python:3.12.8-slim-bookworm AS prod
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --no-create-home aitms
WORKDIR /srv
COPY --from=prod-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=prod-deps /usr/local/bin /usr/local/bin
COPY apps/worker/worker ./worker
USER 10001
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=INFO", "-Q", "eval-light,eval-sandbox,eval-llm"]

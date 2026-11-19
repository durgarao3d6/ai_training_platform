# Build context: repository root.  Targets: dev, prod
# Stub for Phase 0. The real runner (task 6.1) will need the Docker CLI/socket proxy.
FROM python:3.12.8-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY services/requirements-stub.txt ./requirements.txt
RUN pip install -r requirements.txt

FROM base AS dev
COPY services/sandbox-runner/ ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--reload"]

FROM base AS prod
RUN useradd --system --uid 10001 --no-create-home aitms
COPY services/sandbox-runner/app ./app
USER 10001
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]

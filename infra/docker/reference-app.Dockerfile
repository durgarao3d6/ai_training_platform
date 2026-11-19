# Build context: repository root.  Targets: dev, prod
FROM python:3.12.8-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY services/requirements-stub.txt ./requirements.txt
RUN pip install -r requirements.txt

FROM base AS dev
COPY services/reference-app/ ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200", "--reload"]

FROM base AS prod
RUN useradd --system --uid 10001 --no-create-home aitms
COPY services/reference-app/app ./app
USER 10001
EXPOSE 8200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]

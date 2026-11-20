# AITMS: AI Training Management System

Multi-role intern training platform (Developer, BA, QA, UI/UX). Specs live in `docs/` and `.kiro/specs/aitms-prototype/`.

## Clone and run locally with Docker

Install Git and start Docker Desktop, or use Docker Engine with the Docker Compose v2 plugin. Run the commands from your terminal. The app and its dependencies run in containers.

1. Clone the repository and enter its directory.

   ```sh
   git clone https://github.com/durgarao3d6/ai_training_platform.git
   cd ai_training_platform
   ```

2. Create a local configuration with `cp .env.example .env` in Bash or `Copy-Item .env.example .env` in PowerShell. Open `.env` and set `DEMO_PASSWORD` to a local-only password of at least 12 characters. The default fixture mode works without an OpenAI API key. Keep `.env` out of Git.

3. Build and start the web app and its dependencies, apply the database migrations, and create the bootstrap accounts and storage bucket.

   ```sh
   docker compose --env-file .env -f infra/compose.yml up --build -d --wait web
   docker compose --env-file .env -f infra/compose.yml run --rm --no-deps api alembic upgrade head
   docker compose --env-file .env -f infra/compose.yml run --rm --no-deps api python -m app.seed.bootstrap
   ```

4. Open [http://localhost:3000](http://localhost:3000) and sign in as `admin@example.com` with the password you set. The catalog starts empty. To try the workflow, create and publish a course, assign a trainer to a cohort, and enroll one of the [seeded interns](#seeded-accounts).

To stop the stack while keeping database and uploaded files, run:

```sh
docker compose --env-file .env -f infra/compose.yml down
```

## Run everything with Docker only

The development helpers below start the stack with hot reload and run project checks inside Docker.

```powershell
./scripts/dev.ps1 up      # build and start all services (dev mode, hot reload), waits until healthy
./scripts/dev.ps1 test    # pytest inside the tools container
./scripts/dev.ps1 lint    # ruff, mypy, eslint, tsc
./scripts/dev.ps1 down
./scripts/dev.ps1 reset   # wipe volumes, rebuild, restart
```

With `make` available, use `make up`, `make test`, `make lint` and so on.

| Service | URL |
| --- | --- |
| web | http://localhost:3000 |
| api | http://localhost:8000/healthz |
| s3 (RustFS) API / console | http://localhost:9000 / http://localhost:9001 |

`.env` is created from `.env.example` on first `up`. Never commit `.env`.

Run `make client` (or `./scripts/dev.ps1 client`) to export the API schema and regenerate the TypeScript declarations. Run `make a11y` or `./scripts/dev.ps1 a11y` in a disposable project to exercise the trainer review flow in Chromium and run accessibility checks.

### Seeded accounts

These are the only seeded data (from `apps/api/app/seed/bootstrap.py`). All use the `DEMO_PASSWORD` value.

| Role | Email |
| --- | --- |
| Intern, Developer track | intern.dev@example.com |
| Intern, Business Analyst track | intern.ba@example.com |
| Intern, QA track | intern.qa@example.com |
| Intern, UI/UX track | intern.ux@example.com |
| Trainer | trainer@example.com |
| HR | hr@example.com |
| Admin | admin@example.com |

There is no sample data. A fresh platform has no courses, cohorts or enrollments.

### Creating content and people

Everything else is created in the application:

- Admins author courses, milestones, tasks, deliverable manifests and rubrics (draft, then publish).
- HR and admins create cohorts, enroll interns in published courses (an intern can be in several courses) and create accounts. HR can create interns only.
- Enrolling an intern creates their milestone progress and task instances.

Optional one-time import: the drafted YAML in `content/` can be brought in once with `python -m app.content.cli import` (run it in the api container). It only creates missing records and never overwrites edits made in the app. `./scripts/dev.ps1 content-validate` checks the YAML without importing it.

See [the BA demo walkthrough](docs/ba-demo.md) and [pilot release checks](docs/pilot-release.md).

## Layout

```
apps/web  apps/api  apps/worker
services/sandbox-runner  services/reference-app
packages/contracts  content  infra  docs/adr
```

`apps/web/app/tokens.css` is a copy of `docs/aitms-tokens.css`. Keep them identical.

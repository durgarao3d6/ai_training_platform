# AITMS: AI Training Management System

Multi-role intern training platform (Developer, BA, QA, UI/UX). Specs live in `docs/` and `.kiro/specs/aitms-prototype/`.

## Run everything with Docker only

The host needs only Docker Desktop. No Python, Node or database is installed locally.

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

Commands for later phases (`client`, `a11y`) exist but report which task will implement them.

## First start

1. Set `DEMO_PASSWORD` in `.env` (at least 12 characters). It is the password for every seeded account.
2. Start and prepare the platform:

```powershell
./scripts/dev.ps1 up        # start all services
./scripts/dev.ps1 migrate   # alembic upgrade head
./scripts/dev.ps1 seed      # bootstrap: accounts, role profiles, storage bucket
```

Running `seed` twice changes nothing. All of the above is implemented in code and not yet verified end to end.

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

## Layout

```
apps/web  apps/api  apps/worker
services/sandbox-runner  services/reference-app
packages/contracts  content  infra  docs/adr
```

`apps/web/app/tokens.css` is a copy of `docs/aitms-tokens.css`. Keep them identical.

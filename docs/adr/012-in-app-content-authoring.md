# ADR-012: Course content authored in the application; YAML import is one-time

Status: Accepted (product owner decision, 8 Nov 2026). Implemented in code, not yet verified.
Supersedes ADR-008 for courses, milestones, tasks, deliverable manifests and rubrics.

## Context

ADR-008 kept content as versioned files in git, validated and loaded by a seed command. That suits a small fixed demo. On 8 Nov 2026 the product owner decided that the platform has no sample data and that everything except the seeded accounts and role profiles is created in the application.

Admins need to add a course, a milestone or a task without a code change and a deployment. Cohorts, enrollments and accounts already live in the database and need the same in-app management by HR and admins.

## Decision

- Admins author courses, milestones, tasks, deliverable manifests and rubrics in the application under `/api/v1/admin`. The permission is `catalog.manage` (admin).
- Rubrics have a lifecycle. A draft is saved with `PUT /api/v1/admin/tasks/{id}/rubric-draft` and can be edited. `POST /api/v1/admin/tasks/{id}/rubric-draft/publish` validates it, freezes it as a new version identified by its content hash, and writes an audit entry. A published rubric is never edited; a change means a new draft and a new version. Evaluations keep pinning the rubric version (FR-CAT-03).
- HR and admins create cohorts, enroll interns and create accounts under the `cohort.manage` permission (HR, admin). HR can create interns only. An intern can be enrolled in several courses at once.
- Enrolling creates the intern's milestone progress and task instances. Adding milestones or tasks to a course syncs enrolled interns.
- The admin module is an application-service layer. It owns no tables and calls the Catalog, Delivery, Identity and Progression services.
- The YAML in `content/` becomes a one-time, create-only import: `python -m app.content.cli validate` checks it, and `python -m app.content.cli import` creates missing records and never overwrites edits made in the app.

## What stays in code

- Role profiles and their checker lists (`apps/api/app/modules/catalog/roles.py`). Checkers are code plugins, so a role profile cannot be defined only by data. Bootstrap writes the profiles to the database.
- The rubric JSON schema and its validation rules (weights total 100, level descriptors, every bound check names a registered checker).
- Prompts and golden sets remain versioned files in the repository (ADR-008 still applies to them).
- The seeded accounts (`python -m app.seed.bootstrap`). Nothing else is seeded.

## Consequences

- Content is no longer reviewed through pull requests. The control moves into the application: publishing is a permissioned, audited action, and the role expert approval rule in docs/open-questions.md section 6 still applies before an admin publishes a rubric. AGENTS.md rule 4 (no changes to published rubrics without a human-approved ticket) still holds.
- The database becomes the source of truth for catalog content. Drafted YAML and the database can drift. This is accepted: the import never overwrites, so the app wins.
- Reproducibility of a fresh environment no longer comes from git alone. A new environment starts empty plus seeded accounts, and content is authored or imported once.
- The admin API surface and its authorisation tests grow (AGENTS.md rule 7: allowed and denied roles for every endpoint).
- Tests and golden sets cannot assume course content exists. They create what they need.
- Not yet verified: the endpoints, the draft and publish lifecycle, enrollment sync and the import exist in code and have not been tested end to end.

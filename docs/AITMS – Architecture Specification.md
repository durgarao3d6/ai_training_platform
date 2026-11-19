# AITMS – Architecture Specification

Version 0.2 prototype · Draft for development handover · 8 November 2026

Companion documents: AITMS Product Requirements Document · AITMS Implementation Plan. Requirement IDs (FR-, NFR-) refer to the PRD.

## Changes in v0.3 (8 November 2026)

Product owner decisions. Implemented in code, not yet verified.

1. **No sample data, no `is_sample`.** There is no `is_sample` column and no sample ribbon or tag. The only seeded data are seven user accounts, the four role profiles and the storage bucket (`python -m app.seed.bootstrap`). There is no demo-history command. This withdraws PRD FR-SMP-01 to FR-SMP-04.
2. **The catalog is authored in the application.** Admins create courses, milestones, tasks, deliverable manifests and rubrics. Rubrics follow a draft, then publish lifecycle: a draft can be edited, a published rubric is frozen and versioned, and publishing is audited. The YAML in `content/` is a one-time, create-only import (`python -m app.content.cli import`) that never overwrites edits made in the app. This supersedes ADR-008 for courses, tasks and rubrics (see ADR-012). Prompts and golden sets are not affected.
3. **Role profiles stay in code** (`apps/api/app/modules/catalog/roles.py`) because their checker lists are code plugins. Bootstrap writes them to the database.
4. **The admin module is an application-service layer and owns no tables.** It orchestrates the Catalog, Delivery, Identity and Progression services under `/api/v1/admin`: role-profiles; courses (list, create, get, patch, delete); courses/{id}/modules; courses/{id}/module-order; modules/{id} (patch, delete); modules/{id}/tasks; tasks/{id} (patch, delete); tasks/{id}/rubric-draft (put) and tasks/{id}/rubric-draft/publish (post); cohorts (list, create, get, patch); cohorts/{id}/enrollments; users (list by role, create). Two permissions guard it: `catalog.manage` (admin) and `cohort.manage` (HR, admin). HR can create interns only.
5. **Enrollment is dynamic.** An intern can be enrolled in several courses at once. Enrolling creates the intern's milestone progress and task instances, and adding milestones or tasks to a course syncs enrolled interns.

## 1. Purpose and scope

This document defines how AITMS is built: the structure of the system, its data model, the evaluation engine, the AI layer, security and the contracts between parts. It is detailed enough for engineers and AI coding agents to implement from, and open points are listed in section 19 and need a decision before the related phase.

The prototype is built to scale: it is a modular monolith with only the sandbox runner and the evaluation workers separated.

## 2. Architectural principles

1. **One engine, many role profiles.** Roles are configuration (rubrics, checkers, artifact types), not code forks. Adding DevOps or Data Analyst later means new content files plus a few plugins.
2. **Deterministic first, LLM second.** Tools produce facts: test results, lint output, contrast ratios, parsed structure. The LLM judges only what tools cannot, and it never sets facts or the final score.
3. **Scores are computed in code.** The LLM returns criterion ratings with evidence. A scoring service applies weights, thresholds and mandatory gates.
4. **Evaluations are reproducible.** Every run pins the rubric version, prompt version, model ID and tool versions.
5. **Coach, do not solve.** Feedback guides the intern. It is checked so it does not contain the corrected deliverable.
6. **Untrusted input everywhere.** Submissions are data, never instructions. Intern code never runs outside the sandbox.
7. **Modular monolith first.** Split into services only where there is a real reason.
8. **Contracts first.** The OpenAPI spec and the JSON schemas are the source of truth. Clients and tests are generated from them.

## 3. System context

```
 Next.js (TypeScript): Intern UI | Trainer UI | Admin/HR UI
      |  REST/JSON (OpenAPI), SSE for evaluation progress
 +----v------------- FastAPI modular monolith ---------------------+
 | Identity/RBAC | Catalog | Submissions | Evaluation | Traceability |
 | Progression   | Competency | Review  | Analytics  | Audit        |
 +----+-------------+----------------+-------------------+---------+
   PostgreSQL     Redis (queue,     Object store        LLM Gateway
   + pgvector     pub/sub)          (S3 API; RustFS     (provider-agnostic,
                                    locally, ADR-011)
                       |                                 schema-validated, cached)
            +----------v-----------+
            |  Evaluation Workers  |--> Sandbox Runner (gVisor, no network)
            +----------+-----------+--> Figma API (read-only)
                       +-------------> Reference app: Smart Knowledge Portal
                                       (isolated network, seeded defects)
```

## 4. Technology stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind with design tokens | Typed client generated from OpenAPI |
| API | FastAPI, Pydantic v2 | OpenAPI is generated and checked in CI |
| Data access | SQLAlchemy 2, Alembic | Migrations reviewed like code |
| Database | PostgreSQL 16 with pgvector | Row-level security for scoped access |
| Queue and events | Redis, Celery (see ADR-007) | Redis pub/sub feeds SSE |
| Object storage | RustFS locally (ADR-011), S3-compatible in cloud | Signed upload and download URLs; S3 API only |
| LLM | OpenAI API behind an internal gateway | Provider swappable; fixture mode for tests |
| Sandbox | Docker with gVisor runtime (runsc) | Separate runner service |
| Browser automation | Playwright | QA execution, UX to Dev screenshot comparison |
| Observability | OpenTelemetry, structlog, Prometheus-style metrics | One trace per evaluation run |
| Packaging | Docker Compose locally | Same images for CI and demo |

## 5. Modules of the monolith

Each module owns its tables and exposes a Python service interface. Other modules call the interface, never the tables. Dependencies point downwards only: Evaluation may call Catalog; Catalog may not call Evaluation.

| Module | Responsibility | Owns |
| --- | --- | --- |
| Identity/RBAC | Users, sessions, roles, permission checks | user, session, role\_assignment |
| Catalog | Role profiles, courses, milestones, task templates, rubric versions (draft and published), one-time content import | role\_profile, course, module, task\_template, rubric\_version |
| Delivery | Cohorts, enrollments, task instances | cohort, enrollment, task\_instance |
| Submissions | Attempts, artifacts, validation entry point | submission, artifact |
| Evaluation | State machine, stages, plugins, scoring, feedback, corrections | evaluation\_run, stage\_result, criterion\_score, finding, correction\_task |
| Review | Trainer queue, decisions, interventions, messages | review\_decision, intervention, message |
| Progression | Milestone unlocking and progress | milestone\_progress |
| Competency | Competency scores and history | competency, competency\_score |
| Traceability | Project, nodes, edges, coverage queries, integration evaluations | project, project\_artifact, trace\_node, trace\_edge |
| Admin (application services) | Authoring and enrollment workflows under `/api/v1/admin`; calls Catalog, Delivery, Identity and Progression services | none |
| Analytics | Read models for dashboards | views and materialised views only |
| Audit | Immutable event log | audit\_log |
| LLM Gateway | Provider calls, retries, cache, cost log, fixtures | llm\_call, prompt\_version |

## 6. Domain model

Every table has id (UUID), created\_at and updated\_at. There is no `is_sample` column: the platform has no sample data (v0.3).

### 6.1 Catalog (authored in the app, versioned rubrics)

`RoleProfile` → `Course` → `Module` (milestone) → `TaskTemplate` → `RubricVersion`.

- **RoleProfile:** key (developer, ba, qa, uiux), checker registry keys, judge prompt key, review policy.
- **TaskTemplate:** task\_type (practical, integration, assessment), description, learning objective, typed deliverable specs, current published rubric\_version\_id, depth (demo or content).
- **RubricVersion:** a draft until published (`tasks/{id}/rubric-draft`, then `/publish`); immutable once published. Contains criteria, weights, level descriptors, mandatory gates, threshold, checker bindings, correction templates. Identified by content hash.

### 6.2 Delivery (runtime)

`Cohort`, `User`, `Enrollment`, `TaskInstance`, `Submission` (attempt number, status), `Artifact` (kind: file, link, text; content type; SHA-256; storage key), `EvaluationRun`, `StageResult`, `CriterionScore`, `Finding` (source: tool, ai, trainer), `CorrectionTask`, `ReviewDecision`, `MilestoneProgress`, `CompetencyScore`.

### 6.3 Shared project and traceability

- `Project` (Smart Knowledge Portal) and `ProjectArtifact` (the approved output of each role, linked to a submission).
- `TraceNode(type, external_ref, version, project_id)`. Types: requirement, story, acceptance\_criterion, design\_frame, endpoint, dev\_task, test\_case, defect.
- `TraceEdge(from_node, to_node, relation, status, confirmed_by, origin)`. Relations: satisfies, designs, implements, verifies, reveals. Origin: tag, suggested, manual. Status: proposed, confirmed, rejected.

### 6.4 Cross-cutting

`AuditLog` (actor, action, subject, before and after, reason), `PromptVersion`, `LLMCall` (run, stage, model, tokens, cost, latency, cache hit), `GoldenSample` (task, label, trainer scores, kind: good, average, poor, adversarial).

### 6.5 Content authored in the app (replaces "Content as code")

Courses, milestones, tasks, deliverable manifests and rubrics are authored by admins in the application and stored in the database. A rubric is a draft until an admin publishes it. Publishing freezes it, assigns the next version, records its content hash and writes an audit entry. A published rubric is never edited; a change means a new draft and a new version. The YAML in `content/` is a one-time, create-only import: `python -m app.content.cli validate` checks it and `python -m app.content.cli import` creates missing records without overwriting edits made in the app. Role profiles and their checker lists remain in code (`apps/api/app/modules/catalog/roles.py`) because checkers are code plugins. Prompts and golden sets remain files in the repository. See ADR-012.

## 7. Rubric version format

This is the contract the whole engine depends on. Example (shortened):

```json
{
  "rubric_id": "dev.chunking",
  "version": 1,
  "role_profile": "developer",
  "pass_threshold": 70,
  "scale": {"min": 0, "max": 4},
  "criteria": [
    {
      "id": "overlap_handling",
      "weight": 20,
      "mandatory_min_level": 2,
      "levels": {
        "0": "No overlap or overlap breaks chunks",
        "2": "Fixed overlap works for normal input",
        "4": "Overlap correct, configurable and safe at boundaries"
      },
      "bound_checks": ["pytest_hidden.overlap"],
      "correction_template": "corr.overlap"
    }
  ],
  "deliverables": [
    {"id": "code", "kind": "file", "accept": [".py"], "required": true},
    {"id": "tests", "kind": "file", "accept": [".py"], "required": true},
    {"id": "explanation", "kind": "text", "min_words": 80, "required": true}
  ],
  "checkers": ["pytest_visible", "pytest_hidden", "coverage", "ruff", "mypy"]
}
```

Validation rules: weights sum to 100; every criterion has level descriptors for at least 0, 2 and 4; every bound check names a registered checker; every criterion has a correction template.

## 8. Evaluation engine

### 8.1 State machine

```
SUBMITTED -> VALIDATED -> COMPLETENESS_CHECKED -> AUTOCHECKED -> AI_RUBRIC
  -> SCORED -> FEEDBACK -> CORRECTION_CREATED -> [HUMAN_REVIEW]
  -> APPROVED | REVISION_REQUIRED
```

Any stage can move to `ERROR_RETRYING` and then `NEEDS_HUMAN` after the retry budget. Each stage:

- is idempotent: the same input produces the same stored output, keyed by (run\_id, stage, input\_hash);
- persists its result before the next stage starts;
- can be resumed by any worker after a crash;
- emits an SSE event.

### 8.2 Stages and owners

| Stage | Responsibility | Owner |
| --- | --- | --- |
| Validation | File type and size, empty files, link reachability, schema; malware scan (P1) | Code |
| Completeness | Every required deliverable present (for example all seven BA items) | Code |
| Objective checks | Role checkers run and emit findings | Tools |
| AI rubric | Per-criterion rating with verbatim evidence | LLM |
| Scoring | Weights, rating caps, gates, threshold | Code |
| Feedback | Strengths, priorities, guiding questions; leak check | LLM and code |
| Correction | Targeted tasks from failed criteria via templates | Code and LLM |
| Review gate | Decides if a human must review | Code |
| Approval | Unlocks the next milestone | Code |

### 8.3 Plugin interfaces

```python
class Checker(Protocol):  # deterministic
    key: str
    version: str
    def run(self, ctx: EvalContext) -> list[Finding]: ...

class RubricJudge(Protocol):  # LLM based
    def judge(self, ctx: EvalContext, criteria: list[Criterion],
              facts: list[Finding]) -> RubricResult: ...
```

A `RoleProfile` names its checkers and its judge prompt. A registry resolves them by key. **A test asserts that a task can only reference checkers and prompts belonging to its own role profile** (FR-EVAL-07).

### 8.4 Findings and rating caps

A `Finding` has: source (tool, ai, trainer), checker key, severity (info, warning, blocking), criterion\_id (optional), message, data, and an optional `rating_cap`. A cap limits the maximum rating the LLM may give for that criterion. Example: if hidden overlap tests fail, `overlap_handling` is capped at level 1 no matter what the LLM says. This is how facts from tools bind the AI.

### 8.5 Scoring algorithm

1. For each criterion: `rating = min(llm_rating, min(rating_caps))`.
2. `points = weight * rating / 4`. `total = sum(points)`.
3. A mandatory gate fails if `rating < mandatory_min_level` for any mandatory criterion, or any blocking finding exists.
4. Outcome is `PASS_CANDIDATE` if `total >= pass_threshold` and no gate fails. Otherwise it is `REVISION_REQUIRED`.
5. The review gate then decides whether a human must confirm.

The scoring service is a pure function with no I/O and has exhaustive unit tests.

### 8.6 Review gate

A human review is required when any of these holds:

- the role profile always requires review (UI/UX);
- the task is a final deliverable;
- an evidence quote failed verification;
- the judge returned low confidence or a review flag;
- the total is within 5 points of the threshold (configurable);
- instruction-like text was detected in the submission;
- the intern raised a disagreement.

APPROVED requires: PASS\_CANDIDATE and no pending review. A trainer approval unlocks the next milestone.

## 9. LLM layer

### 9.1 Gateway

The gateway handles retries with backoff, timeouts, caching by content hash (prompt version, model, input hash), per-call cost and latency logging, a model fallback policy, and a **fixture mode** that replays recorded responses (FR-EVAL-10). Application code never calls a provider SDK directly.

### 9.2 Output schema

```python
class Evidence(BaseModel):
    artifact_id: UUID
    quote: str            # verbatim text from the submission
    location: str | None  # for example page, line, section

class CriterionRating(BaseModel):
    criterion_id: str
    rating: int = Field(ge=0, le=4)
    rationale: str
    evidence: list[Evidence]
    failed_acceptance_criteria: list[str] = []

class RubricResult(BaseModel):
    criteria: list[CriterionRating]
    strengths: list[str]
    priorities: list[str]           # at most three
    feedback: str
    correction_hints: list[str]     # guiding questions, no full answers
    confidence: Literal['high', 'medium', 'low']
    review_flag: bool
    review_reason: str | None = None
    next_action: Literal['approve_candidate', 'correct', 'escalate']
```

Outputs that fail schema validation are retried once with the validation error, then escalated.

### 9.3 Controls

- **Anchored scale:** 0 to 4 with written level descriptors. Code converts to points.
- **Evidence verification:** every quote must appear in the artifact text (normalised whitespace, substring match). A miss lowers confidence and forces review.
- **Determinism:** temperature 0. Two or three sample self-consistency only on borderline results (P1).
- **Injection defence:** submission content is placed in delimited data blocks; the system prompt states that blocks contain data only; output is schema-bound; a detector flags instruction-like text (for example ignore previous instructions) and records a finding.
- **Leak check:** a second pass (code heuristics plus a small model) checks that feedback and correction hints do not contain a corrected version of the deliverable. A failed check regenerates the feedback with a stricter instruction.
- **Calibration:** each demo task has a golden set (good, average, poor and adversarial samples with trainer scores). CI re-runs it when a rubric or prompt changes and reports agreement with trainers (FR-EVAL-12).

### 9.4 Prompts

Prompts are versioned files in `content/prompts/` with a content hash, loaded into `prompt_version`. A prompt change is a reviewed pull request and triggers golden-set regression.

## 10. Role profile plugins

| Role | Checkers (demo task) | Notes |
| --- | --- | --- |
| Developer | `pytest_visible`, `pytest_hidden`, `coverage`, `ruff`, `mypy`, `edge_case_injection` | Hidden tests are never shown to the intern. Edge cases: empty input, overlap greater than chunk size, unicode, very long lines |
| BA | `doc_parse`, `req_id_unique`, `ambiguity_lint`, `story_format`, `gwt_pattern`, `nfr_measurable` | Ambiguity words (fast, user-friendly, easy) come from a maintained list in content. Parser supports .docx, .md and pasted text |
| QA | `testcase_parse`, `run_against_reference_app`, `seeded_defect_detection`, `defect_replay`, `scenario_coverage` | The platform executes the tests. Seeded-defect detection rate is the share of injected defects the intern's tests catch |
| UI/UX | `figma_extract`, `contrast`, `text_size`, `tap_target`, `flow_coverage`, `axe` (HTML only) | Figma extraction is read-only. Screenshot upload is the fallback. AI vision judge is advisory. Review is always required |

**QA flow:** parse the intern's test cases into an executable format (Playwright or API steps, using a defined template) → reset the reference app → run all tests in the sandbox against the reference app with a defect profile enabled → record pass or fail per test → compute which seeded defects were detected → replay each defect report's reproduction steps. A test is never marked executed because the intern wrote an expected result.

**UX flow:** fetch frames and styles from the Figma API (or read screenshots) → compute contrast ratios, text sizes and tap-target sizes from node data → map frames to requirement IDs through tags in frame names → call the vision judge with screenshots and rubric → findings are advisory → the trainer decides.

## 11. Traceability and cross-role integration

**Linking approach:** interns tag IDs explicitly (REQ-012 inside TC-045, or in a Figma frame name). The platform parses tags into `TraceEdge` rows with origin = tag. pgvector similarity can suggest further candidate links (origin = suggested, status = proposed), and a person confirms or rejects them. Coverage is then a graph query, which keeps it deterministic and auditable. The LLM only judges link quality, such as whether a test really verifies a requirement.

| Integration | Inputs | Core check | Priority |
| --- | --- | --- | --- |
| BA → QA | Requirements, test cases | Requirement-to-test coverage matrix; acceptance criteria testable | P0 |
| BA → UX | Approved requirements, design frames | Each story maps to at least one frame; exception flows present | P1 |
| UX → Dev | Frames, running app | Screenshot comparison (Playwright), navigation and responsive checks | P1 |
| Dev → QA | OpenAPI spec, app, defects | Contract tests, defect replay | P1 |
| Full product | All of the above | End-to-end journey, groundedness, security and accessibility checks | P2 |

Integration evaluations reuse the same engine with `task_type = integration` and several input artifacts. Their checkers are graph queries and tool runs.

## 12. Sandbox and reference application

### 12.1 Sandbox runner

- Separate service. Only the runner has access to the container runtime; the API and workers call it over an internal authenticated API. The Docker socket is never mounted into the monolith.
- One container per run under gVisor. Non-root user, read-only base image, ephemeral writable volume, no network (an allow-list proxy exists only for tasks that need an LLM), CPU, memory, process and wall-clock limits, output size cap.
- Inputs are copied in; outputs (logs, JUnit XML, coverage) are copied out and stored as artifacts. Containers are destroyed after each run.
- Runner image versions are recorded in the evaluation run.

### 12.2 Reference application

A reference implementation of the Smart Knowledge Portal runs in its own isolated network. It has resettable data, deterministic seed users and a **defect catalogue**: named defects enabled by a profile (for example no lockout after repeated failed logins, session never expires, protected page reachable without authentication). QA scoring uses the profile that was active during the run.

## 13. Security

### 13.1 Authentication and sessions

Email and password with Argon2 hashing, short-lived access tokens, refresh token in an httpOnly secure cookie, CSRF protection for cookie-based calls, rate limiting and lockout on auth endpoints.

### 13.2 Authorisation

Permissions are enforced in a FastAPI dependency layer and mirrored by PostgreSQL row-level security on cohort and intern identifiers. Both are tested.

| Resource | Intern | Trainer | HR | Admin |
| --- | --- | --- | --- | --- |
| Own submissions and evaluations | read, create | n/a | n/a | n/a |
| Assigned interns' submissions | no | read, review | no | read |
| Cohort overview and reports | no | assigned only | read | read |
| Override decision | no | yes, reason required | no | yes |
| Rubrics | read published | read | read | draft, publish |
| Users and cohorts | no | no | manage interns | manage all |
| Audit log | no | no | no | read |

### 13.3 Other controls

- Secrets from environment variables or a secret manager; a secret scanner runs in CI.
- Signed upload URLs with type and size limits; uploaded files are never executed outside the sandbox.
- All overrides, rubric publishes, exports and role changes are written to the audit log.
- Dependency and container image scanning in CI.
- Data retention and deletion jobs follow the policy decided in the PRD open questions.

## 14. API contracts

OpenAPI-first under `/api/v1`. Errors use RFC 7807 problem+json. List endpoints are paginated. Submissions accept an `Idempotency-Key` header.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /me` |
| Catalog | `GET /courses`, `GET /courses/{id}/modules`, `GET /task-instances/{id}` |
| Intern | `GET /interns/{id}/dashboard`, `GET /corrections?intern_id=` |
| Submissions | `POST /task-instances/{id}/submissions` (202 Accepted, evaluation id), `GET /submissions/{id}`, `GET /submissions/{id}/evaluations`, `POST /submissions/{id}/resubmit`, `POST /uploads/sign` |
| Evaluations | `GET /evaluations/{id}` (stages, criterion scores, findings), `GET /evaluations/{id}/stream` (SSE), `POST /evaluations/{id}/review`, `POST /evaluations/{id}/disagree` |
| Review | `GET /review/queue`, `POST /messages` |
| Projects | `GET /projects/{id}/traceability`, `GET /projects/{id}/coverage`, `GET /projects/{id}/integrations`, `POST /projects/{id}/integrations/{type}/run` |
| Admin | `POST /admin/cohorts`, `GET /admin/cohorts/{id}/overview`, `GET /admin/analytics/skills`, `POST /admin/rubrics`, `POST /admin/rubrics/{id}/publish`, `POST /admin/demo/reset` |

**SSE event types:** `stage.started`, `stage.completed`, `evaluation.completed`, `review.requested`, `evaluation.error`. Events carry ids only; the client fetches state with a normal GET, which makes reconnects safe.

## 15. Frontend architecture

- Next.js App Router with server components for read-heavy pages; client components for the uploader, evaluation stream and tables.
- Typed API client generated from OpenAPI. TanStack Query for server state.
- Design tokens (colour, type, spacing) in one file; the component library is built on accessible primitives. Keyboard and screen-reader tests run in CI.
- **One `EvaluationResult` component** renders any role from the result schema (PRD section 8). Role differences live in data, not components.
- Role-aware navigation: intern, trainer and admin/HR shells share components but have separate route groups.
- There is no sample data, so there are no sample ribbon or tag components. Lists and cards have designed empty states instead. The visual system is "Soft depth" (design tokens v0.3, UI Design Brief).

## 16. Asynchronous processing

- Submission creates the run and enqueues the first stage in one transaction (outbox pattern) so a run is never created without work queued.
- Workers pick up stages by run id. Retries use exponential backoff with a retry budget; failures end in `NEEDS_HUMAN` and a visible trainer queue item.
- Stage events are published to Redis; the API's SSE endpoint subscribes and forwards.
- Queues are separated by cost: `eval-light` (validation, document checks), `eval-sandbox` (code and test runs), `eval-llm` (rubric and feedback).

## 17. Quality, testing and observability

| Level | What |
| --- | --- |
| Unit | Scoring function, state machine transitions, rubric schema validation, evidence verification, permission matrix |
| Contract | OpenAPI conformance for every endpoint; generated client builds |
| Integration | End-to-end runs for the four demo tasks using fake LLM fixtures |
| Sandbox security | Escape attempts, network access, fork bombs, memory and time limits, large outputs |
| Golden-set regression | Agreement with trainer scores per task; fails the build below the target |
| Accessibility | Automated axe checks plus scripted keyboard flows |
| Demo | Scripted 10-minute run from reset, executed in CI nightly |

**Metrics:** per-stage latency, LLM cost per evaluation, trainer-override rate (the key quality signal), review-flag rate, evidence-verification failure rate, queue depth. **Tracing:** every evaluation run is one trace with LLM calls and tool runs as spans.

## 18. Environments and repository

### 18.1 Environments

| Environment | Purpose |
| --- | --- |
| Local | Docker Compose: web, api, worker, sandbox-runner, reference-app, postgres, redis, s3 (RustFS, ADR-011) |
| CI | Lint, type checks, unit and contract tests, fixture-based integration tests, golden-set regression, security tests |
| Demo | Compose or a single VM, seeded with the bootstrap accounts only; courses and cohorts authored in the app or imported once; LLM live with fixture fallback |

### 18.2 Key configuration

`DATABASE_URL`, `REDIS_URL`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `LLM_PROVIDER`, `OPENAI_API_KEY`, `LLM_MODE` (live or fixture), `FIGMA_TOKEN`, `JWT_SECRET`, `SANDBOX_URL`, `SANDBOX_TOKEN`, `REFERENCE_APP_URL`. A `.env.example` lists every variable with no real values.

### 18.3 Repository layout

```
aitms/
  AGENTS.md                 rules for AI coding agents
  apps/web/                 Next.js frontend
  apps/api/                 FastAPI modular monolith
  apps/worker/              Celery workers and stage runners
  services/sandbox-runner/  isolated execution service
  services/reference-app/   Smart Knowledge Portal with defect catalogue
  packages/contracts/       OpenAPI spec, JSON schemas, generated clients
  content/                  roles, courses, rubrics, prompts, golden sets
  infra/                    compose files, gVisor setup, CI
  docs/adr/                 architecture decision records
```

## 19. Decisions (ADRs) and open technical questions

| ADR | Decision | Status |
| --- | --- | --- |
| 001 | Modular monolith, with only the sandbox runner and workers separated | Proposed |
| 002 | Evaluation run as a persisted, idempotent state machine | Proposed |
| 003 | Checker and judge plugin interfaces, resolved by role profile | Proposed |
| 004 | Traceability as a typed graph with explicit tags and confirmed suggestions | Proposed |
| 005 | Anchored 0–4 ratings, scores computed in code, tool findings cap ratings | Proposed |
| 006 | gVisor containers for the sandbox; Firecracker is a later option | Proposed |
| 007 | Celery with Redis for the queue (alternative: Arq); decide at Phase 0 based on team experience | Open |
| 008 | Content (rubrics, prompts, golden sets) as versioned files in git, loaded by seed. Superseded by ADR-012 for courses, tasks and rubrics; still applies to prompts and golden sets | Proposed (partly superseded) |
| 009 | LLM gateway with fixture mode; provider is swappable | Proposed |
| 010 | Self-managed email and password auth for the prototype; SSO later | Proposed |
| 011 | RustFS as local object storage (docs/adr/011-rustfs-local-object-storage.md) | Accepted with conditions |
| 012 | Course content authored in the application; YAML import is one-time (docs/adr/012-in-app-content-authoring.md) | Accepted |

**Open technical questions**

1. Hosting target for the demo and for a pilot, and whether gVisor is available there.
2. Figma API access model (personal tokens or an organisation app) and rate limits.
3. How intern test cases are submitted for QA execution: a defined template (CSV or YAML) is proposed so the platform can run them.
4. Whether intern submissions may be sent to the LLM provider under company policy.
5. Whether pgvector suggestions (P1) justify their cost in the prototype, or tag-based linking is enough.


## Appendix A. AI-assisted course authoring (added 8 November 2026)

Scope and decisions: `docs/open-questions.md` section 7. Not yet in the PRD; proposed IDs FR-AUTH-01 to 05 await product owner confirmation.

**Principle.** AI proposes, a person commits. AI output is stored on `ai_job.result` and changes nothing until a person accepts items. Accepted items are always `draft`. An admin approves; only then do interns see a milestone. The model never scores, never publishes a rubric and never approves.

**Tables** (migrations 0002, 0003)
- `ai_job` (kind, status, requester, target, input, result, error). Row-level security: requester or admin.
- `course_material` (versioned text; originals are never overwritten; `.md` and `.txt` only for now).
- `course_component` (resource, reading_note, quiz, starter_file; `review_status` draft, in_review, approved; `ai_generated`; approver).
- `module.review_status` (draft or approved, existing rows approved) and `module.created_by`. Enrollment sync and every intern-facing read ignore draft modules.

**Permissions.** New `catalog.draft` for trainer and admin. `catalog.manage` (admin) is still required to approve milestones and components.

**Endpoints** (`/api/v1/authoring`): `config`, `pending`, `courses`, `drafts`, `attach`, `materials`, `materials/{id}/improve`, `jobs/{id}`, `jobs/{id}/accept|dismiss`, `components` (+ `submit`, `verify-link`, `approve`), `modules/{id}/approve`, trainer edits of own draft milestones. AI endpoints return 404 unless `AI_AUTHORING_ENABLED=true`.

**LLM gateway.** `complete_structured` in `app/modules/llm_gateway/service.py`. Prompts in `content/prompts/author_*.md`, hashed into `prompt_version`. Fixture mode replays recorded responses; live mode needs `LLM_LIVE_APPROVED=true` and an OpenAI key (data statement: open questions 7.4). Untrusted text goes in delimited blocks. Output must match a Pydantic schema (one retry). Each call is logged to `llm_call`.

**Guards on AI output.** Material suggestions must quote the text verbatim or they are dropped. Links must be https and start unverified; a person confirms them before approval. Quiz answers must point at an option. Starter-file names cannot contain paths. Suggestions made for an older material version cannot be applied.

**Study material for learners.** `GET /api/v1/modules/{id}/study` returns approved components only, milestone-level first, then per task. Interns need an enrollment and an open or complete milestone (locked: 403; not enrolled: 404). Trainer, HR and admin can preview any approved milestone. `POST /authoring/materials/{id}/publish` turns a material version into a draft reading note, which then goes through the normal approval. The intern course map shows "1. Study" then "2. Do the task" on each open milestone, and the task page shows the milestone's study material above the brief. Self-check quizzes are checked in the browser and never saved or scored.

**Known gaps.** Jobs run inside the request (no worker or outbox relay yet). No response cache. `cost_usd` is 0 (tokens are logged). Word and PDF upload not supported. Rubric drafts and deliverable manifests are not attachable yet. The approval check still requires an exact milestone count (open question 10). The OpenAPI client is not regenerated (`make client` is not implemented).

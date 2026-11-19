# Requirements Document

## Introduction

AITMS is a competency-based practical training and evaluation platform for IT interns. One shared evaluation engine supports several professional disciplines. The prototype covers four tracks (Software Developer, Business Analyst, QA Engineer, UI/UX Designer) working on one shared scenario, the Smart Knowledge Portal.

This spec covers the P0 scope of the management-demo prototype. P1 and P2 items are listed under "Out of scope" so they stay visible without driving the build.

Source documents (authoritative for detail and original requirement IDs):

- #[[file:docs/AITMS – Product Requirements Document.md]]
- #[[file:docs/AITMS – Architecture Specification.md]]
- #[[file:docs/AITMS – Implementation Plan.md]]
- #[[file:docs/AITMS – UI Design Brief and Reference Board (1).md]]

Each requirement has a "Source" line listing the PRD IDs it covers. Use those IDs in tickets, commits and tests.

## Glossary

- **Platform**: The AITMS system as a whole.
- **Intern, Trainer, HR_User, Admin**: The four user roles.
- **Catalog**: Role profiles (in code), and courses, milestones, task templates, deliverable manifests and rubric versions (authored in the application).
- **Rubric_Version**: A rubric is a draft until an Admin publishes it. A published Rubric_Version is an immutable, versioned, content-hashed definition of criteria, weights, level descriptors (0 to 4), mandatory gates, threshold, checker bindings and correction templates.
- **Submission**: One attempt by an Intern at a task, made of artifacts (file, link, text).
- **Evaluation_Engine**: The persisted, idempotent, resumable state machine that evaluates a Submission.
- **Checker**: A deterministic tool plugin that produces Findings.
- **Rubric_Judge**: The LLM-based plugin that rates criteria with verbatim evidence.
- **Finding**: A result with a source (tool, ai, trainer), severity and optional rating cap.
- **Scoring_Service**: A pure function that computes the score from ratings, caps, weights, gates and threshold.
- **LLM_Gateway**: The only component allowed to call an LLM provider. Supports caching, cost logging and fixture mode.
- **Sandbox_Runner**: The isolated service that executes intern-supplied code and tests.
- **Reference_App**: The Smart Knowledge Portal instance with a seeded defect catalogue, used for QA execution.
- **Review_Gate**: The rule set that decides whether a Trainer must confirm a result.
- **Trace_Graph**: Typed nodes and edges linking requirements, stories, design frames, tests and defects.
- **Bootstrap_Data**: The only seeded data: seven user accounts (one Intern per track, a Trainer, an HR_User, an Admin), the four role profiles and the storage bucket, created by `python -m app.seed.bootstrap`. There is no sample data.
- **Demo_Task**: One of four fully built tasks: Developer chunking, BA requirements, QA login and search tests, UX homepage wireframe.

## Requirements

### Requirement 1: Authentication and sessions

**User Story:** As a user, I want to log in securely, so that only I can access my account.

Source: FR-IAM-01, NFR-SEC-03

#### Acceptance Criteria

1. WHEN a user submits valid email and password THEN the Platform SHALL create a session with a short-lived access token and an httpOnly secure refresh cookie.
2. WHEN a user submits invalid credentials THEN the Platform SHALL return a generic error that does not reveal whether the email exists.
3. WHEN repeated failed logins occur for one account or address THEN the Platform SHALL rate limit and lock out further attempts.
4. WHEN a user logs out THEN the Platform SHALL invalidate the refresh token.
5. Passwords SHALL be stored using Argon2 hashes.

### Requirement 2: Role-based access control

**User Story:** As a product owner, I want access enforced on the server, so that nobody sees data outside their scope.

Source: FR-IAM-02, FR-IAM-03, NFR-PRV-01, PRD section 4 permission matrix, Architecture 13.2

#### Acceptance Criteria

1. The Platform SHALL enforce the permission matrix in a server-side dependency layer and mirror it with PostgreSQL row-level security on cohort and intern identifiers.
2. WHEN an Intern requests data belonging to another Intern THEN the Platform SHALL return 403.
3. WHEN a Trainer requests data of an Intern not assigned to them THEN the Platform SHALL return 403.
4. WHEN an HR_User requests data outside their cohorts THEN the Platform SHALL return 403.
5. WHEN a role without override permission attempts an override THEN the Platform SHALL return 403.
6. Every endpoint SHALL have automated tests for allowed and denied roles.

### Requirement 3: Catalog and rubric versioning

**User Story:** As an Admin, I want courses and rubrics stored with versioned rubrics, so that adding a course is content work done in the application.

Source: FR-CAT-01, FR-CAT-02, FR-CAT-03, FR-CAT-04 (changed 8 Nov 2026), NFR-MNT-01

#### Acceptance Criteria

1. The Platform SHALL store role profiles, courses, milestones, task templates and rubric versions as validated records. Role profiles and their checker lists SHALL stay in code.
2. Each task template SHALL define description, learning objective, typed deliverables, criteria with level descriptors 0 to 4, weights, passing threshold, mandatory gates, checker list and correction templates.
3. WHEN a Rubric_Version is published THEN the Platform SHALL make it immutable and identify it by content hash.
4. WHEN an evaluation runs THEN the Platform SHALL pin the Rubric_Version it used.
5. IF a rubric file fails schema validation (weights not summing to 100, missing descriptors for levels 0, 2 and 4, unregistered checker, missing correction template) THEN the content validator SHALL reject it with the failing rule named.
6. WHEN `python -m app.content.cli import` runs THEN the Platform SHALL create the missing records from the drafted YAML in content/ (4 tracks, 38 milestones) and SHALL NOT overwrite any record edited in the application, so that running it twice changes nothing. The import is one-time and create-only.
7. Four milestones SHALL be demo-depth. The other 34 SHALL be content-only.

### Requirement 4: Bootstrap data and reset (no sample data)

**User Story:** As a presenter, I want a platform that starts empty apart from the accounts, so that nothing on screen is invented and the demo is honest.

Source: FR-SMP-01 to FR-SMP-04 (withdrawn 8 Nov 2026; product owner decision)

#### Acceptance Criteria

1. There SHALL be no sample data and no `is_sample` column on any table. The UI SHALL have no SAMPLE ribbon or tag.
2. WHEN `python -m app.seed.bootstrap` runs THEN the Platform SHALL create only the seven user accounts (one Intern per track, a Trainer, an HR_User, an Admin), the four role profiles and the storage bucket, and running it twice SHALL change nothing. It SHALL read the account password from DEMO_PASSWORD and refuse a value shorter than 12 characters.
3. The bootstrap SHALL NOT write courses, cohorts, enrollments, progress, submissions, scores, findings, evidence or decisions.
4. WHEN a documented reset runs THEN the Platform SHALL return to an empty platform plus the seeded accounts.
5. Lists and cards on a fresh platform SHALL show designed empty states with a next step (Requirement 5, criterion 9).
### Requirement 5: Intern experience

**User Story:** As an Intern, I want to know what to do next and what is expected, so that I can work without confusion.

Source: FR-INT-01 to FR-INT-06, UI Design Brief 6.1 to 6.3, 6.9

#### Acceptance Criteria

1. The intern home SHALL show a hero card for the course that most needs attention, with its current task and one primary action, and SHALL list every enrolled course with a status: In progress, Not started, Waiting for review or Complete. An Intern MAY be enrolled in several courses at once.
2. "My courses" SHALL open a course map page per course. Each map SHALL show locked, unlocked and complete milestones, and a locked milestone SHALL state what unlocks it.
3. The task page SHALL show brief, objective, deliverables and the rubric in plain language before the Intern starts.
4. The Platform SHALL show submission history with attempt number, status and result.
5. WHILE an evaluation is running THEN the UI SHALL show human-language stages and tell the Intern they can close the tab.
6. IF an evaluation fails to finish THEN the UI SHALL state that the work is saved and the Trainer has been told.
7. The Intern SHALL be able to send a message to their Trainer from a task or evaluation.
8. The intern screens SHALL NOT show leaderboards, streak pressure or cohort comparisons.
9. Every list and card SHALL have a designed empty state with a next step.

### Requirement 6: Submissions and attempts

**User Story:** As an Intern, I want to submit files, links and text and resubmit after feedback, so that I can improve my work.

Source: FR-SUB-01 to FR-SUB-05, NFR-SEC-03

#### Acceptance Criteria

1. The Platform SHALL accept file, link and pasted-text artifacts and store type, size and SHA-256 for each.
2. Uploads SHALL use signed URLs with type and size limits.
3. WHEN an Intern resubmits THEN the Platform SHALL create a new attempt and keep earlier attempts immutable.
4. WHEN a submission request carries an Idempotency-Key already used THEN the Platform SHALL return the original result without creating a duplicate.
5. IF an artifact has a disallowed type, exceeds size, is empty or is an unreachable link THEN the Platform SHALL reject it with a specific message.
6. WHEN a submission is accepted THEN the Platform SHALL return 202 with an evaluation id and run evaluation asynchronously.
7. Submission content SHALL be treated as data only and never as instructions to the AI.
8. Auth and submission endpoints SHALL be rate limited.

### Requirement 7: Evaluation engine core

**User Story:** As a Trainer, I want evaluations to be reliable and reproducible, so that I can trust them.

Source: FR-EVAL-01, 02, 04, 06, 07, 10, NFR-REL-01, NFR-REL-02, Architecture 8

#### Acceptance Criteria

1. The Evaluation_Engine SHALL run stages in order: validation, completeness, objective checks, AI rubric, scoring, feedback, correction, review gate, approval.
2. Each stage SHALL be idempotent, persist its result before the next starts, be resumable by any worker, and emit an SSE event.
3. WHEN a worker crashes THEN another worker SHALL resume from the last completed stage.
4. IF a stage exhausts its retry budget THEN the run SHALL move to NEEDS_HUMAN and appear in the Trainer queue.
5. Objective results SHALL come only from Checkers. The AI SHALL NOT create or change them.
6. Each run SHALL record rubric version, prompt version, model id, checker versions, tokens, cost and latency.
7. A role profile SHALL resolve only its own Checkers and judge prompt, and an automated test SHALL prove no role is evaluated with another role's rubric.
8. SSE events SHALL carry ids only so reconnects are safe.
9. IF the LLM provider fails THEN the run SHALL wait, retry, then flag for human review, and SHALL NOT invent a result.

### Requirement 8: Scoring and review gate

**User Story:** As a product owner, I want scores computed in code, so that AI variance cannot decide outcomes.

Source: FR-EVAL-04, Architecture 8.4 to 8.6

#### Acceptance Criteria

1. The Scoring_Service SHALL be a pure function without I/O.
2. For each criterion the effective rating SHALL be min(llm_rating, minimum of rating caps from Findings).
3. Points SHALL equal weight × rating / 4, and total SHALL be their sum.
4. A mandatory gate SHALL fail if any mandatory criterion rating is below its minimum level or any blocking Finding exists.
5. The outcome SHALL be PASS_CANDIDATE only if total ≥ threshold and no gate fails; otherwise REVISION_REQUIRED.
6. The Review_Gate SHALL require human review WHEN any of these hold: role always requires review; final deliverable; evidence verification failed; low confidence or review flag; total within 5 points of threshold; instruction-like text detected; intern raised disagreement.
7. APPROVED SHALL require PASS_CANDIDATE and no pending review.
8. The Scoring_Service SHALL have exhaustive unit tests.

### Requirement 9: LLM gateway and AI controls

**User Story:** As a tech lead, I want all AI use controlled and verifiable, so that results are safe and repeatable.

Source: FR-EVAL-03, 05, 08, 09, 10, NFR-SEC-04, NFR-COST-01, NFR-PORT-01, Architecture 9

#### Acceptance Criteria

1. All LLM calls SHALL go through the LLM_Gateway, with retries, timeouts, content-hash caching and per-call cost and latency logging.
2. The LLM_Gateway SHALL support a fixture mode that replays recorded responses for tests and as a demo fallback.
3. The Rubric_Judge SHALL return the strict schema: per-criterion rating 0 to 4, verbatim evidence, failed acceptance criteria, feedback, correction hints, confidence, review flag and next action.
4. IF output fails schema validation THEN the Platform SHALL retry once with the validation error, then escalate.
5. WHEN a rating's evidence quote does not appear in the artifact text (whitespace-normalised substring) THEN the Platform SHALL lower confidence and force human review.
6. The Platform SHALL place submission content in delimited data blocks and flag instruction-like text as a Finding visible to the Trainer.
7. A leak check SHALL verify feedback and correction hints do not contain the corrected deliverable, and a failure SHALL regenerate feedback with a stricter instruction.
8. Prompts SHALL be versioned files with content hashes.
9. Temperature SHALL be 0.

### Requirement 10: Developer role profile (chunking task)

**User Story:** As a Developer Intern, I want my code run against real tests, so that feedback reflects whether it works.

Source: FR-ROLE-01, FR-ROLE-04, NFR-SEC-01, Architecture 10, 12.1

#### Acceptance Criteria

1. The Developer profile SHALL run pytest (visible and hidden), coverage, ruff, mypy and edge-case injection (empty input, overlap larger than chunk size, unicode, very long lines).
2. Hidden tests SHALL never be shown to the Intern.
3. IF hidden overlap tests fail THEN the overlap_handling criterion SHALL be capped at level 1.
4. Intern code and tests SHALL execute only in the Sandbox_Runner.
5. The Sandbox_Runner SHALL run each execution in its own gVisor-capable container with no network, non-root, read-only image, ephemeral volume, and CPU, memory, process, time and output limits, and SHALL destroy it afterwards.
6. The Docker socket SHALL NOT be mounted into the API or workers.
7. A sandbox security test suite SHALL cover escape attempts, network access, fork bombs, memory and time limits and large output.
8. The Developer task SHALL complete in under 3 minutes at p90.

### Requirement 11: Business Analyst role profile (requirements task)

**User Story:** As a BA Intern, I want guided feedback that does not rewrite my work, so that I learn to improve it.

Source: FR-ROLE-01, FR-FB-02, Architecture 10

#### Acceptance Criteria

1. The BA profile SHALL parse .docx, .md and pasted text.
2. The BA profile SHALL check requirement ID uniqueness, ambiguity words from a maintained list, user-story format, Given/When/Then pattern and NFR measurability.
3. WHEN requirements are missing THEN feedback SHALL name the gap through guiding questions and SHALL NOT supply rewritten requirements.
4. The document-based task SHALL complete in under 90 seconds at p90.

### Requirement 12: QA role profile (login and search task)

**User Story:** As a QA Intern, I want my tests actually executed, so that results measure real defect detection.

Source: FR-ROLE-01, FR-ROLE-02, Architecture 10, 12.2

#### Acceptance Criteria

1. The QA profile SHALL parse intern test cases from the agreed template (CSV or YAML, decision pending).
2. A test SHALL count as executed only if the Platform ran it against the Reference_App. Expected results written by the Intern SHALL NOT count as execution.
3. The Reference_App SHALL run in an isolated network with resettable data, deterministic seed users and a defect catalogue enabled by profile.
4. The Platform SHALL compute the seeded-defect detection rate using the defect profile active during the run.
5. The Platform SHALL replay the reproduction steps of each defect report and compute scenario coverage against requirements.
6. The Reference_App SHALL be reset before each run.

### Requirement 13: UI/UX role profile (homepage wireframe task)

**User Story:** As a Trainer, I want automated accessibility findings with AI as an advisory only, so that I make the final design call.

Source: FR-ROLE-01, FR-ROLE-03, Architecture 10

#### Acceptance Criteria

1. The UX profile SHALL extract frames, components and styles from the Figma API using read-only access, and compute contrast, text size and tap-target size.
2. The UX profile SHALL map frames to requirement IDs through tags in frame names.
3. AI findings for UX SHALL be labelled advisory.
4. Every UX evaluation SHALL require Trainer review, and the evaluation view SHALL show the Trainer review pending badge.
5. Screenshot upload as a fallback is P1 and SHALL be tracked but not required for the demo.

### Requirement 14: Feedback and corrections

**User Story:** As an Intern, I want respectful, specific feedback with a clear next step, so that I know how to improve.

Source: FR-FB-01 to FR-FB-04, FR-PRG-02, UI Design Brief 3, 6.5, 8

#### Acceptance Criteria

1. Feedback SHALL appear in this order: status, one-line summary, strengths with evidence, up to three priority improvements, per-criterion detail.
2. The Platform SHALL use "Needs another pass" and SHALL NOT use "Failed" or "Rejected" in user-facing text.
3. WHEN a criterion fails THEN the Platform SHALL create a correction task from its template with guiding questions and what to resubmit, without giving the answer.
4. Every Finding SHALL carry a source label: Measured by tests, Read by AI, or Reviewed by a trainer (named).
5. The correction panel SHALL show one correction at a time and state that the previous attempt stays in history.
6. Feedback SHALL NOT use fake-precision confidence figures and SHALL NOT use exclamation marks.

### Requirement 15: Shared evaluation view

**User Story:** As an Intern or Trainer, I want one consistent evaluation screen for every role, so that results are easy to read.

Source: FR-EVU-01 to FR-EVU-08, FR-INT-05, NFR-A11Y-01

#### Acceptance Criteria

1. One EvaluationResult component SHALL render any role from the result schema, with no per-role screens.
2. The view SHALL show status and a one-line summary before any number.
3. The view SHALL show what is working first, then the top three priorities, with the rest collapsed.
4. Criterion bars SHALL carry words as well as numbers.
5. Each criterion SHALL expand to its evidence quote highlighted in the Intern's own submission, with a verified flag.
6. The view SHALL show the source label of each Finding.
7. The review badge SHALL state the reason and an expected time.
8. Actions SHALL be Start correction and Ask a question. I disagree is P1.
9. Meaning SHALL NOT be conveyed by colour alone, all actions SHALL be keyboard operable, and contrast SHALL meet WCAG 2.2 AA.

### Requirement 16: Trainer review

**User Story:** As a Trainer, I want a fast queue with evidence beside the submission, so that I can decide confidently.

Source: FR-REV-01 to FR-REV-04, UI Design Brief 6.6

#### Acceptance Criteria

1. The queue SHALL sort by risk then waiting time, and show why each item was flagged.
2. The review pane SHALL show AI evidence beside the submission.
3. A Trainer SHALL be able to approve, request revision, or override.
4. WHEN a Trainer overrides THEN the Platform SHALL require a reason and write an audit log entry.
5. The review pane SHALL show an Intern context card with attempt history and earlier weak criteria.
6. Review actions SHALL have keyboard shortcuts.
7. Trainers SHALL see only assigned Interns.
8. Tables SHALL support Compact, Default (40px rows) and Comfortable density, remembered per user.

### Requirement 17: Progression and competency

**User Story:** As an Intern, I want the next milestone to unlock when my work is approved, so that progress is meaningful.

Source: FR-PRG-01, FR-PRG-03

#### Acceptance Criteria

1. The next milestone SHALL unlock only after approval.
2. WHEN an evaluation is approved THEN competency scores SHALL update from that approved result only.
3. For each Demo_Task the flow fail → correction → resubmit → approve SHALL work end to end, including Trainer decision where required.

### Requirement 18: Cross-role traceability

**User Story:** As HR, I want to see which requirements have verifying tests, so that I can judge project readiness.

Source: FR-XR-01 to FR-XR-05

#### Acceptance Criteria

1. A shared project SHALL hold the approved output of each role.
2. The Trace_Graph SHALL support node types requirement, story, acceptance criterion, design frame, endpoint, dev task, test case, defect and relations satisfies, designs, implements, verifies, reveals.
3. The Platform SHALL parse Intern-provided tags (for example REQ-012 inside TC-045) into edges with origin = tag.
4. The BA→QA coverage matrix SHALL be computed by graph query and be reproducible.
5. The AI SHALL judge only the quality of a link, never whether the link exists.

### Requirement 19: HR dashboard

**User Story:** As an HR user, I want an honest view of progress and support needs, so that I can act without a witch hunt.

Source: FR-HR-01 to FR-HR-07, NFR-PRV-02, UI Design Brief 6.7, 12.6

#### Acceptance Criteria

1. An HR_User or Admin SHALL be able to create a cohort, enroll Interns in one or more courses and create Intern accounts (see Requirement 23).
2. The cohort overview SHALL show per Intern track, progress, status and the reason for the status, using "Needs support" and not red alarms.
3. The Platform SHALL show evaluation history and the list of evaluations needing another pass.
4. The Platform SHALL show skills needing attention across the cohort and the cross-role dependency view with final project status.
5. Readiness SHALL be a three-state label (Not yet, Getting close, Ready for project work) always shown with its inputs checklist, and SHALL NOT be a percentage or ranking. The definition is a proposal pending product owner confirmation.
6. Reports SHALL separate tool-measured results from AI judgments.
7. Interns SHALL be able to see the same readiness card about themselves.
8. Every number on screen SHALL be traceable to records.

### Requirement 20: Non-functional

**User Story:** As a tech lead, I want security, performance, observability and portability baselines, so that the prototype is safe and demonstrable.

Source: NFR-SEC-02, NFR-PERF-01, NFR-OBS-01, NFR-A11Y-01, NFR-MNT-01, NFR-PORT-01

#### Acceptance Criteria

1. Secrets SHALL exist only in environment variables or a secret manager. A secret scanner SHALL run in CI and `.env.example` SHALL list variables without values.
2. UI pages SHALL respond in under 1 second at p90 on the demo dataset.
3. Every evaluation run SHALL be one trace, with metrics for stage latency, LLM cost per evaluation, override rate, review-flag rate, evidence verification failure rate and queue depth.
4. The whole stack SHALL build and run locally with `docker compose up --build`, requiring only Docker on the host. No Python, Node, PostgreSQL, Redis or other runtime SHALL be needed on the host.
4a. Every Dockerfile SHALL be buildable from a clean checkout, using pinned base image versions and a multi-stage build with separate development and production targets.
4b. All developer commands (lint, type checks, unit and integration tests, migrations, seed, content validation, OpenAPI client generation, accessibility checks) SHALL run inside containers through documented Compose services or a Makefile/script wrapper.
4c. WHEN `docker compose up --build` completes THEN every service SHALL expose a health check, and a single `docker compose ps` SHALL show all services healthy.
4d. The web app SHALL support hot reload in the development target through bind-mounted source, and database, object storage and Redis data SHALL persist in named volumes.
4e. A documented command SHALL reset the local environment (containers, volumes) to a clean state, after which the bootstrap recreates the seeded accounts.
4f. CI SHALL use the same images and Compose files as local development.
5. The API SHALL be OpenAPI-first, errors SHALL use RFC 7807 problem+json, and a TypeScript client SHALL be generated.
6. The UI SHALL pass automated accessibility checks in CI plus a manual keyboard pass per phase.
7. The UI SHALL use semantic design tokens only, with no raw colour values in components.

### Requirement 21: Management demo acceptance

**User Story:** As a product owner, I want the 10-minute demo to run repeatably, so that management sees a credible product.

Source: PRD section 3.3, section 11 (reset changed 8 Nov 2026; FR-SMP-03 withdrawn)

#### Acceptance Criteria

1. The scripted 10-minute demo SHALL run from a reset (empty platform plus seeded accounts, then the demo course content authored in the app or imported once) three consecutive times with no manual fixes.
2. The demo SHALL run on the real evaluation pipeline, with fixtures replacing only the LLM call.
3. WHEN the LLM provider is disabled THEN the demo SHALL still complete using recorded fixtures.
4. 100% of displayed evidence quotes SHALL exist in the submission.
5. The scripted run SHALL execute nightly in CI.

### Requirement 22: In-app catalog authoring

**User Story:** As an Admin, I want to author courses, milestones, tasks, deliverable manifests and rubrics in the application, so that content changes need no code change.

Source: FR-CAT-04 and FR-CAT-05 (changed 8 Nov 2026), ADR-012. Status: implemented in code, not yet verified.

#### Acceptance Criteria

1. An Admin (permission catalog.manage) SHALL be able to list, create, read, update and delete courses, create and reorder milestones, create tasks under a milestone, and update or delete milestones and tasks, under /api/v1/admin.
2. An Admin SHALL be able to save a rubric as a draft and edit it freely, then publish it.
3. WHEN a rubric is published THEN the Platform SHALL validate it against the rubric schema, freeze it as a new version identified by its content hash, and write an audit log entry. A published rubric SHALL NOT be edited.
4. Role profiles SHALL be listed read-only from the admin API.
5. WHEN a milestone or task is added to a course THEN the Platform SHALL sync it to the Interns already enrolled in that course.
6. Roles other than Admin SHALL receive 403 on the catalog endpoints, and each endpoint SHALL have allowed and denied role tests.

### Requirement 23: Cohorts, enrollments and accounts

**User Story:** As an HR user or Admin, I want to create cohorts, enroll interns and create accounts in the application, so that no seeding is needed to onboard people.

Source: FR-HR-01, FR-IAM-02. Status: implemented in code, not yet verified.

#### Acceptance Criteria

1. An HR_User or Admin (permission cohort.manage) SHALL be able to list, create, read and update cohorts and to enroll Interns through cohorts/{id}/enrollments.
2. An Intern MAY be enrolled in several courses at once.
3. WHEN an Intern is enrolled THEN the Platform SHALL create the Intern's milestone progress and task instances for that course.
4. An Admin SHALL be able to list users by role and create accounts of any role. An HR_User SHALL be able to create Intern accounts only and SHALL receive 403 for any other role.
5. Each endpoint SHALL have allowed and denied role tests, and an HR_User SHALL see only their own cohorts.

### Requirement 24: Soft depth visual system

**User Story:** As a designer, I want one token file and a defined look, so that the interface is consistent and accessible.

Source: UI Design Brief v0.3 sections 4, 5, 12.3 and 12.5, docs/aitms-tokens.css. Status: implemented in code, not yet verified.

#### Acceptance Criteria

1. The web app SHALL use design tokens v0.3 from apps/web/app/tokens.css, which SHALL be identical to docs/aitms-tokens.css.
2. The shell SHALL use a floating white sidebar whose active item is a solid ink pill, floating white cards with large radii and soft shadows, solid ink primary buttons, and violet for links and focus.
3. Each track SHALL have a pastel colour (developer peach, BA mint, QA lavender, UI/UX butter), and the track name SHALL always appear beside it.
4. The interface SHALL use Plus Jakarta Sans, human words (feedback, briefs, trainer notes) Source Serif 4, and code and evidence IBM Plex Mono, all self-hosted.
5. Status SHALL always use text plus an icon shape, and text and controls SHALL meet WCAG 2.2 AA contrast.

## Out of scope for this spec

- P1: self-consistency re-runs, golden-set regression in CI, skill profile, exports, audit log views, I disagree, trainer personal notes, intervention log, attempt limits, malware scan, screenshot fallback, BA→UX / UX→Dev / Dev→QA evaluations, similarity-suggested links.
- P2: SSO, full product evaluation, additional roles, dark mode.
- Withdrawn: sample data, SAMPLE labelling, seeded evaluation history and the demo-history command (FR-SMP-01 to FR-SMP-04, 8 Nov 2026).

## Open decisions (from PRD section 13 and Plan section 9)

Passing threshold and gates per task, readiness definition, attempt limits, data retention, trainer capacity for UX, Figma access model, whether submissions may go to the LLM provider, Celery vs Arq (ADR-007), QA test-case template format, hosting and gVisor availability.

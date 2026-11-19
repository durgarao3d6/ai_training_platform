# AITMS – Implementation Plan

Version 0.2 prototype · Draft for development handover · 8 November 2026

Companion documents: AITMS Product Requirements Document · AITMS Architecture Specification. Requirement IDs (FR-, NFR-) refer to the PRD; section numbers refer to the Architecture Specification.

## 1. Purpose

This plan tells the development team what to build, in what order, how to know each step is done, and how to work with AI coding agents safely. Durations are **indicative**: they assume the team in section 3 and should be re-estimated at the end of Phase 0.

## 2. Delivery approach

1. **Contracts first.** Lock the database schema, the rubric JSON schema and the OpenAPI skeleton before feature work. Everything depends on them.
2. **Vertical slice first.** Build the Developer chunking task end to end (upload, sandbox, evaluation, feedback, correction, approval, UI). It becomes the reference implementation for the other three roles.
3. **Content is on the critical path.** Rubrics with level descriptors, golden sets, correction templates and the reference app's defect catalogue need trainers. Start this in Phase 0 and run it in parallel with engineering.
4. **Demo-depth before breadth.** Four tasks are built fully (chunking, requirements, login test cases, homepage wireframe). The remaining 34 milestones are filled in as content only.
5. **Every phase ends with a gate.** Demo to the product owner, check the exit criteria, record decisions. No phase starts on top of an unfinished gate.
6. **Humans own the risky parts.** AI agents write most code, but people review authentication, authorisation, the sandbox, scoring, migrations, prompts and rubrics (section 7.5).

## 3. Team and workstreams (suggested)

| Role | Count | Focus |
| --- | --- | --- |
| Tech lead / architect | 1 | Contracts, ADRs, reviews of high-risk code, agent guardrails |
| Backend engineers | 2 | API, evaluation engine, LLM gateway, workers |
| Frontend engineer | 1 | Application shells, intern, trainer and HR screens, evaluation component |
| Platform / QA engineer | 1 | Sandbox runner, reference app, CI, security and demo-reset tests |
| UX designer | 0.5 | Design tokens, key screens, usability sessions |
| Role experts (trainers) | 4 part-time | One per track: rubrics, level descriptors, golden sets, correction templates |
| Product owner | 1 | Decisions in section 9, gate sign-off |

| Workstream | Output |
| --- | --- |
| A. Platform | Schema, auth, RBAC, catalog, submissions, progression |
| B. Evaluation | State machine, scoring, LLM gateway, plugins, review gate |
| C. Experience | Intern, trainer and HR UI, evaluation component, sample data labelling |
| D. Content | Rubrics, prompts, golden sets, templates, reference app defects, seed data |
| E. Quality | Test strategy, sandbox security tests, golden-set regression, demo rehearsal |

## 4. Phase overview

| Phase | Scope | Indicative duration | Exit criterion |
| --- | --- | --- | --- |
| 0 | Foundations: schema, ADRs, OpenAPI skeleton, Compose, CI, content schemas | 1 week | `docker compose up` gives a healthy stack and CI is green |
| 1 | Auth, RBAC and application shells | 1.5 weeks | Four roles log in and see only scoped views |
| 2 | Catalog and seed: four tracks, 38 milestones, rubric drafts | 2 weeks | Seed is idempotent and all data is flagged sample |
| 3 | Submissions and history | 1.5 weeks | File, link and text uploads are versioned as attempts |
| 4 | Evaluation engine and role plugins | 4 weeks | One task per role is evaluated end to end |
| 5 | Unlocking and corrections | 1.5 weeks | Fail, correct, resubmit, approve works for each demo task |
| 6 | Traceability and integration evaluations | 2 weeks | BA→QA coverage matrix is computed and shown |
| 7 | HR dashboard and reporting | 1.5 weeks | Management views are complete |
| 8 | Demo hardening | 1.5 weeks | The 10-minute script runs repeatably from a reset |

Phases overlap where dependencies allow (for example Phase 7 UI work can start during Phase 6). Expected calendar time is about 14–16 weeks. The content workstream runs throughout.

## 5. Phase details

### Phase 0 – Foundations

**Covers:** NFR-MNT-01, NFR-PORT-01, NFR-SEC-02.

- Monorepo layout from Architecture section 18.3, with `AGENTS.md`, `.env.example`, pre-commit hooks and CI (lint, types, tests, secret scan).
- Docker Compose with web, api, worker, postgres (pgvector), redis, s3 (RustFS, ADR-011); sandbox-runner and reference-app as stubs.
- Database schema v1 and Alembic migrations; every table has `is_sample`.
- OpenAPI skeleton and generated TypeScript client.
- JSON schemas for rubric versions, task templates and golden samples; a content validator command.
- ADRs 001–010 reviewed. ADR-007 (Celery or Arq) decided.
- Start the content workstream: name a trainer per track and agree the rubric authoring template.

**Exit:** healthy stack, CI green, schema and rubric format signed off.

### Phase 1 – Identity and shells

**Covers:** FR-IAM-01 to 03, NFR-SEC-03.

- Login, sessions, refresh, logout, rate limiting.
- Permission dependency layer and PostgreSQL row-level security on cohort and intern.
- Three route groups (intern, trainer, admin/HR) with shared design tokens and layout.
- Permission matrix tests: every endpoint is tested for allowed and denied roles.

**Exit:** four demo roles log in; cross-role access attempts return 403; tests prove it.

### Phase 2 – Catalog and seed

**Covers:** FR-CAT-01 to 04, FR-SMP-01, FR-SMP-02, FR-INT-01 to 03.

- Catalog read APIs, content loader and idempotent seed command.
- 4 role profiles, 4 courses, 38 milestones. Four demo tasks with full rubrics; 34 content-only tasks.
- Four demo users with prepopulated submissions and evaluation history, all flagged sample.
- Intern home, course map (locked, unlocked, complete) and task page showing the rubric in plain language.
- Sample-data ribbon and per-record tag components.

**Exit:** running the seed twice changes nothing; an intern sees their course map and task page; sample labelling is visible everywhere seeded data appears.

### Phase 3 – Submissions

**Covers:** FR-SUB-01 to 05, FR-INT-04.

- Signed uploads, artifact records with type, size and SHA-256.
- Attempt versioning, immutable earlier attempts, idempotency key.
- Validation: type, size, empty file, link reachability.
- Submission history UI.

**Exit:** an intern submits files, links and text, resubmits, and sees attempts 1, 2, 3 in history.

### Phase 4 – Evaluation engine and role plugins

The largest phase. Build in four slices, each a vertical slice that ends with a visible result in the evaluation view.

**4a. Engine core (about 1.5 weeks).** Covers FR-EVAL-01 to 07, 10.

- State machine with persisted, idempotent, resumable stages and SSE progress.
- Scoring service as a pure function with exhaustive tests (Architecture 8.5).
- Findings with rating caps; review gate rules (8.6).
- LLM gateway with caching, cost logging and **fixture mode**.
- Evidence verification and prompt-injection flagging.
- Shared `EvaluationResult` component (FR-EVU-01 to 08).

**4b. Developer chunking (about 1 week).** Covers FR-ROLE-01, 04.

- Sandbox runner MVP with security tests (escape, network, limits).
- Checkers: pytest visible and hidden, coverage, ruff, mypy, edge-case injection.
- Judge prompt for explanation and rationale; golden set; correction templates.

**4c. BA requirements and QA login tests (about 1 week, two engineers in parallel).**

- BA checkers: document parsing, requirement ID uniqueness, ambiguity lint, story format, Given/When/Then, NFR measurability. Guided feedback must not rewrite the answer.
- QA checkers: test-case parsing from the agreed template, execution against the reference app, seeded-defect detection rate, defect replay, scenario coverage. Reference app and defect catalogue delivered by the platform engineer.

**4d. UX homepage wireframe (about 0.5 week plus Figma access).** Covers FR-ROLE-03, 05.

- Figma extraction, contrast, text size and tap-target checks; screenshot fallback.
- Vision judge as advisory; review required in every case.

**Exit:** one task per role is evaluated end to end with real checkers, fixtures replay correctly, and the golden-set agreement meets the PRD targets or the gap is documented.

### Phase 5 – Unlocking and corrections

**Covers:** FR-FB-01 to 05, FR-REV-01 to 04, FR-PRG-01 to 03.

- Feedback structure (summary, strengths, three priorities, details) and respectful status language.
- Correction tasks from templates and the leak check.
- Trainer queue with side-by-side evidence, intern context card, override with reason and audit log.
- Milestone unlocking only on approval; competency scores updated from approved results.
- Message to trainer from the intern view.

**Exit:** for each demo task, fail → correction → resubmit → approve works with a trainer decision where required.

### Phase 6 – Traceability and integration

**Covers:** FR-XR-01 to 05 (P0), FR-XR-06 and 07 (P1).

- Tag parser (REQ-012 inside TC-045 or a Figma frame name), graph tables and queries.
- BA→QA coverage matrix with link-quality judgments by the AI.
- P1: BA→UX, UX→Dev, Dev→QA evaluations, similarity-suggested links with confirmation.

**Exit:** the coverage matrix shows which requirements have verifying tests and which do not, computed by graph query and reproducible.

### Phase 7 – HR dashboard and reporting

**Covers:** FR-HR-01 to 08.

- Cohort creation and tracks, cohort overview with reasons for each status.
- Failed (needs another pass) list, skills needing attention, dependency view, project status.
- Readiness definition applied and displayed with its inputs; tool-measured and AI judgments shown separately.
- Exports (P1).

**Exit:** management views complete; every number on screen is traceable to records.

### Phase 8 – Demo hardening

**Covers:** FR-SMP-03, FR-SMP-04, NFR-REL, NFR-A11Y, NFR-OBS.

- One-click reset and a scripted 10-minute run that executes in CI nightly.
- Recorded LLM fixtures as fallback; latency and failure-path rehearsals.
- Accessibility pass (automated and keyboard), security pass, performance check on the demo dataset.
- Usability sessions (6–8 participants) and fixes for top issues.

**Exit:** three consecutive clean rehearsals from reset.

## 6. Content workstream (critical path)

| Item | Per demo task | For the other 34 milestones |
| --- | --- | --- |
| Task description, objective, deliverables | Full | Full |
| Rubric criteria and weights | Full (weights from PRD Appendix A) | Draft |
| Level descriptors 0–4 per criterion | Full, written by the role expert | Later |
| Mandatory gates and threshold | Full | Later |
| Correction templates | One per criterion | Later |
| Golden set (good, average, poor, adversarial) with trainer scores | 8–12 samples | None |
| Prompts | Reviewed and versioned | Generic |
| Reference app defect catalogue | QA task only | n/a |
| Sample submissions and history for the dashboard | Per demo user | Optional |

Content changes go through pull requests like code. A trainer approves rubric and golden-set changes; golden-set regression runs on every change.

## 7. Working with AI coding agents

### 7.1 Principles

- Agents work from tickets, not from the whole PRD. A ticket links the exact PRD and architecture sections.
- Small, single-purpose pull requests (aim for under 400 changed lines).
- Tests come with the code. An agent may not mark work done without running the tests.
- When the specification is ambiguous, the agent stops and writes the question to `docs/open-questions.md` instead of guessing.

### 7.2 `AGENTS.md` (place at the repository root)

```
Project: AITMS multi-role training platform. Read before any task:
  PRD (requirements), Architecture Specification, Implementation Plan.

Hard rules
1. Never let LLM output set a final score. Scores come from the scoring service.
2. Never call an LLM provider SDK directly. Use the LLM gateway.
3. Never execute intern-supplied code outside the sandbox runner.
4. Never change published rubric files, weights or level descriptors
   without a human-approved ticket.
5. Never put secrets in the repository. Update .env.example only.
6. Seeded or demo records must set is_sample = true.
7. Every endpoint needs an authorisation test (allowed and denied roles).
8. Do not invent test results, evidence or metrics anywhere, including fixtures.

Workflow
- Reference requirement IDs (for example FR-EVAL-04) in commits and tests.
- Schema change => Alembic migration + updated docs.
- API change => regenerate OpenAPI and the TypeScript client.
- New dependency => state why in the PR description.
- If the spec is unclear, add a question to docs/open-questions.md and stop.

Definition of done
- CI green: lint, types, unit, contract, integration tests.
- Tests cover the happy path and at least two failure paths.
- UI changes pass automated accessibility checks and keyboard navigation.
- The demo script still runs.
```

### 7.3 Ticket template for agents

```
ID / Title:
Requirements: (PRD IDs)         Architecture refs: (section numbers)
Context: why this exists, in two or three sentences
In scope:                       Out of scope:
Acceptance criteria: (Given / When / Then, testable)
Test plan: unit, contract, integration, negative cases
Files or modules likely touched:
Dependencies:                   Risk level: low / medium / high
Human review required: yes / no (always yes for auth, RBAC, sandbox,
  scoring, migrations, prompts, rubrics)
```

### 7.4 Prompt pattern for an agent session

```
You are implementing ticket <ID> in the AITMS repository.
Read AGENTS.md and the referenced PRD and Architecture sections first.
Plan the change in a short list, then implement it in small commits.
Write the tests first where practical. Run lint, type checks and tests.
Do not touch files outside the listed modules unless you explain why.
If anything is ambiguous, stop and add a question to docs/open-questions.md.
Finish with: what changed, how you verified it, what you did not do.
```

### 7.5 Review policy for AI-written code

| Area | Review |
| --- | --- |
| Authentication, RBAC, row-level security | Tech lead, always |
| Sandbox runner and anything that executes code | Tech lead and platform engineer, always |
| Scoring service and the review gate | Tech lead, always |
| Database migrations | A second engineer, always |
| Prompts, rubrics, golden sets | Role expert and tech lead, always |
| UI components and standard CRUD endpoints | One engineer; automated checks must be green |

### 7.6 Anti-patterns to watch for

- Fixtures that were generated by the same model they are testing; record real outputs and review them by hand.
- Tests that assert the implementation instead of the requirement.
- Silent scope growth: features no ticket asked for.
- Hard-coded demo outputs that bypass the engine. The demo must run on the real pipeline with fixtures only replacing the LLM call.

## 8. First tickets (starter backlog)

| # | Ticket | Phase | Review |
| --- | --- | --- | --- |
| T-001 | Monorepo scaffold, Compose stack, `.env.example` | 0 | Tech lead |
| T-002 | CI: lint, types, tests, secret scan | 0 | Tech lead |
| T-003 | Database schema v1 and Alembic baseline | 0 | Second engineer |
| T-004 | OpenAPI skeleton and generated client | 0 | One engineer |
| T-005 | JSON schemas for rubric, task template, golden sample; validator command | 0 | Tech lead |
| T-006 | Auth: login, refresh, logout, rate limiting | 1 | Tech lead |
| T-007 | Permission dependency layer, row-level security, matrix tests | 1 | Tech lead |
| T-008 | App shells and design tokens (three route groups) | 1 | One engineer |
| T-009 | Catalog read APIs and content loader | 2 | One engineer |
| T-010 | Idempotent seed command with sample flags | 2 | Second engineer |
| T-011 | Intern home, course map, task page | 2 | One engineer |
| T-012 | Sample ribbon and tag components | 2 | One engineer |
| T-013 | Signed uploads and artifact records | 3 | Second engineer |
| T-014 | Submission attempts, idempotency, validation | 3 | Second engineer |
| T-015 | Scoring service with exhaustive tests | 4a | Tech lead |
| T-016 | Evaluation state machine, stage persistence, SSE | 4a | Tech lead |
| T-017 | LLM gateway: cache, cost log, fixture mode | 4a | Tech lead |
| T-018 | Evidence verification and injection flagging | 4a | Tech lead |
| T-019 | `EvaluationResult` shared component | 4a | One engineer |
| T-020 | Sandbox runner MVP and security tests | 4b | Tech lead and platform |

## 9. Decisions needed and owners

| Decision | Owner | Needed by |
| --- | --- | --- |
| Celery or Arq (ADR-007) | Tech lead | End of Phase 0 |
| Passing thresholds and mandatory gates per demo task | Product owner with role experts | Start of Phase 2 |
| Readiness definition for HR | Product owner | Start of Phase 7 |
| Attempt limits and escalation | Product owner | Start of Phase 5 |
| Whether submissions may go to the LLM provider | Product owner and security | Before Phase 4 |
| Figma access model | Tech lead | Start of Phase 4d |
| Hosting for demo and pilot, gVisor availability | Platform engineer | Mid Phase 3 |
| QA test-case submission template (CSV or YAML) | QA role expert and tech lead | Start of Phase 4c |
| Data retention and export policy | Product owner and HR | Before pilot |

## 10. Quality gates

| Gate | Checks |
| --- | --- |
| Every pull request | Lint, types, unit and contract tests, secret scan, migration check, accessibility check on UI changes |
| End of each phase | Exit criterion demonstrated live; open-questions log reviewed; ADRs updated |
| End of Phase 4 | Golden-set agreement reported per task; sandbox security suite green; evidence verification failure rate recorded |
| Before the management demo | Three clean rehearsals, fixture fallback tested by disabling the LLM, reset tested, sample labelling verified on every screen |

## 11. Risks to delivery

| Risk | Effect | Response |
| --- | --- | --- |
| Content (rubrics, golden sets) arrives late | Phase 4 plugins cannot be validated | Start in Phase 0; trainers named; weekly content review |
| Sandbox complexity | Phase 4b slips | Build MVP early with Docker and tighten with gVisor behind a feature flag; keep security tests from day one |
| Agent-generated code drifts from the spec | Rework | Ticket-based work, reference IDs, review policy, `AGENTS.md` hard rules |
| LLM variance or cost | Unstable scores | Anchored scale, caps from tools, caching, golden-set regression |
| Figma access delays | UX track incomplete | Screenshot fallback is a P1 deliverable, not an afterthought |
| Scope creep into P1 and P2 | Demo at risk | Phase gates; P0 list is the contract for the demo |
| Demo fragility | Failed management demo | Fixtures, reset, nightly scripted run, rehearsals |

## 12. Handover checklist for day one

- [ ] PRD, Architecture Specification and this plan reviewed by the tech lead.
- [ ] Repository created with branch protection and CI.
- [ ] Named owners: product owner, tech lead, four role experts.
- [ ] LLM API key in a secret manager; Figma access arranged.
- [ ] Draft rubrics for the four demo tasks from the project brief (weights in PRD Appendix A).
- [ ] Design tokens and the key screen direction from the design discussion shared with the frontend engineer and designer.
- [ ] Decisions list (section 9) scheduled in the project calendar.
- [ ] `AGENTS.md`, ticket template and prompt pattern copied into the repository.

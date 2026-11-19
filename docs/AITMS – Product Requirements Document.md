# AITMS – Product Requirements Document

Version 0.2 prototype · Draft for development handover · 8 November 2026

Companion documents: AITMS Architecture Specification · AITMS Implementation Plan

## 1. Purpose and how to use this document

This PRD defines what the AITMS prototype must do and how we will know it works. It is written for a development team working with AI coding agents, so every requirement has an ID, a priority and a testable outcome. Reference the IDs (for example FR-EVAL-03) in tickets, commits and tests.

Priority key: **P0** = needed for the management demo. **P1** = needed for a credible pilot. **P2** = later.

Items marked ASSUMPTION or OPEN QUESTION need a product owner decision before the related phase starts (see section 13).

## 2. Product vision

AITMS is a competency-based practical training and evaluation platform for IT interns. One shared engine supports several professional disciplines. Each discipline has its own modules, practical assignments, rubrics, objective checkers and acceptance criteria. The prototype covers four: Software Developer, Business Analyst, QA Engineer and UI/UX Designer.

Positioning for management: an AI-powered workforce competency development system, not an AI course platform.

What AITMS is not:

- Not a video-and-quiz LMS. Interns produce real work products and are evaluated on them.
- Not an answer machine. Feedback guides interns to improve their own work and never writes the corrected deliverable.
- Not a replacement for trainers. Trainers approve borderline results, all UX work and final deliverables.

## 3. Goals, non-goals and success measures

### 3.1 Goals

- G1. Evaluate practical work by what good looks like in each profession. No role is ever judged with another role's rubric.
- G2. Give interns specific, evidence-backed, respectful feedback and a targeted correction task.
- G3. Give trainers a fast, trustworthy review queue.
- G4. Give HR and management an honest view of progress, support needs and project readiness.
- G5. Show cross-role collaboration on one shared project, with traceability from requirement to design, code, test and defect.
- G6. Make adding a new role mostly configuration (rubrics, checkers, templates), not new code.

### 3.2 Non-goals (prototype)

- Production multi-tenancy, SSO, billing or native mobile apps.
- Automated hiring decisions, or ranking interns against each other.
- Judging visual design quality by AI alone.
- Roles beyond the four tracks (DevOps, Data Analyst and others come later).

### 3.3 Success measures

| Measure | Prototype target |
| --- | --- |
| Demo repeatability | The 10-minute script runs from a one-click reset three times in a row with no manual fixes |
| Loop completeness | All four demo tasks complete fail → correction → resubmit → approve |
| Score reproducibility | Same submission and rubric version: criterion ratings within one level on 95% of reruns (ASSUMPTION) |
| Trainer agreement | On golden sets, the pass / needs-another-pass outcome matches the trainer on at least 80% of samples (ASSUMPTION) |
| Evidence integrity | 100% of displayed evidence quotes exist in the submission |
| Latency (p90) | Developer task under 3 minutes; document-based tasks under 90 seconds |
| Security | Sandbox security tests show no escape and no network egress |

## 4. Users

These personas are hypotheses drawn from the project brief. Validate them in the usability sessions in section 10.

| Persona | Context | Needs | Likely worries |
| --- | --- | --- | --- |
| Intern | New joiner, being assessed | Know what to do next, understand feedback, fix and resubmit, see their own growth | Being judged unfairly by a machine, being compared with others |
| Trainer | Reviews many interns, little time | Fast queue, evidence beside the submission, override with a reason | Rubber-stamping, AI mistakes, missing context |
| HR / management | Oversees a batch and its readiness | Who needs support and why, readiness against clear criteria | Vanity charts, unreliable scores, privacy |
| Admin | Configures the platform | Manage cohorts, users, courses, rubrics | Breaking a published rubric |

### Roles and permissions

| Role | Can do | Cannot do |
| --- | --- | --- |
| Admin | Everything, including configuration, rubrics, audit log | – |
| HR | Create cohorts, add interns, view cohort reports and individual records in their cohort | Edit rubrics, override scores |
| Trainer | See assigned interns only; review, override with reason, write notes, log interventions | See unassigned interns, publish rubrics |
| Intern | See and submit own work, read own feedback | See anyone else's data |

## 5. Scope

**In scope (P0):** application shell and login; four-track catalog with 38 milestones; four fully built demo tasks (one per role); submissions with versioned attempts; evaluation engine with role plugins; correction and approval workflow; milestone unlocking; BA→QA coverage matrix; trainer queue; HR dashboard; admin authoring of courses, cohorts, enrollments and accounts; reset to an empty platform plus seeded accounts.

**In scope (P1):** rubric admin UI, remaining integration evaluations (BA→UX, UX→Dev, Dev→QA), self-consistency re-runs, golden-set regression in CI, skill profile, exports, audit log views.

**Out of scope:** full product evaluation (P2), additional roles, SSO, payments, native mobile.

## 6. Shared project and catalog

**Smart Knowledge Portal** is the common business scenario. Employees can search internal documents, ask questions about HR policies and technical procedures, receive answers based on approved documents, raise support requests when information is unavailable, and see the status of those requests. Four interns work on it from four professional angles.

| Track | Course | Milestones | Final deliverable |
| --- | --- | --- | --- |
| Developer | AI-Powered RAG Application Development | 10 | Working RAG application over approved documents |
| Business Analyst | Business Requirement Analysis and Documentation | 9 | SRS, user stories, process flows, acceptance criteria, traceability matrix |
| QA Engineer | Software Testing and Quality Engineering | 10 | Test suite, execution report, defect log, automated regression tests |
| UI/UX Designer | User Experience and Interface Design | 9 | Research, flows and high-fidelity prototype |

The catalog contains 38 milestones. Four are **demo-depth** (fully built with rubric, checkers, golden set and correction templates). The other 34 are **content-only** in P0 (description, objective, deliverables and rubric text, evaluated manually or by a basic AI rubric).

| Demo-depth task | Milestone | Why this one |
| --- | --- | --- |
| Developer: implement chunking | Dev 3 | Fully testable by code, shows sandbox and hidden tests |
| BA: identify requirements for the portal | BA 3 | Shows document checks and guided feedback |
| QA: test login and search | QA 3 | Shows platform-executed tests and seeded defects |
| UX: knowledge portal homepage wireframe | UX 6 | Shows advisory AI plus mandatory human review |

## 7. Functional requirements

### 7.1 Identity and access (FR-IAM)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-IAM-01 | Email and password login with secure sessions | P0 |
| FR-IAM-02 | Four roles with a permission matrix enforced on the server, not only in the UI | P0 |
| FR-IAM-03 | Interns see only their own data; trainers only assigned interns; HR only their cohorts | P0 |
| FR-IAM-04 | Audit log for logins, overrides, rubric publishing and exports | P1 |
| FR-IAM-05 | Single sign-on | P2 |

### 7.2 Catalog and rubrics (FR-CAT)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-CAT-01 | Role profiles, courses, milestones and task templates stored as versioned configuration | P0 |
| FR-CAT-02 | Each task template defines: description, learning objective, typed expected deliverables, criteria with anchored 0–4 level descriptors, weights, passing threshold, mandatory acceptance criteria (gates), checker list, correction templates | P0 |
| FR-CAT-03 | Rubric versions are immutable once published; every evaluation pins the rubric version | P0 |
| FR-CAT-04 | Seeding from JSON files with an idempotent script (4 tracks, 38 milestones). **Changed 8 Nov 2026:** the drafted YAML in content/ is a one-time, create-only import (`python -m app.content.cli import`) that never overwrites edits made in the app. Courses, milestones, tasks, manifests and rubrics are authored in the app. Role profiles and checker lists stay in code | P0 |
| FR-CAT-05 | Admin UI to draft, validate and publish rubric versions. **Changed 8 Nov 2026:** pulled into the prototype and widened to authoring of courses, milestones, tasks and deliverable manifests. A published rubric is frozen and versioned, and publishing is audited | P0 |

Note (8 Nov 2026): HR and admins create cohorts, enroll interns and create accounts (HR: interns only) in the app. An intern can be enrolled in several courses at once. Enrolling creates the intern's milestone progress and task instances, and adding milestones or tasks to a course syncs enrolled interns. Implemented in code, not yet verified.

### 7.3 Intern experience (FR-INT)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-INT-01 | Home shows the assigned course, current milestone and task with one primary action. **Note 8 Nov 2026:** an intern can be enrolled in several courses. Home shows a hero for the course that most needs attention and every enrolled course with a status (In progress, Not started, Waiting for review, Complete) | P0 |
| FR-INT-02 | Course map (one page per course, reached from "My courses") shows locked, unlocked and complete milestones; locked ones explain what unlocks them | P0 |
| FR-INT-03 | Task page shows brief, objective, deliverables and the rubric in plain language before the intern starts | P0 |
| FR-INT-04 | Submission history with attempt number, status and result | P0 |
| FR-INT-05 | Evaluation view as specified in section 8 | P0 |
| FR-INT-06 | Ask my trainer: send a message from a task or evaluation | P0 |
| FR-INT-07 | Disagree with a criterion result, with a comment that goes to the trainer queue | P1 |
| FR-INT-08 | Skill profile with per-competency bars and a baseline marker from the first assessment | P1 |

### 7.4 Submissions (FR-SUB)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-SUB-01 | Accept file, link and pasted-text artifacts; store type, size and SHA-256 | P0 |
| FR-SUB-02 | Each resubmission is a new attempt; earlier attempts are immutable | P0 |
| FR-SUB-03 | Validate type and size per task, link reachability and empty files; malware scan is P1 | P0 |
| FR-SUB-04 | Submission returns immediately; evaluation runs asynchronously with live progress | P0 |
| FR-SUB-05 | Submission content is data only and is never treated as instructions to the AI | P0 |

### 7.5 Evaluation engine (FR-EVAL)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-EVAL-01 | Each run is a persisted state machine with stages: validation, completeness, objective checks, AI rubric, scoring, feedback, correction, review gate, approval. Stages are idempotent and resumable | P0 |
| FR-EVAL-02 | Objective results come from real tools. The AI cannot invent or change them | P0 |
| FR-EVAL-03 | The AI rubric stage returns, in a strict schema: per-criterion rating (0–4), verbatim evidence, failed acceptance criteria, feedback, correction, confidence, review flag, next action | P0 |
| FR-EVAL-04 | Scores are computed in code from ratings, weights, mandatory gates and threshold. The AI never sets the final score | P0 |
| FR-EVAL-05 | Every evidence quote is checked against the submission. A failed check lowers confidence and forces human review | P0 |
| FR-EVAL-06 | Each run records rubric version, prompt version, model ID, checker versions, tokens, cost and latency | P0 |
| FR-EVAL-07 | The role profile selects checkers and judge prompt. A test proves no role is evaluated with another role's rubric | P0 |
| FR-EVAL-08 | Feedback is checked so it does not contain the corrected deliverable | P0 |
| FR-EVAL-09 | Instruction-like text inside a submission is flagged and shown to the trainer | P0 |
| FR-EVAL-10 | A fake-LLM fixture mode exists for tests and as a demo fallback | P0 |
| FR-EVAL-11 | Re-run borderline results 2–3 times and use the consistent outcome | P1 |
| FR-EVAL-12 | Golden-set regression runs in CI when a rubric or prompt changes | P1 |

### 7.6 Role profiles (FR-ROLE)

| Role | Objective checks (tools) | AI-judged | Human review |
| --- | --- | --- | --- |
| Developer | pytest in sandbox with visible and hidden tests, coverage, ruff and mypy, edge-case injection (empty text, overlap larger than chunk, unicode) | Explanation quality, design rationale | Borderline scores |
| Business Analyst | Document parsing, unique requirement IDs, ambiguity-word lint, user-story format, Given/When/Then pattern, measurable NFRs | Completeness against the brief, clarity, consistency, testability | Final SRS (P1) |
| QA Engineer | Platform runs the intern's tests against the reference app, seeded-defect detection rate, replay of defect steps, scenario coverage against requirements | Test-case quality, severity classification | Sampled |
| UI/UX Designer | Figma API extraction (frames, components, styles), contrast, text size, tap-target size, flow-to-requirement coverage | Advisory rubric on research, flows and screenshots | **Always** |

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-ROLE-01 | The four demo tasks have the full pipeline, golden sets and correction templates | P0 |
| FR-ROLE-02 | QA: a test counts as executed only if the platform ran it. Expected results written by the intern are not execution | P0 |
| FR-ROLE-03 | UX: AI and automated findings are advisory. Approval needs a trainer | P0 |
| FR-ROLE-04 | Developer code and intern-supplied tests run only in the sandbox | P0 |
| FR-ROLE-05 | UX screenshot upload works when a Figma link is unavailable | P1 |

### 7.7 Feedback and corrections (FR-FB)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-FB-01 | Feedback order: status, one-line summary, strengths with evidence, up to three priority improvements, per-criterion detail | P0 |
| FR-FB-02 | Each failed criterion creates a correction task from a template with guiding questions and what to resubmit, without giving the answer | P0 |
| FR-FB-03 | Every finding is labelled: Measured by tests, Read by AI, or Reviewed by a trainer (named) | P0 |
| FR-FB-04 | Status language is respectful: Needs another pass, never Failed | P0 |
| FR-FB-05 | Trainer can add a personal note shown under their name | P1 |

### 7.8 Trainer review (FR-REV)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-REV-01 | Queue sorted by risk and waiting time, showing why each item was flagged | P0 |
| FR-REV-02 | Side-by-side view: AI evidence and the submission | P0 |
| FR-REV-03 | Approve, request revision, or override; override needs a reason and is audit-logged | P0 |
| FR-REV-04 | Intern context card: attempt history and earlier weak criteria | P0 |
| FR-REV-05 | Intervention log: message, call, extra task | P1 |
| FR-REV-06 | AI and trainer agreement rate view | P1 |

### 7.9 Progression (FR-PRG)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-PRG-01 | The next milestone unlocks only after approval | P0 |
| FR-PRG-02 | Fail → correction → resubmit → approve works end to end | P0 |
| FR-PRG-03 | Competency scores update from approved evaluations | P0 |
| FR-PRG-04 | Maximum attempts with escalation to a trainer | P1 |

### 7.10 Cross-role integration and traceability (FR-XR)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-XR-01 | A shared project holds the approved output of each role | P0 |
| FR-XR-02 | Traceability graph with node types: requirement, story, acceptance criterion, design frame, endpoint, dev task, test case, defect; relations: satisfies, designs, implements, verifies, reveals | P0 |
| FR-XR-03 | Interns tag IDs explicitly (for example REQ-012 inside test case TC-045); the platform parses the tags | P0 |
| FR-XR-04 | BA→QA coverage matrix computed by graph query: which requirements have verifying test cases | P0 |
| FR-XR-05 | The AI judges only whether a link is a good one (does the test really verify the requirement), never whether a link exists | P0 |
| FR-XR-06 | Similarity-suggested links, confirmed by a person | P1 |
| FR-XR-07 | BA→UX, UX→Dev and Dev→QA integration evaluations | P1 |
| FR-XR-08 | Full product evaluation | P2 |

### 7.11 Admin and HR (FR-HR)

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-HR-01 | Create a cohort, add interns, assign tracks | P0 |
| FR-HR-02 | Cohort overview: per intern track, progress, status and the reason for the status | P0 |
| FR-HR-03 | Evaluation history and the list of evaluations needing another pass | P0 |
| FR-HR-04 | Skills needing attention, across the cohort | P0 |
| FR-HR-05 | Cross-role dependency view and final project status | P0 |
| FR-HR-06 | Readiness is defined explicitly and shown with its inputs | P0 |
| FR-HR-07 | Reports separate tool-measured results from AI judgments | P0 |
| FR-HR-08 | Export to CSV and PDF | P1 |

### 7.12 Sample data (FR-SMP): withdrawn

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-SMP-01 | ~~Four demo users, each on one track: Developer Intern 01, Business Analyst Intern 01, QA Intern 01, UI/UX Intern 01, with prepopulated submissions and evaluation history~~ **Withdrawn 8 Nov 2026** | – |
| FR-SMP-02 | ~~Every seeded record carries is\_sample = true. The UI shows a page banner and a per-record SAMPLE tag~~ **Withdrawn 8 Nov 2026** | – |
| FR-SMP-03 | ~~One-click reset to the demo state~~ **Withdrawn 8 Nov 2026**; replaced by a reset to an empty platform plus seeded accounts | – |
| FR-SMP-04 | ~~Sample figures are never presented as real assessment results~~ **Withdrawn 8 Nov 2026** | – |

**Withdrawn on 8 November 2026 by the product owner.** Reason: the platform has no sample data. The only seeded data are seven user accounts (one intern per track, a trainer, HR, an admin), the four role profiles and the storage bucket (`python -m app.seed.bootstrap`). There is no is\_sample column, no SAMPLE ribbon or tag and no demo-history command. The point of FR-SMP-04 is kept by construction: no scores, findings or approvals are ever fabricated, because none are seeded. The demo reset returns the platform to empty plus the seeded accounts. The IDs are not reused.

## 8. Evaluation view (one shared component)

One component renders any role's evaluation from the result schema. There are no per-role screens.

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-EVU-01 | Shows status in plain words with a one-line summary before any number | P0 |
| FR-EVU-02 | Shows What is working first, then the top three things to work on; remaining items collapsed | P0 |
| FR-EVU-03 | Criterion bars carry words as well as numbers, for example Level 3 of 4: handles overlap, misses empty input | P0 |
| FR-EVU-04 | Each criterion expands to its evidence quote, highlighted in the intern's own submission | P0 |
| FR-EVU-05 | Shows the finding source label from FR-FB-03 | P0 |
| FR-EVU-06 | A clear review badge: Trainer review pending, with the reason and an expected time | P0 |
| FR-EVU-07 | Actions: Start correction, I disagree (P1), Ask a question | P0 |
| FR-EVU-08 | Meaning is never carried by colour alone; full keyboard operation; WCAG 2.2 AA contrast | P0 |

## 9. Non-functional requirements

| ID | Area | Requirement |
| --- | --- | --- |
| NFR-SEC-01 | Security | Intern code runs only in a sandbox: no network, CPU, memory and time limits, non-root, read-only image, ephemeral volumes |
| NFR-SEC-02 | Security | Secrets only in environment variables or a secret manager; none in the repository |
| NFR-SEC-03 | Security | Signed upload URLs, file type and size limits, rate limiting on auth and submission endpoints |
| NFR-SEC-04 | Security | Prompt-injection defences: delimited data blocks, strict output schema, flagging |
| NFR-PRV-01 | Privacy | Submissions and evaluations visible only to the intern, assigned trainer and permitted HR; retention rule documented |
| NFR-PRV-02 | Privacy | Interns can see what HR can see about them |
| NFR-PERF-01 | Performance | UI pages respond in under 1 second at p90 on the demo dataset; evaluation latency per section 3.3 |
| NFR-REL-01 | Reliability | A crashed worker resumes an evaluation from its last completed stage |
| NFR-REL-02 | Reliability | If the LLM provider fails, the run waits and retries, then flags for human review. It never invents a result |
| NFR-OBS-01 | Observability | Every run is traced; metrics for stage latency, LLM cost per evaluation, trainer-override rate, review-flag rate, queue depth |
| NFR-A11Y-01 | Accessibility | WCAG 2.2 AA for all screens, checked with automated tests and manual keyboard passes |
| NFR-MNT-01 | Maintainability | OpenAPI-first; typed end to end; adding a role needs configuration plus plugins only |
| NFR-COST-01 | Cost | Cache LLM calls by content hash; small model for validation, larger model only for the rubric stage; cost per evaluation recorded |
| NFR-PORT-01 | Portability | The whole stack runs locally with Docker Compose; the LLM provider sits behind a gateway so it can be swapped |

## 10. UX requirements

The visual and interaction direction was agreed in the design discussion. Summary for implementers:

- **Intern view:** bento-style cards by importance (current task is largest). Locked milestones shown as a trail, not a grid. No leaderboards, streak pressure or cohort comparisons.
- **Trainer and HR views:** dense, table-first, keyboard-friendly, with a context card per intern.
- **Tone:** specific, calm, human. Examples: Day 9 of 30. You are on chunking. Needs another pass, not Failed. A trainer will take a second look, not Low confidence.
- **Visual language (v0.3, "Soft depth", 8 Nov 2026):** soft lavender-grey canvas, floating white cards with large radii and soft shadows, solid ink primary buttons, violet for links and focus, a pastel colour per track, Plus Jakarta Sans for the interface, Source Serif 4 for human words, monospace for code and quoted evidence. Avoid gradient hero cards, glass effects, emoji headings, stock illustrations and radar charts. See the UI Design Brief.
- **Honesty:** no fake precision such as 87% confidence. Say what a trainer will double-check and why.
- **Sample data:** none (FR-SMP withdrawn 8 Nov 2026). Empty states carry a next step instead.

### Usability validation plan

Run 6–8 short sessions (interns across tracks, two trainers, one HR user) before the pilot. Tasks: an intern reads a weak result and states the next action within 30 seconds; a trainer finds the riskiest item in the queue; HR finds who needs support and why. Open questions to settle by observation: does leading with a summary instead of a score feel caring or evasive; does Needs another pass feel honest; do worded bars beat a radar chart.

## 11. Management demo acceptance (10 minutes)

| Minute | Scenario | Must be visible |
| --- | --- | --- |
| 1 | HR creates a batch, adds four interns, assigns tracks | FR-HR-01 |
| 2–3 | Developer submits chunking code | Sandbox test results, AI feedback, correction task (FR-EVAL, FR-FB) |
| 4–5 | BA submits requirements | Ambiguity lint, missing requirements, guided feedback with no rewritten answer |
| 6–7 | QA submits test cases | Platform-executed results, missing scenarios, seeded-defect detection rate |
| 8 | UX submits wireframe | Accessibility findings, advisory AI, mandatory trainer review badge |
| 9–10 | HR dashboard | Progress, evaluation history, readiness with inputs, BA→QA coverage matrix |

Fallback: recorded LLM fixtures keep the demo working if the provider is unavailable. A reset returns the platform to empty plus the seeded accounts (changed 8 Nov 2026); the demo content is then authored or imported before the script runs.

## 12. Appendix A: demo task rubrics (weights)

These weights come from the project brief. Level descriptors (0–4) for each criterion are authored with trainers during Phase 2. Passing threshold is an assumption (70 of 100 plus all mandatory gates) pending section 13.

| Developer: chunking | Weight | BA: requirements | Weight |
| --- | --- | --- | --- |
| Chunking logic | 25 | Business understanding | 15 |
| Overlap handling | 20 | Requirement completeness | 20 |
| Metadata preservation | 15 | Functional requirement clarity | 20 |
| Edge cases | 15 | Non-functional requirements | 15 |
| Unit tests | 15 | User story quality | 10 |
| Code quality | 10 | Acceptance criteria | 10 |
|  |  | Documentation quality | 10 |

| QA: login and search | Weight | UX: homepage wireframe | Weight |
| --- | --- | --- | --- |
| Test scenario coverage | 20 | User problem understanding | 15 |
| Test case accuracy | 20 | User journey and flow | 15 |
| Negative testing | 15 | Information architecture | 15 |
| API testing | 15 | Wireframe usability | 20 |
| Defect identification | 15 | Visual consistency | 15 |
| Automation quality | 10 | Accessibility | 10 |
| Documentation | 5 | Usability testing | 10 |

## 13. Assumptions, risks and open questions

### Decisions needed from the product owner

1. **Passing threshold and gates** per task. Proposed default: 70 of 100 plus all mandatory criteria met.
2. **Readiness definition** for the HR dashboard (for example: all P0 milestones approved, no open correction tasks, final deliverable approved by a trainer).
3. **Attempt limits** and what happens after the limit (escalation to a trainer is proposed).
4. **Data retention** for submissions and evaluations, and who may export them.
5. **Trainer capacity**: who reviews UX work and how quickly (affects the review badge promise).
6. **Figma access**: personal access tokens or an organisation app; screenshot fallback is already planned.
7. **LLM provider and data policy**: OpenAI is the stated provider. Confirm whether intern submissions may be sent to it.

### Risks

| Risk | Mitigation |
| --- | --- |
| AI scoring variance | Anchored scales, scores computed in code, golden sets, override-rate tracking |
| UX judged by AI | Advisory only; trainer approval required |
| Hallucinated evidence | Substring verification; forced review on failure |
| Interns gaming the rubric | Rubric is visible; hidden tests and held-out golden sets are not |
| Solution leakage in feedback | Leak-check pass and a guide-don't-complete prompt policy |
| Sandbox escape | gVisor, no network, limits, security tests in CI |
| Content workload (rubrics, golden sets, templates) | Start a content workstream with trainers in Phase 0; it is the critical path |
| Demo fragility | Recorded fixtures, one-click reset, rehearsal runs |

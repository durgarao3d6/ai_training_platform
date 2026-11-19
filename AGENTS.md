Project: AITMS multi-role training platform. Read before any task:
  PRD (requirements), Architecture Specification, Implementation Plan (all in docs/).
  Spec and task list: .kiro/specs/aitms-prototype/

Hard rules
1. Never let LLM output set a final score. Scores come from the scoring service.
2. Never call an LLM provider SDK directly. Use the LLM gateway.
3. Never execute intern-supplied code outside the sandbox runner.
4. Never change published rubric files, weights or level descriptors
   without a human-approved ticket.
5. Never put secrets in the repository. Update .env.example only.
6. Seed no sample or demo records. The only seeded data are the bootstrap
   accounts and the role profiles (python -m app.seed.bootstrap). Course
   content (courses, milestones, tasks, rubrics) is authored in the app.
7. Every endpoint needs an authorisation test (allowed and denied roles).
8. Do not invent test results, evidence or metrics anywhere, including fixtures.

Workflow
- Reference requirement IDs (for example FR-EVAL-04) in commits and tests.
- Schema change => Alembic migration + updated docs.
- API change => regenerate OpenAPI and the TypeScript client.
- New dependency => state why in the PR description.
- If the spec is unclear, add a question to docs/open-questions.md and stop.
- Run tooling through Docker only (make / scripts/dev.ps1). Nothing is installed on the host.

Definition of done
- CI green: lint, types, unit, contract, integration tests.
- Tests cover the happy path and at least two failure paths.
- UI changes pass automated accessibility checks and keyboard navigation.
- The demo script still runs.

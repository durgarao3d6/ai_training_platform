# Single-cohort pilot release checks

Use the Verification workflow on every pull request to check lint, types, API contract drift,
PostgreSQL and object-storage integration, and the Chromium trainer review path. The browser test
uses a synthetic BA fixture in a disposable Compose database. The approved BA demo follows
[the separate walkthrough](ba-demo.md).

## Deployment

- Use a dedicated environment and database with HTTPS, secure cookies, and a restricted network.
  Provide JWT, database and object-storage secrets through deployment configuration. Keep object
  storage and PostgreSQL off the public network.
- Run `alembic upgrade head` with the migration role before switching application traffic to
  the release. Run the API with the scoped application role. Provision pilot accounts individually.
- Confirm the trainer and intern accounts are assigned to the intended cohort. Use the approved
  BA materials and verify course publication before enrolling interns.
- Review production dependency advisories. Record the results with the release candidate.

## Recovery and monitoring

- Back up PostgreSQL and the object store. Keep the database and finalized artifact backups
  together under the same recovery point so restored attempts reference available objects.
- Restore both into a disposable environment. Run migrations as needed, verify that an authorized
  trainer can read the queue and download a known artifact, and check its recorded SHA-256.
- Check API availability, unexpected errors, object-store access errors, and review queue age.
  Record the owner and response procedure for each alert.

Record the CI run, approved rubric version, BA walkthrough, and restore drill before tagging
`v1.0.0`.

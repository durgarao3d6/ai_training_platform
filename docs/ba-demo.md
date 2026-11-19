# Business Analyst portfolio demo

This walkthrough demonstrates a trainer reviewing requirements for a company policy portal. Use a dedicated local database and the bootstrap accounts. The portfolio flow uses trainer decisions and records the rubric version used for each attempt.

## Prepare the course

1. Start the stack, run migrations, and seed the accounts and role profiles as described in the root README. Begin with the BA assignment brief in `content/tasks/ba.yaml` under `ba.requirements`.
2. Obtain BA role-expert approval for the assignment, its deliverable manifest, and the rubric. The rubric draft is in `content/drafts/rubrics/ba.requirements.yaml`. Record the reviewer and date on the release issue. Approve each criterion's 0–4 descriptions, mandatory gates, and correction guidance before publication.
3. As an admin, create a BA course with an approved opening milestone for the requirements assignment and an approved second milestone to show unlocking. The BA course publication gate currently requires nine approved milestones with a task in each. Use approved material for the other milestones, or obtain a product decision and implement an explicit demo-course rule before running a smaller course.
4. Create the requirements task in the opening milestone. Add the requirements document and process flow deliverables, both with text enabled so the walkthrough can run without file preparation. Paste the reviewed rubric as JSON through the task's rubric editor and publish it.
5. Publish the course. As HR or admin, create a cohort, assign the seeded trainer, and enroll the seeded BA intern in the published course.

## Walk through the review

1. Sign in as the BA intern. Open the requirements task and hand in a short requirements document and a process flow. For the first attempt, leave out the acceptance criteria so the trainer has a specific issue to call out.
2. Sign in as the assigned trainer in a separate browser session. Open **Review queue**, select the attempt, and verify the requirements and rubric version are visible. Choose **Request revision**. Ask the intern to add a Given/When/Then acceptance criterion that covers the case where a policy search has no approved answer.
3. In the intern session, choose **Refresh progress**. Verify that the feedback is shown and the second milestone is locked. Submit a new attempt with the requested criterion.
4. In the trainer session, refresh the queue and open the new attempt. Verify the revision is present, then approve it.
5. In the intern session, refresh progress. Verify the earlier feedback is still in the attempt history, the new attempt is approved, and the next milestone is open.

Record the course identifier, rubric version, reviewer approval, and the result of the walkthrough before closing the demo issue. Resetting a local Compose project removes its data, so run repeatability checks in a disposable project.

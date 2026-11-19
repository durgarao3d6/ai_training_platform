import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const base = process.env.WEB_BASE_URL ?? "http://localhost:3000";
const feedback = "Add acceptance criteria for a search with no approved answer.";

async function signIn(page: Page, email: string, destination: string) {
  const password = process.env.DEMO_PASSWORD;
  if (!password) throw new Error("The browser test requires DEMO_PASSWORD from the disposable stack");
  await page.goto(`${base}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(`${base}/${destination}`);
}

async function recordDecision(page: Page, decision: "request_revision" | "approve") {
  await page.getByLabel("Decision").selectOption(decision);
  if (decision === "request_revision") {
    await page.getByLabel("What should the intern revise?").fill(feedback);
  }
  const save = page.getByRole("button", { name: "Save decision" });
  await save.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Recorded decision" })).toBeVisible();
}

test("BA intern revises an attempt and trainer approval unlocks the next milestone", async ({ browser }) => {
  const internContext = await browser.newContext();
  const trainerContext = await browser.newContext();
  const intern = await internContext.newPage();
  const trainer = await trainerContext.newPage();
  try {
    await signIn(intern, "intern.ba@example.com", "intern");
    await intern.getByRole("link", { name: "Continue the task" }).click();
    const requirements = intern.getByLabel("Text for Requirements");
    await requirements.fill("A policy search shows answers from approved sources.");
    await intern.getByRole("button", { name: "Hand in this attempt" }).click();
    await expect(intern.getByText("Attempt 1", { exact: true })).toBeVisible();

    await signIn(trainer, "trainer@example.com", "trainer");
    await trainer.getByRole("link", { name: "Requirements test 1" }).click();
    await expect(trainer.getByRole("heading", { name: "Rubric version 1" })).toBeVisible();
    await expect(trainer.getByText("A policy search shows answers from approved sources.")).toBeVisible();
    const report = await new AxeBuilder({ page: trainer })
      .include("main")
      .withRules(["label", "button-name", "link-name", "aria-valid-attr-value"])
      .analyze();
    expect(report.violations).toEqual([]);
    await recordDecision(trainer, "request_revision");

    await intern.getByRole("button", { name: "Refresh progress" }).click();
    await expect(intern.getByText(feedback)).toBeVisible();
    await expect(intern.getByRole("link", { name: "Next milestone", exact: false })).toHaveCount(0);
    await requirements.fill("Given no approved answer, when an intern searches, then show a support request link.");
    await intern.getByRole("button", { name: "Hand in this attempt" }).click();
    await expect(intern.getByText("Attempt 2", { exact: true })).toBeVisible();

    await trainer.getByRole("link", { name: "Back to review queue" }).click();
    await trainer.getByRole("link", { name: "Requirements test 1" }).click();
    await expect(trainer.getByRole("heading", { name: "Review attempt 2" })).toBeVisible();
    await recordDecision(trainer, "approve");

    await intern.getByRole("button", { name: "Refresh progress" }).click();
    await expect(intern.getByRole("link", { name: "Next milestone · Milestone 2" })).toBeVisible();
  } finally {
    await internContext.close();
    await trainerContext.close();
  }
});

import { expect, test } from "@playwright/test";

test("dashboard exposes repair workflow without overflow", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "OhOhOps" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Repair guarantees" })).toContainText(
    "Tree Sitter AST chunks",
  );
  await expect(page.getByText("Dual model consensus", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Automatic rollback", { exact: true })).toBeVisible();

  const widths = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(widths.scroll).toBe(widths.client);
});

test("sunfire theme persists across reloads", async ({ page }) => {
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("primary pages and backend health load", async ({ page, request }) => {
  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: "Set up OhOhOps" })).toBeVisible();

  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Access keys" })).toBeVisible();

  const apiBase = process.env.OHOHOPS_API_BASE_URL ?? "http://127.0.0.1:8000";
  const response = await request.get(`${apiBase}/api/v1/health`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.dependencies.embedding_dimension).toBe("3072");
});

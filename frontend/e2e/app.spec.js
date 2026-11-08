import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";

// Local .env is ignored by Git. CI supplies credentials in environment variables.
const envText = fs.existsSync("../.env")
  ? fs.readFileSync("../.env", "utf8")
  : "";
const password =
  process.env.ADMIN_PASSWORD || envText.match(/^ADMIN_PASSWORD=(.+)$/m)?.[1];
const username = process.env.ADMIN_USERNAME || "admin";

test("public dashboard, keyboard selection, filters, mobile, print and accessibility", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator(".screen-rows tr").first()).toBeVisible();
  await page.getByRole("button", { name: "Wszystkie", exact: true }).click();
  const value = page.locator(".screen-rows .value-btn").first();
  await value.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("selected-point")).toBeVisible();
  await expect(value).toHaveAttribute("aria-pressed", "true");
  const before = await page.locator("thead th").count();
  await page.locator(".legend-item input").first().uncheck();
  await expect(page.locator("thead th")).toHaveCount(before - 1);
  await page.locator(".legend-item input").first().check();
  await expect(page.locator("thead th")).toHaveCount(before);
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
  await page.evaluate(() => document.activeElement?.blur());
  fs.mkdirSync("../artifacts", { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../artifacts/dashboard-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 360, height: 800 });
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/dashboard-mobile.png",
    fullPage: true,
  });
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".topbar")).toBeHidden();
  await expect(page.locator(".filter-bar")).toBeHidden();
  await expect(page.locator(".print-rows")).toBeVisible();
  await page.pdf({
    path: "../artifacts/raport-pomiarow.pdf",
    format: "A4",
    landscape: true,
    printBackground: true,
  });
  expect(errors).toEqual([]);
});

test("admin lifecycle, sensor key, live measurements, revocation and logout", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrator", exact: true })
    .click();
  await page.getByLabel("Login", { exact: true }).fill(username);
  await page.getByLabel("Hasło", { exact: true }).fill(password);
  await page.getByLabel("Hasło", { exact: true }).press("Enter");
  await expect(
    page.getByRole("button", { name: "Wyloguj", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Serie", exact: true }).click();
  await page.getByRole("button", { name: "Dodaj serię", exact: true }).click();
  await page.getByLabel("Nazwa serii", { exact: true }).fill("E2E obserwacja");
  await page.getByRole("button", { name: "Zapisz serię" }).click();
  await expect(
    page.getByRole("heading", { name: "E2E obserwacja", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Czujniki", exact: true }).click();
  await page.getByRole("button", { name: "Dodaj czujnik" }).click();
  await page.getByLabel("Nazwa czujnika").fill("E2E termometr");
  await page
    .getByLabel("Seria pomiarowa")
    .selectOption({ label: "E2E obserwacja" });
  await page
    .getByRole("button", { name: "Zarejestruj czujnik", exact: true })
    .click();
  const keyInput = page.getByLabel("Klucz API", { exact: true });
  await expect(keyInput).toBeVisible();
  const key = await keyInput.inputValue();
  expect(key.length).toBeGreaterThanOrEqual(32);
  await page.getByRole("button", { name: "Klucz zapisany, zamknij" }).click();
  await page.getByRole("button", { name: "Pulpit", exact: true }).click();
  const response = await request.post("/api/measurements", {
    headers: { "X-API-Key": key },
    data: { value: 23.456 },
  });
  expect(response.status()).toBe(201);
  await expect(
    page.locator(".metric-card").filter({ hasText: "E2E obserwacja" }),
  ).toContainText("23,46", { timeout: 12000 });
  await page.getByRole("button", { name: "Czujniki", exact: true }).click();
  await page
    .getByRole("button", {
      name: "Wyrejestruj czujnik E2E termometr",
      exact: true,
    })
    .click();
  await page.getByRole("button", { name: "Wyrejestruj", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "E2E termometr", exact: true }),
  ).toHaveCount(0);
  expect(
    (
      await request.post("/api/measurements", {
        headers: { "X-API-Key": key },
        data: { value: 22 },
      })
    ).status(),
  ).toBe(401);
  await page.getByRole("button", { name: "Serie", exact: true }).click();
  await page
    .getByRole("button", { name: "Usuń serię E2E obserwacja", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Usuń serię i pomiary", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "E2E obserwacja", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Wyloguj", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Administrator", exact: true }),
  ).toBeVisible();
});

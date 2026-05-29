import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test.describe.configure({ mode: "serial" });

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

test("source-results：真实最小闭环返回来源结果", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Suton" })).toBeVisible();

  await page.getByLabel("新建项目").fill(`高等数学（上）期末复习 ${Date.now()}`);
  await page.getByRole("button", { name: "创建项目" }).click();
  await expect(page.getByRole("heading", { name: /高等数学/ })).toBeVisible();

  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));
  await expect(page.getByText("text-layer-material.pdf")).toBeVisible();
  await expect(page.getByTestId("document-status").filter({ hasText: "完成" })).toBeVisible({ timeout: 90_000 });

  const question = readFileSync(resolve("tests/fixtures/question.txt"), "utf-8").trim();
  await page.getByTestId("question-text").fill(question);
  await page.getByRole("button", { name: "查找资料依据" }).click();

  await expect(page.getByRole("heading", { name: "资料依据" })).toBeVisible();
  await expect(page.getByText("pgvector 相似度").first()).toBeVisible({ timeout: 30_000 });
  const pdfLink = page.getByRole("link", { name: "PDF" }).first();
  await expect(pdfLink).toHaveAttribute("href", /\/documents\/\d+\/file#page=\d+/);
});

test("empty-results：明显无关题目展示空结果", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /高等数学/ })).toBeVisible();

  const question = readFileSync(resolve("tests/fixtures/unmatched-question.txt"), "utf-8").trim();
  await page.getByTestId("question-text").fill(question);
  await page.getByRole("button", { name: "查找资料依据" }).click();

  await expect(page.getByText("没有匹配资料。系统不会生成无来源答案。")).toBeVisible({ timeout: 30_000 });
});

test("missing-source-filter：缺少来源字段的候选不从 API 返回", async ({ request }) => {
  const questionId = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_missing_source.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();

  const response = await request.get(`${apiUrl}/questions/${questionId}`);
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { matches: unknown[] };
  expect(body.matches).toHaveLength(0);
});

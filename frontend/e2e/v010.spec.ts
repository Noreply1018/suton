import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test.describe.configure({ mode: "serial" });

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function createProject(page: Page, prefix: string) {
  const name = `${prefix} ${Date.now()}`;
  await page.getByLabel("新建项目").fill(name);
  await page.getByRole("button", { name: "创建项目" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  return name;
}

async function uploadMaterial(page: Page) {
  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));
  await expect(page.getByText("text-layer-material.pdf")).toBeVisible();
  await expect(page.getByTestId("document-status").filter({ hasText: "完成" })).toBeVisible({ timeout: 90_000 });
}

test("project-validation：空项目名被拦截", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("新建项目").fill(" ");
  await page.getByRole("button", { name: "创建项目" }).click();
  await expect(page.getByText("项目名称不能为空")).toBeVisible();
});

test("question-input：无资料时提交题目被拦截", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "无资料项目");

  const question = readFileSync(resolve("tests/fixtures/question.txt"), "utf-8").trim();
  await page.getByTestId("question-text").fill(question);
  await page.getByRole("button", { name: "查找资料依据" }).click();
  await expect(page.getByText("需先上传并处理资料")).toBeVisible();
});

test("document-upload：拒绝非 PDF 文件", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "非 PDF 验证项目");

  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/not-pdf.txt"));
  await expect(page.getByText("v0.1.0 只支持上传 PDF 文件")).toBeVisible();
});

test("minimal-loop/source-results：真实最小闭环返回来源结果", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Suton" })).toBeVisible();
  await createProject(page, "高等数学（上）期末复习");

  await uploadMaterial(page);

  const question = readFileSync(resolve("tests/fixtures/question.txt"), "utf-8").trim();
  await page.getByTestId("question-text").fill(question);
  await page.getByRole("button", { name: "查找资料依据" }).click();

  await expect(page.getByRole("heading", { name: "资料依据" })).toBeVisible();
  await expect(page.getByText("pgvector 相似度").first()).toBeVisible({ timeout: 30_000 });
  const pdfLink = page.getByRole("link", { name: "PDF" }).first();
  await expect(pdfLink).toHaveAttribute("href", /\/documents\/\d+\/file#page=\d+/);
});

test("document-failure：损坏 PDF 展示失败状态", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "损坏 PDF 验证项目");

  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/broken.pdf"));
  await expect(page.getByText("broken.pdf")).toBeVisible();
  await expect(page.getByTestId("document-status").filter({ hasText: "失败" })).toBeVisible({ timeout: 30_000 });
});

test("empty-results：明显无关题目展示空结果", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "空结果验证项目");
  await uploadMaterial(page);

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

test("missing-source-page：缺少来源字段的候选不在页面展示", async ({ page }) => {
  const questionId = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_missing_source.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();

  await page.goto(`/?questionId=${questionId}`);
  await expect(page.getByRole("heading", { name: "资料依据" })).toBeVisible();
  await expect(page.getByText("没有匹配资料。系统不会生成无来源答案。")).toBeVisible();
  await expect(page.getByText("seed missing source")).toHaveCount(0);
});

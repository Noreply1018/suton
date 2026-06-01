import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

test.describe.configure({ mode: "serial" });

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type Project = {
  id: number;
  name: string;
};

type ProjectSeed = {
  id: number;
  name: string;
  document_id: number;
  document_filename: string;
  question_id: number;
};

type QuestionDetail = {
  id: number;
  matches: unknown[];
};

type DocumentDetailsSeed = {
  project_id: number;
  project_name: string;
  completed_id: number;
  failed_id: number;
  unsupported_id: number;
};

type SourceReaderSeed = {
  project_id: number;
  project_name: string;
  question_id: number;
  document_id: number;
  match_id: number;
  second_match_id: number;
};

async function createProject(page: Page, prefix: string) {
  const name = `${prefix} ${Date.now()}`;
  await page.getByRole("button", { name: "新建项目" }).click();
  await page.getByLabel("项目名称").fill(name);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  return name;
}

async function openProjectAction(page: Page, action: "重命名" | "删除项目") {
  await page.getByRole("button", { name: "项目操作" }).click();
  await page.getByTestId("trace-workspace").getByRole("button", { name: action, exact: true }).click();
}

function seedProjectWithCounts() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_project_counts.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as ProjectSeed;
}

function seedDocumentDetails() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_document_details.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as DocumentDetailsSeed;
}

function seedSourceReader() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_source_reader.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as SourceReaderSeed;
}

function seedSourceFileMissing() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_source_file_missing.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as SourceReaderSeed;
}

function seedStaleSource() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_stale_source.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as SourceReaderSeed;
}

async function expectDetailItem(page: Page, testId: string, label: string, value: string) {
  const item = page.getByTestId(`document-detail-${testId}`);
  await expect(item).toContainText(label);
  await expect(item).toContainText(value);
}

async function uploadMaterial(page: Page) {
  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));
  await expect(page.getByTestId("material-library").getByText("text-layer-material.pdf")).toBeVisible();
  await expect(page.getByTestId("document-status").filter({ hasText: "完成" })).toBeVisible({ timeout: 90_000 });
}

test("project-validation：空项目名被拦截", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "新建项目" }).click();
  await page.getByLabel("项目名称").fill(" ");
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByText("项目名称不能为空")).toBeVisible();
});

test("v020-first-empty-project：首次空工作台不使用默认项目名", async ({ page }) => {
  const projectsResponse = page.waitForResponse(
    (response) => response.url().endsWith("/projects") && response.request().method() === "GET"
  );
  await page.goto("/");
  expect((await projectsResponse).status()).toBe(200);
  await expect(page.getByTestId("sidebar-nav")).toBeVisible();
  await expect(page.getByTestId("trace-workspace")).toBeVisible();
  await expect(page.getByTestId("evidence-preview")).toBeVisible();
  await expect(page.getByRole("heading", { name: "尚未创建项目" })).toBeVisible();
  await expect(page.getByTestId("v020-first-empty-project")).toContainText("添加第一份课程资料");
  await expect(page.getByRole("button", { name: "新建项目" })).toBeVisible();
  await page.getByRole("button", { name: "添加第一份课程资料" }).click();
  await expect(page.getByRole("dialog", { name: "新建项目" })).toBeVisible();
  await page.getByRole("button", { name: "取消" }).click();
  await expect(page.getByText("高等数学（上）期末复习")).toHaveCount(0);
});

test("v020-project-create：新建项目不使用演示默认名", async ({ page }) => {
  await page.goto("/");
  const name = `线性代数期末 ${Date.now()}`;
  await page.getByRole("button", { name: "新建项目" }).click();
  await expect(page.getByRole("dialog", { name: "新建项目" })).toBeVisible();
  await page.getByLabel("项目名称").fill(name);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(name) })).toBeVisible();
  await expect(page.getByText("高等数学（上）期末复习")).toHaveCount(0);
});

test("v020-project-unique-name：重名项目被前端展示为固定错误", async ({ page }) => {
  await page.goto("/");
  const name = "高性能计算期末";
  await page.getByRole("button", { name: "新建项目" }).click();
  await page.getByLabel("项目名称").fill(name);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();

  await page.getByRole("button", { name: "新建项目" }).click();
  await page.getByLabel("项目名称").fill(name);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByText("项目名称已存在")).toBeVisible();

  const response = await page.request.get(`${apiUrl}/projects`);
  expect(response.status()).toBe(200);
  const projects = (await response.json()) as Project[];
  expect(projects.filter((project) => project.name === name)).toHaveLength(1);
});

test("v020-project-name-limits：空名超长名被拦截且 80 字符合法", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "新建项目" }).click();
  await page.getByLabel("项目名称").fill(" ");
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByText("项目名称不能为空")).toBeVisible();

  await page.getByLabel("项目名称").fill("课".repeat(81));
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByText("项目名称不能超过 80 个字符")).toBeVisible();

  const validName = "课".repeat(80);
  await page.getByLabel("项目名称").fill(validName);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByRole("heading", { name: validName })).toBeVisible();

  await createProject(page, "重命名边界项目");
  await openProjectAction(page, "重命名");
  await page.getByLabel("项目名称").fill(" ");
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByText("项目名称不能为空")).toBeVisible();

  await page.getByLabel("项目名称").fill("课".repeat(81));
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByText("项目名称不能超过 80 个字符")).toBeVisible();

  await page.getByLabel("项目名称").fill(validName);
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByText("项目名称已存在")).toBeVisible();
});

test("v020-project-rename-delete：重命名同步并通过确认删除当前项目", async ({ page }) => {
  const seed = seedProjectWithCounts();
  await page.goto("/");
  const originalName = seed.name;
  const renamedName = `${originalName} 已重命名`;
  await expect(page.getByRole("heading", { name: originalName })).toBeVisible();

  await openProjectAction(page, "重命名");
  await expect(page.getByRole("dialog", { name: "重命名项目" })).toBeVisible();
  await expect(page.getByLabel("项目名称")).toHaveValue(originalName);
  await page.getByLabel("项目名称").fill(renamedName);
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByRole("heading", { name: renamedName })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(renamedName) })).toBeVisible();

  await openProjectAction(page, "删除项目");
  const dialog = page.getByRole("dialog", { name: "删除项目" });
  await expect(dialog).toContainText("删除项目及其全部资料");
  await expect(dialog).toContainText("将删除项目、全部资料、题目和来源结果。");
  await expect(dialog).toContainText(`项目：${renamedName} · 资料 1 份 · 题目 1 道`);
  await page.getByRole("button", { name: "确认删除" }).click();
  await expect(page.getByRole("heading", { name: "尚未创建项目" })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(renamedName) })).toHaveCount(0);

  const response = await page.request.get(`${apiUrl}/projects`);
  expect(response.status()).toBe(200);
  const projects = (await response.json()) as Project[];
  expect(projects.some((project) => project.name === renamedName)).toBe(false);
});

test("v020-project-delete-selection：删除当前项目后选择排序第一项或空工作区", async ({ page }) => {
  await page.goto("/");
  const first = await createProject(page, "删除选择 A");
  const second = await createProject(page, "删除选择 B");
  const third = await createProject(page, "删除选择 C");

  await page.getByRole("button", { name: new RegExp(first) }).click();
  await expect(page.getByRole("heading", { name: first })).toBeVisible();
  await openProjectAction(page, "删除项目");
  await page.getByRole("button", { name: "确认删除" }).click();
  await expect(page.getByRole("heading", { name: third })).toBeVisible();

  for (const name of [third, second]) {
    await openProjectAction(page, "删除项目");
    await page.getByRole("button", { name: "确认删除" }).click();
    await expect(page.getByRole("button", { name: new RegExp(name) })).toHaveCount(0);
  }
  await expect(page.getByRole("heading", { name: "尚未创建项目" })).toBeVisible();
  await expect(page.getByTestId("v020-first-empty-project")).toContainText("添加第一份课程资料");
});

test("v020-document-delete：资料删除确认后移除资料且保留题目记录", async ({ page }) => {
  const seed = seedProjectWithCounts();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: seed.name })).toBeVisible();
  await expect(page.getByTestId("material-library").getByText(seed.document_filename)).toBeVisible();
  await expect(page.getByTestId("material-library")).toContainText("1 页 · 良好 · 1 个片段 · 可检索");

  await page.getByTestId("material-library").getByRole("button", { name: "删除资料" }).click();
  const dialog = page.getByRole("dialog", { name: "删除资料" });
  await expect(dialog).toContainText(seed.document_filename);
  await expect(dialog).toContainText("将删除该 PDF、页面文本、索引和相关来源结果。题目记录会保留。");
  await dialog.getByRole("button", { name: "删除资料" }).click();

  await expect(page.getByTestId("material-library").getByText(seed.document_filename)).toHaveCount(0);
  await expect(page.getByTestId("material-library")).toContainText("项目内还没有资料。");

  const questionsResponse = await page.request.get(`${apiUrl}/projects/${seed.id}/questions`);
  expect(questionsResponse.status()).toBe(200);
  const questions = (await questionsResponse.json()) as unknown[];
  expect(questions).toHaveLength(1);

  const questionResponse = await page.request.get(`${apiUrl}/questions/${seed.question_id}`);
  expect(questionResponse.status()).toBe(200);
  const question = (await questionResponse.json()) as QuestionDetail;
  expect(question.matches).toHaveLength(0);
});

test("v020-document-health：资料列表展示健康信息和不可检索原因", async ({ page }) => {
  const seed = seedDocumentDetails();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

  const library = page.getByTestId("material-library");
  await expect(library).toContainText("detail-completed.pdf");
  await expect(library).toContainText("2 页 · 良好 · 1 个片段 · 可检索 · 最近处理 2026-01-02 03:04:05");
  await expect(library).toContainText("detail-failed.pdf");
  await expect(library).toContainText("0 页 · 不可检索 · 0 个片段 · 不可检索 · 最近处理 2026-01-02 03:04:05");
  await expect(library).toContainText("PDF 文件损坏，无法读取");
  await expect(library).toContainText("detail-scanned.pdf");
  await expect(library).toContainText("1 页 · 不可检索 · 0 个片段 · 不可检索 · 最近处理 2026-01-02 03:04:05");
  await expect(library).toContainText("PDF 无可提取文字层，v0.2.0 不进入 OCR");
});

test("v020-document-detail-fields：资料详情展示完成失败和 unsupported 固定字段", async ({ page }) => {
  const seed = seedDocumentDetails();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

  await page.getByRole("button", { name: /detail-completed\.pdf/ }).click();
  let detail = page.getByTestId("document-detail");
  await expect(detail).toBeVisible();
  await expectDetailItem(page, "filename", "文件名", "detail-completed.pdf");
  await expectDetailItem(page, "content-type", "内容类型", "application/pdf");
  await expectDetailItem(page, "page-count", "页数", "2");
  await expectDetailItem(page, "extractable-page-count", "可提取文字页数", "2");
  await expectDetailItem(page, "text-quality", "文字层质量", "良好");
  await expectDetailItem(page, "chunk-count", "chunk 数", "1");
  await expectDetailItem(page, "searchable", "可检索状态", "可检索");
  await expectDetailItem(page, "status", "处理状态", "完成");
  await expectDetailItem(page, "processing-stage", "处理阶段", "完成");
  await expectDetailItem(page, "failed-stage", "失败阶段", "无");
  await expectDetailItem(page, "failure-code", "失败码", "无");
  await expectDetailItem(page, "failure-reason", "失败原因", "无");
  await expectDetailItem(page, "created-at", "创建时间", "2026-01-01 01:02:03");
  await expectDetailItem(page, "processed-at", "最近处理时间", "2026-01-02 03:04:05");

  await page.getByRole("button", { name: /detail-failed\.pdf/ }).click();
  detail = page.getByTestId("document-detail");
  await expect(detail).toBeVisible();
  await expectDetailItem(page, "filename", "文件名", "detail-failed.pdf");
  await expectDetailItem(page, "page-count", "页数", "0");
  await expectDetailItem(page, "status", "处理状态", "失败");
  await expectDetailItem(page, "failed-stage", "失败阶段", "提取文本");
  await expectDetailItem(page, "failure-code", "失败码", "invalid_pdf");
  await expectDetailItem(page, "failure-reason", "失败原因", "PDF 文件损坏，无法读取");
  await expectDetailItem(page, "processed-at", "最近处理时间", "2026-01-02 03:04:05");

  await page.getByRole("button", { name: /detail-scanned\.pdf/ }).click();
  detail = page.getByTestId("document-detail");
  await expect(detail).toBeVisible();
  await expectDetailItem(page, "filename", "文件名", "detail-scanned.pdf");
  await expectDetailItem(page, "page-count", "页数", "1");
  await expectDetailItem(page, "extractable-page-count", "可提取文字页数", "0");
  await expectDetailItem(page, "text-quality", "文字层质量", "不可检索");
  await expectDetailItem(page, "searchable", "可检索状态", "不可检索");
  await expectDetailItem(page, "status", "处理状态", "不支持");
  await expectDetailItem(page, "failure-code", "失败码", "no_text_layer");
  await expectDetailItem(page, "failure-reason", "失败原因", "PDF 无可提取文字层，v0.2.0 不进入 OCR");
});

test("v020-document-scope-disabled：不可检索资料范围选择器禁用态", async ({ page }) => {
  const seed = seedDocumentDetails();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

  const scope = page.getByTestId("document-scope-selector");
  await expect(scope.getByRole("button", { name: "全部可检索资料" })).toHaveAttribute("aria-pressed", "true");
  await scope.getByRole("button", { name: "指定资料" }).click();
  await expect(scope.getByRole("button", { name: "指定资料" })).toHaveAttribute("aria-pressed", "true");

  const submitButton = page.getByRole("button", { name: "查找资料依据" });
  await expect(submitButton).toBeDisabled();

  const completed = page.getByTestId(`document-scope-option-${seed.completed_id}`);
  await expect(completed).toContainText("detail-completed.pdf");
  await expect(completed).toContainText("良好 · 1 个片段 · 可检索");
  await expect(completed.locator("input")).toBeEnabled();

  const failed = page.getByTestId(`document-scope-option-${seed.failed_id}`);
  await expect(failed).toContainText("detail-failed.pdf");
  await expect(failed).toContainText("不可检索 · 0 个片段 · 不可检索 · 资料尚未完成处理");
  await expect(failed.locator("input")).toBeDisabled();

  const unsupported = page.getByTestId(`document-scope-option-${seed.unsupported_id}`);
  await expect(unsupported).toContainText("detail-scanned.pdf");
  await expect(unsupported).toContainText("不可检索 · 0 个片段 · 不可检索 · 资料尚未完成处理");
  await expect(unsupported.locator("input")).toBeDisabled();

  await completed.click();
  await expect(completed.locator("input")).toBeChecked();
  await expect(submitButton).toBeEnabled();
});

test("v020-source-reader-open：点击来源打开 PDF 页与来源详情", async ({ page }) => {
  const seed = seedSourceReader();
  await page.goto(`/?questionId=${seed.question_id}`);
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
  await expect(page.getByTestId("source-card").first()).toContainText("source-reader.pdf 第 1 页");

  await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();

  const reader = page.getByTestId("source-reader");
  await expect(reader).toBeVisible();
  await expect(page.getByTestId("source-reader-filename")).toContainText("source-reader.pdf");
  await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
  await expect(reader).toContainText("命中页");
  await expect(page.getByTestId("source-reader-hit-reason")).toContainText("seed source reader fixture");
  await expect(page.getByTestId("source-reader-source-text")).toContainText("source reader hit");
  await expect(page.getByTestId("source-reader-context")).toContainText("source reader before source reader hit source reader after");
  await expect(page.getByTestId("source-reader-score")).toContainText("pgvector 相似度 0.9100");
  await expect(page.getByTestId("source-reader-pdf")).toHaveAttribute(
    "src",
    new RegExp(`/documents/${seed.document_id}/file#page=1$`)
  );
  await expect(reader.getByRole("button", { name: "上一页" })).toBeDisabled();
  await expect(reader.getByRole("button", { name: "下一页" })).toBeEnabled();
  await expect(reader.getByRole("button", { name: "回到命中页" })).toBeDisabled();
});

test("v020-source-reader-switch：切换来源原地替换 PDF 页和段落详情", async ({ page }) => {
  const seed = seedSourceReader();
  await page.goto(`/?questionId=${seed.question_id}`);
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
  await expect(page.getByTestId("source-card")).toHaveCount(2);

  await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
  await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("source-reader-source-text")).toContainText("source reader hit");
  await expect(page.getByTestId("source-reader-pdf")).toHaveAttribute(
    "src",
    new RegExp(`/documents/${seed.document_id}/file#page=1$`)
  );

  await page.getByTestId("source-card").nth(1).getByRole("button", { name: /source-reader\.pdf/ }).click();
  const reader = page.getByTestId("source-reader");
  await expect(page.getByTestId("source-reader")).toHaveCount(1);
  await expect(page.getByTestId("source-card").nth(1)).toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("source-card").first()).not.toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("source-reader-meta")).toContainText("第 2 / 2 页 · 排序 2 · 可参考");
  await expect(page.getByTestId("source-reader-hit-reason")).toContainText("seed source switch fixture");
  await expect(page.getByTestId("source-reader-source-text")).toContainText("second source hit");
  await expect(page.getByTestId("source-reader-context")).toContainText("switch reader before second source hit switch reader after");
  await expect(page.getByTestId("source-reader-score")).toContainText("pgvector 相似度 0.7300");
  await expect(page.getByTestId("source-reader-pdf")).toHaveAttribute(
    "src",
    new RegExp(`/documents/${seed.document_id}/file#page=2$`)
  );
  await expect(reader.getByRole("button", { name: "下一页" })).toBeDisabled();
  await expect(reader.getByRole("button", { name: "回到命中页" })).toBeDisabled();
});

test("v020-source-reader-file-missing：PDF 文件缺失展示固定错误状态", async ({ page }) => {
  const seed = seedSourceFileMissing();
  await page.goto(`/?questionId=${seed.question_id}`);
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
  await expect(page.getByTestId("source-card").first()).toContainText("source-reader-missing.pdf 第 1 页");

  await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader-missing\.pdf/ }).click();

  const errorState = page.getByTestId("source-reader-error");
  await expect(errorState).toBeVisible();
  await expect(errorState).toContainText("资料文件不存在");
  await expect(errorState).toContainText("无法打开原 PDF 文件。");
  await expect(page.getByTestId("source-reader")).toHaveCount(0);
  await expect(page.getByTestId("source-reader-pdf")).toHaveCount(0);

  const fileResponse = await page.request.get(`${apiUrl}/documents/${seed.document_id}/file`);
  expect(fileResponse.status()).toBe(404);
  expect(await fileResponse.json()).toEqual({ detail: "资料文件不存在" });
});

test("v020-source-reader-stale-source：来源详情失效展示固定错误状态", async ({ page }) => {
  const seed = seedStaleSource();
  await page.goto(`/?questionId=${seed.question_id}`);
  await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
  await expect(page.getByTestId("source-card").first()).toContainText("stale-source.pdf 第 1 页");
  await expect(page.getByTestId("source-card").first()).toContainText("stale source hit");

  await page.getByTestId("source-card").first().getByRole("button", { name: /stale-source\.pdf/ }).click();

  const errorState = page.getByTestId("source-reader-error");
  await expect(errorState).toBeVisible();
  await expect(errorState).toContainText("来源已失效");
  await expect(errorState).toContainText("该来源已被删除或重新处理。");
  await expect(errorState).not.toContainText("stale source hit");
  await expect(page.getByTestId("source-reader")).toHaveCount(0);
  await expect(page.getByTestId("source-reader-pdf")).toHaveCount(0);

  const staleResponse = await page.request.get(`${apiUrl}/questions/${seed.question_id}/matches/${seed.match_id}`);
  expect(staleResponse.status()).toBe(404);
  expect(await staleResponse.json()).toEqual({ detail: "来源已失效" });

  const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
  expect(deleteResponse.status()).toBe(200);
});

test("question-input：无资料时提交题目被拦截", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "无资料项目");

  const question = readFileSync(resolve("tests/fixtures/question.txt"), "utf-8").trim();
  await page.getByTestId("question-text").fill(question);
  await page.getByRole("button", { name: "查找资料依据" }).click();
  await expect(page.getByText("需先上传并处理资料")).toBeVisible();
});

test("project-switch：切换项目后资料边界刷新", async ({ page }) => {
  await page.goto("/");
  const first = await createProject(page, "项目甲");
  await uploadMaterial(page);
  const second = await createProject(page, "项目乙");

  await page.getByRole("button", { name: new RegExp(first) }).click();
  await expect(page.getByRole("heading", { name: first })).toBeVisible();
  await expect(page.getByTestId("material-library").getByText("text-layer-material.pdf")).toBeVisible();

  await page.getByRole("button", { name: new RegExp(second) }).click();
  await expect(page.getByRole("heading", { name: second })).toBeVisible();
  await expect(page.getByTestId("material-library").getByText("项目内还没有资料。")).toBeVisible();
  await expect(page.getByTestId("material-library").getByText("text-layer-material.pdf")).toHaveCount(0);
});

test("document-upload：拒绝非 PDF 文件", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "非 PDF 验证项目");

  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/not-pdf.txt"));
  await expect(page.getByText("v0.2.0 只支持上传 PDF 文件")).toBeVisible();
});

test("minimal-loop/source-results：真实最小闭环返回来源结果", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Suton" })).toBeVisible();
  await expect(page.getByTestId("sidebar-nav")).toBeVisible();
  await expect(page.getByTestId("trace-workspace")).toBeVisible();
  await expect(page.getByTestId("evidence-preview")).toBeVisible();
  await expect(page.getByTestId("material-library")).toBeVisible();
  await expect(page.getByText("溯源请求").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "资料依据" })).toBeVisible();
  await createProject(page, "高等数学（上）期末复习");

  await uploadMaterial(page);

  const question = readFileSync(resolve("tests/fixtures/question.txt"), "utf-8").trim();
  await page.getByTestId("question-text").fill(question);
  await page.getByRole("button", { name: "查找资料依据" }).click();

  await expect(page.getByRole("heading", { name: "资料依据" })).toBeVisible();
  await expect(page.getByText("pgvector 相似度").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("source-card").first()).toBeVisible();
  const pdfLink = page.getByRole("link", { name: "PDF" }).first();
  await expect(pdfLink).toHaveAttribute("href", /\/documents\/\d+\/file#page=\d+/);
});

test("document-failure：损坏 PDF 展示失败状态", async ({ page }) => {
  await page.goto("/");
  await createProject(page, "损坏 PDF 验证项目");

  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/broken.pdf"));
  await expect(page.getByTestId("material-library").getByText("broken.pdf")).toBeVisible();
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

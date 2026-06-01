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

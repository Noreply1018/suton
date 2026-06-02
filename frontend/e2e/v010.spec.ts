import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
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
  matches: { confidence_label: string }[];
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

type ConfidenceLevelsSeed = {
  project_id: number;
  project_name: string;
  question_id: number;
  document_id: number;
  match_ids: number[];
};

type ProcessingFailureSeed = {
  project_id: number;
  project_name: string;
  reprocess_document_id: number;
  delete_document_id: number;
};

type ProcessingPollingSeed = {
  project_id: number;
  project_name: string;
  document_ids: number[];
};

type QuestionHistoryLongTextSeed = {
  project_id: number;
  project_name: string;
  question_ids: number[];
};

type QuestionHistoryResearchSeed = {
  project_id: number;
  project_name: string;
  question_id: number;
  question_text: string;
  document_id: number;
  old_match_id: number;
};

type NoSourceActionsSeed = {
  project_id: number;
  project_name: string;
  question_id: number;
  question_text: string;
  searchable_document_id: number;
  unavailable_document_id: number;
};

type QuestionScopeErrorsSeed = {
  project_id: number;
  project_name: string;
  other_project_id: number;
  searchable_document_id: number;
  processing_document_id: number;
  unsearchable_document_id: number;
  other_document_id: number;
};

type LongListsSeed = {
  project_id: number;
  project_name: string;
  question_id: number;
  project_ids: number[];
  document_ids: number[];
  question_ids: number[];
};

type UploadedDocument = {
  id: number;
  filename: string;
  status: string;
  processing_stage: string;
  failed_stage: string | null;
  failure_code: string | null;
  failure_reason: string | null;
  chunk_count: number;
  searchable: boolean;
};

type VisualEvidenceRecord = {
  state: string;
  viewport: string;
  path: string;
  url: string;
  browser: string;
  data_command: string;
  captured_at: string;
};

const visualMatrixViewports = [
  { width: 1440, height: 900 },
  { width: 1280, height: 832 },
  { width: 1200, height: 800 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 }
];

const visualMatrixStates = [
  "first-empty-project",
  "project-created",
  "document-list",
  "document-health",
  "paper-ingest-uploading",
  "processing-rail-running",
  "processing-failure-actions",
  "question-search",
  "source-confidence-levels",
  "no-reliable-source",
  "focus-mode",
  "source-detail",
  "source-page-nav",
  "pdf-reader",
  "long-lists",
  "mobile-workspace"
] as const;

async function createProject(page: Page, prefix: string) {
  const name = `${prefix} ${Date.now()}`;
  await page.getByRole("button", { name: "新建项目" }).click();
  await page.getByLabel("项目名称").fill(name);
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  return name;
}

async function projectIdByName(page: Page, name: string) {
  const response = await page.request.get(`${apiUrl}/projects`);
  expect(response.ok()).toBeTruthy();
  const projects = (await response.json()) as Project[];
  const project = projects.find((item) => item.name === name);
  if (!project) throw new Error(`project not found: ${name}`);
  return project.id;
}

async function openQuestionProject(page: Page, questionId: number, projectName: string) {
  await page.goto(`/?questionId=${questionId}`);
  await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
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

function seedConfidenceLevels() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_confidence_levels.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as ConfidenceLevelsSeed;
}

function seedProcessingFailure() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_processing_failure.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as ProcessingFailureSeed;
}

function seedProcessingPolling() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_processing_polling.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as ProcessingPollingSeed;
}

function seedQuestionHistoryLongText() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_question_history_long_text.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as QuestionHistoryLongTextSeed;
}

function seedQuestionHistoryResearch() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_question_history_research.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as QuestionHistoryResearchSeed;
}

function seedNoSourceActions() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_no_source_actions.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as NoSourceActionsSeed;
}

function seedQuestionScopeErrors() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_question_scope_errors.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as QuestionScopeErrorsSeed;
}

function seedLongLists() {
  const output = execFileSync("uv", ["run", "--project", "backend", "python", "scripts/seed_long_lists.py"], {
    cwd: resolve("."),
    env: { ...process.env, PYTHONPATH: "backend" },
    encoding: "utf-8"
  }).trim();
  return JSON.parse(output) as LongListsSeed;
}

async function expectDetailItem(page: Page, testId: string, label: string, value: string) {
  const item = page.getByTestId(`document-detail-${testId}`);
  await expect(item).toContainText(label);
  await expect(item).toContainText(value);
}

async function longListMetrics(page: Page) {
  return page.evaluate(() => {
    function listMetric(testId: string) {
      const element = document.querySelector(`[data-testid="${testId}"]`);
      if (!element) throw new Error(`${testId} missing`);
      return {
        clientHeight: element.clientHeight,
        scrollHeight: element.scrollHeight,
        scrolls: element.scrollHeight > element.clientHeight + 1
      };
    }

    return {
      projectList: listMetric("project-list"),
      documentList: listMetric("document-list"),
      questionHistory: listMetric("question-history-list"),
      sourceResults: listMetric("source-results-list"),
      horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      pageHeight: document.documentElement.scrollHeight
    };
  });
}

async function workspaceBreakpointMetrics(page: Page) {
  return page.evaluate(() => {
    const grid = document.querySelector('[data-testid="workspace-grid"]');
    const inspector = document.querySelector('[data-testid="evidence-preview"]');
    if (!grid || !inspector) throw new Error("workspace layout missing");
    const columns = window
      .getComputedStyle(grid)
      .gridTemplateColumns.split(" ")
      .map((value) => Number.parseFloat(value));
    return {
      columns,
      inspectorDisplay: window.getComputedStyle(inspector).display,
      inspectorPosition: window.getComputedStyle(inspector).position,
      inspectorWidth: Math.round(inspector.getBoundingClientRect().width),
      horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      verticalOverflow: document.documentElement.scrollHeight - document.documentElement.clientHeight,
      gridHeight: Math.round(grid.getBoundingClientRect().height),
      viewportHeight: window.innerHeight
    };
  });
}

type VisualHardError = {
  viewport: string;
  type: string;
  label: string;
  detail: string;
};

async function visualHardErrors(page: Page, viewport: string, options: { requireCoverageTargets?: boolean } = {}) {
  return page.evaluate(({ viewportName, requireCoverageTargets }) => {
    const isVisible = (element: Element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
    };
    const labelFor = (element: Element) =>
      element.getAttribute("data-testid") ||
      element.getAttribute("aria-label") ||
      element.textContent?.trim().replace(/\s+/g, " ").slice(0, 80) ||
      element.tagName.toLowerCase();
    const rectArea = (rect: DOMRect) => Math.max(0, rect.width) * Math.max(0, rect.height);
    const intersectionArea = (a: DOMRect, b: DOMRect) => {
      const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
      const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
      return width * height;
    };
    const errors: VisualHardError[] = [];
    const horizontalOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    const verticalOverflow = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    if (horizontalOverflow > 1) {
      errors.push({
        viewport: viewportName,
        type: "horizontal-scroll",
        label: "documentElement",
        detail: `${document.documentElement.scrollWidth} - ${document.documentElement.clientWidth} = ${horizontalOverflow}`
      });
    }
    if (verticalOverflow > 1) {
      errors.push({
        viewport: viewportName,
        type: "vertical-scroll",
        label: "documentElement",
        detail: `${document.documentElement.scrollHeight} - ${document.documentElement.clientHeight} = ${verticalOverflow}`
      });
    }

    for (const element of Array.from(document.querySelectorAll("button, [role='button']"))) {
      if (!isVisible(element)) continue;
      const overflow = element.scrollWidth - element.clientWidth;
      if (overflow > 1) {
        errors.push({
          viewport: viewportName,
          type: "button-overflow",
          label: labelFor(element),
          detail: `${element.scrollWidth} - ${element.clientWidth} = ${overflow}`
        });
      }
    }

    const overflowTargets = Array.from(document.querySelectorAll('[data-v020-check-overflow="true"]')).filter(isVisible);
    if (requireCoverageTargets && overflowTargets.length === 0) {
      errors.push({
        viewport: viewportName,
        type: "missing-overflow-targets",
        label: "data-v020-check-overflow",
        detail: "no visible overflow targets"
      });
    }
    for (const element of overflowTargets) {
      if (!isVisible(element)) continue;
      const horizontal = element.scrollWidth - element.clientWidth;
      const vertical = element.scrollHeight - element.clientHeight;
      if (horizontal > 1 || vertical > 1) {
        errors.push({
          viewport: viewportName,
          type: "text-overflow",
          label: labelFor(element),
          detail: `horizontal=${horizontal}; vertical=${vertical}`
        });
      }
    }

    const regions = Array.from(document.querySelectorAll("[data-v020-critical-region]")).filter(isVisible);
    if (requireCoverageTargets && regions.length < 2) {
      errors.push({
        viewport: viewportName,
        type: "missing-critical-regions",
        label: "data-v020-critical-region",
        detail: `visible regions=${regions.length}`
      });
    }
    for (let index = 0; index < regions.length; index += 1) {
      for (let nextIndex = index + 1; nextIndex < regions.length; nextIndex += 1) {
        const first = regions[index];
        const second = regions[nextIndex];
        const firstRect = first.getBoundingClientRect();
        const secondRect = second.getBoundingClientRect();
        const overlap = intersectionArea(firstRect, secondRect);
        const smallerArea = Math.min(rectArea(firstRect), rectArea(secondRect));
        if (smallerArea > 0 && overlap > smallerArea * 0.1) {
          errors.push({
            viewport: viewportName,
            type: "critical-region-overlap",
            label: `${labelFor(first)} / ${labelFor(second)}`,
            detail: `overlap=${Math.round(overlap)}; smaller=${Math.round(smallerArea)}`
          });
        }
      }
    }

    const main = document.querySelector("main");
    if (!main || !isVisible(main)) {
      errors.push({ viewport: viewportName, type: "blank-main", label: "main", detail: "main missing or invisible" });
    } else {
      const rect = main.getBoundingClientRect();
      const visibleWidth = Math.max(0, Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0));
      const visibleHeight = Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
      const visibleArea = visibleWidth * visibleHeight;
      const viewportArea = window.innerWidth * window.innerHeight;
      if (visibleArea < viewportArea * 0.35) {
        errors.push({
          viewport: viewportName,
          type: "blank-main",
          label: "main",
          detail: `visible=${Math.round(visibleArea)}; viewport=${viewportArea}`
        });
      }
    }
    return errors;
  }, { viewportName: viewport, requireCoverageTargets: options.requireCoverageTargets ?? false });
}

async function uploadMaterial(page: Page) {
  await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));
  await expect(page.getByTestId("material-library").getByText("text-layer-material.pdf")).toBeVisible();
  await expect(page.getByTestId("document-status").filter({ hasText: "完成" })).toBeVisible({ timeout: 90_000 });
}

async function installIndeterminateUploadProbe(page: Page) {
  await page.addInitScript(() => {
    const originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function patchedSend(body?: Document | XMLHttpRequestBodyInit | null) {
      const xhr = this;
      if (typeof xhr.responseURL === "string" && xhr.responseURL.includes("/documents")) {
        return originalSend.call(xhr, body);
      }
      if (body instanceof FormData && Array.from(body.keys()).includes("file")) {
        setTimeout(() => {
          xhr.upload.dispatchEvent(new ProgressEvent("progress", { lengthComputable: false, loaded: 4096, total: 0 }));
        }, 0);
        setTimeout(() => originalSend.call(xhr, body), 800);
        return;
      }
      return originalSend.call(xhr, body);
    };
  });
}

async function installUploadSendDelayProbe(page: Page, delayMs = 800) {
  await page.addInitScript((delay) => {
    const originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function patchedSend(body?: Document | XMLHttpRequestBodyInit | null) {
      if (body instanceof FormData && Array.from(body.keys()).includes("file")) {
        setTimeout(() => originalSend.call(this, body), delay);
        return;
      }
      return originalSend.call(this, body);
    };
  }, delayMs);
}

async function submitQuestionWithScopeOverride(page: Page, projectId: number, documentIds: number[]) {
  await page.route(
    `${apiUrl}/projects/${projectId}/questions`,
    async (route) => {
      const request = route.request();
      if (request.method() !== "POST") {
        await route.continue();
        return;
      }
      const body = JSON.parse(request.postData() ?? "{}") as { text?: string; document_ids?: number[] | null };
      await route.continue({
        postData: JSON.stringify({ ...body, document_ids: documentIds }),
        headers: { ...request.headers(), "content-type": "application/json" }
      });
    },
    { times: 1 }
  );
  const responsePromise = page.waitForResponse(
    (response) => response.url() === `${apiUrl}/projects/${projectId}/questions` && response.request().method() === "POST"
  );
  await page.getByRole("button", { name: "查找资料依据" }).click();
  return responsePromise;
}

function utcIsoNow() {
  return new Date().toISOString();
}

function visualEvidencePath(viewport: { width: number; height: number }, state: string) {
  return resolve("tmp/v0.2.0-visual-evidence", `${viewport.width}x${viewport.height}-${state}.png`);
}

async function captureVisualMatrixState({
  page,
  records,
  browserName,
  state,
  dataCommand,
  viewports = visualMatrixViewports,
  prepare
}: {
  page: Page;
  records: VisualEvidenceRecord[];
  browserName: string;
  state: (typeof visualMatrixStates)[number];
  dataCommand: string;
  viewports?: { width: number; height: number }[];
  prepare: (viewport: { width: number; height: number }) => Promise<void>;
}) {
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await prepare(viewport);
    await expect(page.getByTestId("app-shell")).toBeVisible();
    const hardErrors = await visualHardErrors(page, `${viewport.width}x${viewport.height}`);
    expect(hardErrors).toEqual([]);

    const screenshotPath = visualEvidencePath(viewport, state);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    records.push({
      state,
      viewport: `${viewport.width}x${viewport.height}`,
      path: `tmp/v0.2.0-visual-evidence/${viewport.width}x${viewport.height}-${state}.png`,
      url: page.url(),
      browser: browserName,
      data_command: dataCommand,
      captured_at: utcIsoNow()
    });
  }
}

async function captureUploadingState(
  page: Page,
  records: VisualEvidenceRecord[],
  browserName: string,
  projectIds: number[],
  viewports: { width: number; height: number }[]
) {
  await installIndeterminateUploadProbe(page);
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    const projectName = await createProject(page, `截图上传 ${viewport.width}x${viewport.height}`);
    const projectId = await projectIdByName(page, projectName);
    projectIds.push(projectId);
    await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));
    const progressCard = page.getByTestId("upload-progress-card");
    await expect(progressCard).toBeVisible();
    await expect(progressCard).toHaveAttribute("data-progress-mode", "indeterminate");
    const hardErrors = await visualHardErrors(page, `${viewport.width}x${viewport.height}`);
    expect(hardErrors).toEqual([]);

    const screenshotPath = visualEvidencePath(viewport, "paper-ingest-uploading");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    records.push({
      state: "paper-ingest-uploading",
      viewport: `${viewport.width}x${viewport.height}`,
      path: `tmp/v0.2.0-visual-evidence/${viewport.width}x${viewport.height}-paper-ingest-uploading.png`,
      url: page.url(),
      browser: browserName,
      data_command: "UI createProject + tests/fixtures/text-layer-material.pdf upload with indeterminate browser progress",
      captured_at: utcIsoNow()
    });
    await expect(progressCard).toHaveCount(0, { timeout: 10_000 });
  }
}

async function captureQuestionSearchState(
  page: Page,
  records: VisualEvidenceRecord[],
  browserName: string,
  seed: SourceReaderSeed,
  viewports: { width: number; height: number }[]
) {
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await openQuestionProject(page, seed.question_id, seed.project_name);
    await page.route(
      `${apiUrl}/projects/${seed.project_id}/questions`,
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1800));
        await route.continue();
      },
      { times: 1 }
    );
    await page.getByTestId("question-text").fill("截图矩阵检索中状态");
    await page.getByRole("button", { name: "查找资料依据" }).click();
    await expect(page.getByTestId("question-loading")).toContainText("正在检索来源");
    const hardErrors = await visualHardErrors(page, `${viewport.width}x${viewport.height}`);
    expect(hardErrors).toEqual([]);

    const screenshotPath = visualEvidencePath(viewport, "question-search");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    records.push({
      state: "question-search",
      viewport: `${viewport.width}x${viewport.height}`,
      path: `tmp/v0.2.0-visual-evidence/${viewport.width}x${viewport.height}-question-search.png`,
      url: page.url(),
      browser: browserName,
      data_command: "scripts/seed_source_reader.py + delayed real POST /projects/{project_id}/questions",
      captured_at: utcIsoNow()
    });
  }
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

test("visual-first-empty-project：生成首次空工作台桌面和移动截图", async ({ page }) => {
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const desktopScreenshotPath = resolve(evidenceDir, "1440x900-first-empty-project.png");
  const mobileScreenshotPath = resolve(evidenceDir, "390x844-first-empty-project.png");
  mkdirSync(evidenceDir, { recursive: true });

  for (const viewport of [
    { width: 1440, height: 900, screenshotPath: desktopScreenshotPath },
    { width: 390, height: 844, screenshotPath: mobileScreenshotPath }
  ]) {
    const projectsResponse = page.waitForResponse(
      (response) => response.url().endsWith("/projects") && response.request().method() === "GET"
    );
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    expect((await projectsResponse).status()).toBe(200);

    await expect(page.getByTestId("app-shell")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).toBeVisible();
    await expect(page.getByTestId("trace-workspace")).toBeVisible();
    await expect(page.getByTestId("evidence-preview")).toBeVisible();
    await expect(page.getByRole("heading", { name: "尚未创建项目" })).toBeVisible();
    await expect(page.getByTestId("v020-first-empty-project")).toContainText("添加第一份课程资料");
    await expect(page.getByText("高等数学（上）期末复习")).toHaveCount(0);

    await page.screenshot({ path: viewport.screenshotPath, fullPage: true });
    expect(statSync(viewport.screenshotPath).size).toBeGreaterThan(1000);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  }
});

test("visual-legacy-copy-removed：旧演示文案不进入运行源码和真实页面", async ({ page }) => {
  const bannedCopies = ["v0.1.0", "演示项目", "默认项目", "Demo", "placeholder project", "高等数学（上）期末复习"];
  const appSourceFiles = ["frontend/app/layout.tsx", "frontend/app/page.tsx", "frontend/app/globals.css"];

  for (const filePath of appSourceFiles) {
    const content = readFileSync(resolve(filePath), "utf-8");
    for (const copy of bannedCopies) {
      expect(content, `${filePath} should not contain ${copy}`).not.toContain(copy);
    }
  }

  const projectsResponse = page.waitForResponse(
    (response) => response.url().endsWith("/projects") && response.request().method() === "GET"
  );
  await page.goto("/");
  expect((await projectsResponse).status()).toBe(200);
  await expect(page).toHaveTitle("Suton");
  await expect(page.getByTestId("app-shell")).toBeVisible();

  const visibleText = await page.locator("body").innerText();
  for (const copy of bannedCopies) {
    expect(visibleText).not.toContain(copy);
  }
});

test("visual-legacy-frontend-removed：旧前端结构和样式不进入运行路径", async ({ page }) => {
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "1440x900-legacy-frontend-removed.png");
  const bannedCopies = ["v0.1.0", "演示项目", "默认项目", "Demo", "placeholder project", "高等数学（上）期末复习"];
  const bannedLegacyClasses = [
    "suton-mark",
    "paper-grid",
    "trace-canvas",
    "trace-rings",
    "trace-center",
    "evidence-node",
    "node-orbit",
    "node-body",
    "text-balance",
    "line-clamp-2"
  ];
  const appSourceFiles = ["frontend/app/layout.tsx", "frontend/app/page.tsx", "frontend/app/globals.css"];

  for (const filePath of appSourceFiles) {
    const content = readFileSync(resolve(filePath), "utf-8");
    for (const copy of bannedCopies) {
      expect(content, `${filePath} should not contain old visible copy ${copy}`).not.toContain(copy);
    }
    for (const className of bannedLegacyClasses) {
      expect(content, `${filePath} should not contain old frontend class ${className}`).not.toContain(className);
    }
  }

  const projectsResponse = page.waitForResponse(
    (response) => response.url().endsWith("/projects") && response.request().method() === "GET"
  );
  await page.goto("/");
  expect((await projectsResponse).status()).toBe(200);

  await expect(page).toHaveTitle("Suton");
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("sidebar-nav")).toBeVisible();
  await expect(page.getByTestId("trace-workspace")).toBeVisible();
  await expect(page.getByTestId("evidence-preview")).toBeVisible();
  await expect(page.locator(".suton-mark, .paper-grid, .trace-canvas, .trace-rings, .trace-center, .evidence-node, .node-orbit, .node-body")).toHaveCount(0);

  const visibleText = await page.locator("body").innerText();
  for (const copy of bannedCopies) {
    expect(visibleText).not.toContain(copy);
  }

  mkdirSync(evidenceDir, { recursive: true });
  await page.screenshot({ path: screenshotPath, fullPage: true });
  expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
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
  await expect(page.getByTestId("document-detail-actions").getByRole("button", { name: "重新处理" })).toBeVisible();

  await page.getByRole("button", { name: /detail-failed\.pdf/ }).click();
  detail = page.getByTestId("document-detail");
  await expect(detail).toBeVisible();
  await expectDetailItem(page, "filename", "文件名", "detail-failed.pdf");
  await expectDetailItem(page, "page-count", "页数", "0");
  await expectDetailItem(page, "status", "处理状态", "失败");
  await expectDetailItem(page, "failed-stage", "失败阶段", "提取文字");
  await expectDetailItem(page, "failure-code", "失败码", "invalid_pdf");
  await expectDetailItem(page, "failure-reason", "失败原因", "PDF 文件损坏，无法读取");
  await expectDetailItem(page, "processed-at", "最近处理时间", "2026-01-02 03:04:05");
  await expect(page.getByTestId("document-detail-actions").getByRole("button", { name: "重新处理" })).toBeVisible();

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
  await expect(page.getByTestId("document-detail-actions").getByRole("button", { name: "重新处理" })).toBeVisible();
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

test("v020-processing-failure：失败轨道与修复入口", async ({ page }) => {
  const seed = seedProcessingFailure();
  try {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    const reprocessRow = page.getByTestId(`document-row-${seed.reprocess_document_id}`);
    await expect(reprocessRow).toContainText("processing-failed-reprocess.pdf");
    await expect(reprocessRow.getByTestId(`processing-track-${seed.reprocess_document_id}`)).toContainText("提取文字");
    await expect(reprocessRow.getByTestId("processing-stage-node-uploaded")).toContainText("上传完成");
    await expect(reprocessRow.getByTestId("processing-stage-node-extracting_text")).toContainText("失败");
    await expect(reprocessRow.getByTestId(`document-failure-reason-${seed.reprocess_document_id}`)).toContainText("PDF 文件损坏，无法读取");

    await reprocessRow.getByRole("button", { name: "查看失败原因" }).click();
    await expect(page.getByTestId("document-detail")).toBeVisible();
    await expectDetailItem(page, "failed-stage", "失败阶段", "提取文字");
    await expectDetailItem(page, "failure-code", "失败码", "invalid_pdf");
    await expectDetailItem(page, "failure-reason", "失败原因", "PDF 文件损坏，无法读取");
    await expect(page.getByTestId("document-detail-actions")).toContainText("重新处理");
    await expect(page.getByTestId("document-detail-actions")).toContainText("删除资料");

    const reprocessResponse = page.waitForResponse(
      (response) => response.url().endsWith(`/documents/${seed.reprocess_document_id}/reprocess`) && response.request().method() === "POST"
    );
    await reprocessRow.getByRole("button", { name: "重新处理" }).click();
    expect((await reprocessResponse).status()).toBe(200);

    const deleteRow = page.getByTestId(`document-row-${seed.delete_document_id}`);
    await expect(deleteRow).toContainText("processing-failed-delete.pdf");
    await deleteRow.getByRole("button", { name: "删除资料" }).first().click();
    const dialog = page.getByRole("dialog", { name: "删除资料" });
    await expect(dialog).toContainText("processing-failed-delete.pdf");
    await dialog.getByRole("button", { name: "删除资料" }).click();
    await expect(page.getByTestId(`document-row-${seed.delete_document_id}`)).toHaveCount(0);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-processing-refresh：刷新后从后端恢复处理失败状态", async ({ page }) => {
  const seed = seedProcessingFailure();
  try {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    const row = page.getByTestId(`document-row-${seed.reprocess_document_id}`);
    await expect(row).toContainText("processing-failed-reprocess.pdf");
    await expect(row.getByTestId("processing-stage-node-extracting_text")).toContainText("失败");
    await expect(row.getByTestId(`document-failure-reason-${seed.reprocess_document_id}`)).toContainText("PDF 文件损坏，无法读取");

    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    const documentsResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/projects/${seed.project_id}/documents`) && response.request().method() === "GET"
    );
    await page.reload();
    expect((await documentsResponse).status()).toBe(200);

    const restoredRow = page.getByTestId(`document-row-${seed.reprocess_document_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(restoredRow).toContainText("processing-failed-reprocess.pdf");
    await expect(restoredRow.getByTestId("processing-stage-node-uploaded")).toContainText("上传完成");
    await expect(restoredRow.getByTestId("processing-stage-node-extracting_text")).toContainText("失败");
    await expect(restoredRow.getByTestId(`document-failure-reason-${seed.reprocess_document_id}`)).toContainText("PDF 文件损坏，无法读取");
    const failureActions = restoredRow.getByTestId(`document-failure-actions-${seed.reprocess_document_id}`);
    await expect(failureActions.getByRole("button", { name: "重新处理" })).toBeVisible();
    await expect(failureActions.getByRole("button", { name: "删除资料" })).toBeVisible();
    await expect(failureActions.getByRole("button", { name: "查看失败原因" })).toBeVisible();
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-processing-polling-coalesced：处理中资料共用项目资料列表轮询", async ({ page }) => {
  const seed = seedProcessingPolling();
  const documentDetailPattern = new RegExp(`/documents/(${seed.document_ids.join("|")})$`);
  let projectDocumentListRequests = 0;
  let perDocumentDetailRequests = 0;
  try {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    for (const documentId of seed.document_ids) {
      const row = page.getByTestId(`document-row-${documentId}`);
      await expect(row).toContainText("处理中");
      await expect(row.getByTestId("processing-stage-node-embedding")).toContainText("生成 embedding");
    }
    await page.getByTestId(`document-row-${seed.document_ids[0]}`).getByRole("button", { name: /processing-polling/ }).click();
    await expect(page.getByTestId("document-detail")).toBeVisible();
    await expect(page.getByTestId("document-detail-actions")).toHaveCount(0);

    page.on("request", (request) => {
      const url = request.url();
      if (request.method() !== "GET") return;
      if (url.endsWith(`/projects/${seed.project_id}/documents`)) {
        projectDocumentListRequests += 1;
      }
      if (documentDetailPattern.test(new URL(url).pathname)) {
        perDocumentDetailRequests += 1;
      }
    });

    await page.waitForTimeout(3300);
    expect(projectDocumentListRequests).toBeGreaterThanOrEqual(2);
    expect(perDocumentDetailRequests).toBe(0);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-processing-progress-visual：生成处理轨道运行中截图", async ({ page }) => {
  const seed = seedProcessingPolling();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "1440x900-processing-progress-visual.png");
  mkdirSync(evidenceDir, { recursive: true });
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await page.getByRole("button", { name: new RegExp(seed.project_name) }).click();
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    for (const documentId of seed.document_ids) {
      const row = page.getByTestId(`document-row-${documentId}`);
      await expect(row).toContainText("处理中");
      await expect(row.getByTestId("processing-stage-node-embedding")).toContainText("生成 embedding");
    }

    const hardErrors = await visualHardErrors(page, "1440x900");
    expect(hardErrors).toEqual([]);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
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

test("v020-source-reader-page-nav：来源阅读区页码导航", async ({ page }) => {
  const seed = seedSourceReader();
  try {
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
    const reader = page.getByTestId("source-reader");
    await expect(reader).toBeVisible();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
    await expect(page.getByTestId("source-reader-hit-page")).toBeVisible();
    await expect(reader.getByRole("button", { name: "上一页" })).toBeDisabled();
    await expect(reader.getByRole("button", { name: "下一页" })).toBeEnabled();
    await expect(reader.getByRole("button", { name: "回到命中页" })).toBeDisabled();

    await reader.getByRole("button", { name: "下一页" }).click();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 2 / 2 页 · 排序 1 · 强相关");
    await expect(page.getByTestId("source-reader-pdf")).toHaveAttribute(
      "src",
      new RegExp(`/documents/${seed.document_id}/file#page=2$`)
    );
    await expect(page.getByTestId("source-reader-hit-page")).toHaveCount(0);
    await expect(reader.getByRole("button", { name: "上一页" })).toBeEnabled();
    await expect(reader.getByRole("button", { name: "下一页" })).toBeDisabled();
    await expect(reader.getByRole("button", { name: "回到命中页" })).toBeEnabled();

    await reader.getByRole("button", { name: "回到命中页" }).click();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
    await expect(page.getByTestId("source-reader-pdf")).toHaveAttribute(
      "src",
      new RegExp(`/documents/${seed.document_id}/file#page=1$`)
    );
    await expect(page.getByTestId("source-reader-hit-page")).toBeVisible();
    await expect(reader.getByRole("button", { name: "回到命中页" })).toBeDisabled();
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-source-reader-mobile：移动端来源详情全屏返回后保留状态", async ({ page }) => {
  const seed = seedSourceReader();
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    const firstSource = page.getByTestId("source-card").first();
    await expect(firstSource).toContainText("source-reader.pdf 第 1 页");

    await firstSource.getByRole("button", { name: /source-reader\.pdf/ }).click();
    const reader = page.getByTestId("source-reader");
    await expect(reader).toBeVisible();
    await expect(reader.getByRole("button", { name: "返回题目" })).toBeVisible();
    await expect(page.getByTestId("source-reader-source-text")).toContainText("source reader hit");

    const box = await reader.boundingBox();
    expect(box?.x).toBeLessThanOrEqual(1);
    expect(box?.y).toBeLessThanOrEqual(1);
    expect(box?.width).toBeGreaterThanOrEqual(389);
    expect(box?.height).toBeGreaterThanOrEqual(843);

    await reader.getByRole("button", { name: "返回题目" }).click();
    await expect(reader).not.toBeVisible();
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(firstSource).toBeVisible();
    await expect(firstSource).toHaveAttribute("aria-current", "true");
    await expect(firstSource).toContainText("source reader hit");
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-source-page-nav：生成来源页码导航截图", async ({ page }) => {
  const seed = seedSourceReader();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "1440x900-source-page-nav.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
    const reader = page.getByTestId("source-reader");
    await expect(reader).toBeVisible();
    await reader.getByRole("button", { name: "下一页" }).click();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 2 / 2 页 · 排序 1 · 强相关");
    await expect(reader.getByRole("button", { name: "回到命中页" })).toBeEnabled();
    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(hasHorizontalOverflow).toBe(false);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-current-context：生成当前上下文字段截图", async ({ page }) => {
  const seed = seedSourceReader();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "1440x900-current-context.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    const projectContext = page.getByTestId("project-context-bar");
    await expect(projectContext.getByTestId("project-context-name")).toContainText(seed.project_name);
    await expect(projectContext.getByTestId("project-context-meta")).toContainText("可检索");
    await expect(projectContext.getByTestId("project-context-meta")).toContainText("1 份资料");
    await expect(projectContext.getByTestId("project-context-meta")).toContainText("1 道题目");

    const questionToolbar = page.getByTestId("question-context-toolbar");
    await expect(questionToolbar.getByTestId("question-context-text")).toContainText("source reader question");
    await expect(questionToolbar.getByTestId("question-context-status")).toContainText("已找到来源");
    await expect(questionToolbar.getByRole("button", { name: "检索范围" })).toBeVisible();
    await expect(questionToolbar.getByRole("button", { name: "进入专注模式" })).toBeVisible();

    const firstSource = page.getByTestId("source-card").first();
    await firstSource.getByRole("button", { name: /source-reader\.pdf/ }).click();
    await expect(firstSource).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader-filename")).toContainText("source-reader.pdf");
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");

    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(hasHorizontalOverflow).toBe(false);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-focus-mode：桌面专注模式只保留当前题目来源结果和 PDF 阅读", async ({ page }) => {
  const seed = seedSourceReader();
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
    await expect(page.getByTestId("source-reader")).toBeVisible();

    await page.getByRole("button", { name: "进入专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "true");
    await expect(page.getByRole("button", { name: "退出专注模式" })).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).toBeHidden();
    await expect(page.getByTestId("material-library")).toBeHidden();
    await expect(page.getByTestId("project-context-bar")).toBeHidden();
    await expect(page.getByTestId("question-text")).toBeHidden();
    await expect(page.getByTestId("question-history")).toHaveCount(0);
    await expect(page.getByTestId("question-context-toolbar")).toContainText("source reader question");
    await expect(page.getByTestId("source-card").first()).toBeVisible();
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader")).toBeVisible();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");

    await page.getByRole("button", { name: "退出专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "false");
    await expect(page.getByTestId("sidebar-nav")).toBeVisible();
    await expect(page.getByTestId("material-library")).toBeVisible();
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-focus-mode-restore：退出专注模式后恢复范围来源页码和资料滚动", async ({ page }) => {
  const seed = seedLongLists();
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(page.getByTestId("document-list").locator("[data-testid^='document-row-']")).toHaveCount(20);
    await expect(page.getByTestId("source-card")).toHaveCount(20);

    await page.getByTestId("document-scope-selector").getByRole("button", { name: "指定资料" }).click();
    await page.getByTestId(`document-scope-option-${seed.document_ids[0]}`).getByRole("checkbox").check();
    await expect(page.getByTestId("document-scope-selector").getByRole("button", { name: "指定资料" })).toHaveAttribute("aria-pressed", "true");

    const documentScrollTop = await page.getByTestId("document-list").evaluate((element) => {
      element.scrollTop = 180;
      return element.scrollTop;
    });
    expect(documentScrollTop).toBeGreaterThan(0);

    const firstSource = page.getByTestId("source-card").first();
    await firstSource.getByRole("button", { name: /long-list-material-01\.pdf/ }).click();
    await expect(firstSource).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 1 页 · 排序 1 · 强相关");

    await page.getByRole("button", { name: "进入专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "true");
    await expect(page.getByTestId("material-library")).toBeHidden();
    await expect(page.getByTestId("question-context-toolbar")).toContainText("长列表历史题目 01");
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 1 页 · 排序 1 · 强相关");

    await page.getByRole("button", { name: "退出专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "false");
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(page.getByTestId("question-context-toolbar")).toContainText("长列表历史题目 01");
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 1 页 · 排序 1 · 强相关");
    await expect(page.getByTestId("document-scope-selector").getByRole("button", { name: "指定资料" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId(`document-scope-option-${seed.document_ids[0]}`).getByRole("checkbox")).toBeChecked();
    const restoredScrollTop = await page.getByTestId("document-list").evaluate((element) => element.scrollTop);
    expect(restoredScrollTop).toBe(documentScrollTop);
  } finally {
    for (const projectId of seed.project_ids) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
});

test("visual-focus-mode：生成桌面专注模式截图", async ({ page }) => {
  const seed = seedSourceReader();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "1440x900-focus-mode.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
    await page.getByRole("button", { name: "进入专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "true");
    await expect(page.getByRole("button", { name: "退出专注模式" })).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).toBeHidden();
    await expect(page.getByTestId("material-library")).toBeHidden();
    await expect(page.getByTestId("question-context-toolbar")).toContainText("source reader question");
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(hasHorizontalOverflow).toBe(false);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-workspace-breakpoints：生成桌面断点矩阵截图", async ({ page }) => {
  const seed = seedSourceReader();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const viewports = [
    { width: 1440, height: 900, columns: [248, null, 420], minMiddle: 520, inspector: "block", overlay: false },
    { width: 1280, height: 832, columns: [248, null, 420], minMiddle: 520, inspector: "block", overlay: false },
    { width: 1200, height: 800, columns: [220, null, 360], minMiddle: 480, inspector: "block", overlay: false },
    { width: 1024, height: 768, columns: [220, null], minMiddle: 700, inspector: "block", overlay: true }
  ];
  try {
    mkdirSync(evidenceDir, { recursive: true });
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/?questionId=${seed.question_id}`);
      await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
      const metrics = await workspaceBreakpointMetrics(page);
      expect(metrics.gridHeight).toBe(viewport.height);
      expect(metrics.horizontalOverflow).toBeLessThanOrEqual(1);
      expect(metrics.verticalOverflow).toBeLessThanOrEqual(1);
      expect(metrics.columns.length).toBe(viewport.columns.length);
      expect(Math.round(metrics.columns[0])).toBe(viewport.columns[0]);
      expect(metrics.columns[1]).toBeGreaterThanOrEqual(viewport.minMiddle);
      if (viewport.columns[2] !== null && viewport.columns[2] !== undefined) {
        expect(Math.round(metrics.columns[2])).toBe(viewport.columns[2]);
      }
      expect(metrics.inspectorDisplay).toBe(viewport.inspector);
      if (viewport.overlay) {
        expect(metrics.inspectorPosition).toBe("fixed");
        expect(metrics.inspectorWidth).toBe(420);
        await expect(page.getByTestId("source-card").first()).toBeVisible();
        await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
        await expect(page.getByTestId("source-reader")).toBeVisible();
        await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
      }
      await page.screenshot({
        path: resolve(evidenceDir, `${viewport.width}x${viewport.height}-workspace-breakpoints.png`),
        fullPage: true
      });
      expect(statSync(resolve(evidenceDir, `${viewport.width}x${viewport.height}-workspace-breakpoints.png`)).size).toBeGreaterThan(1000);
    }
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-hard-errors：固定 viewport 无布局硬错误", async ({ page }) => {
  const seed = seedSourceReader();
  const viewports = [
    { width: 1440, height: 900 },
    { width: 1280, height: 832 },
    { width: 1200, height: 800 },
    { width: 1024, height: 768 },
    { width: 390, height: 844 }
  ];
  try {
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto(`/?questionId=${seed.question_id}`);
      await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
      await expect(page.getByTestId("app-shell")).toBeVisible();
      const errors = await visualHardErrors(page, `${viewport.width}x${viewport.height}`, { requireCoverageTargets: true });
      expect(errors).toEqual([]);
    }
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-screenshot-matrix：生成 v0.2.0 视觉截图矩阵和 manifest", async ({ page }, testInfo) => {
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  rmSync(evidenceDir, { recursive: true, force: true });
  mkdirSync(evidenceDir, { recursive: true });
  const records: VisualEvidenceRecord[] = [];
  const projectIdsToDelete: number[] = [];
  const browserName = testInfo.project.name;
  const viewport = {
    desktop: { width: 1440, height: 900 },
    wide: { width: 1280, height: 832 },
    compact: { width: 1200, height: 800 },
    tablet: { width: 1024, height: 768 },
    mobile: { width: 390, height: 844 }
  };

  try {
    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "first-empty-project",
      dataCommand: "scripts/reset_demo.py",
      viewports: [viewport.desktop],
      prepare: async () => {
        await page.goto("/");
        await expect(page.getByRole("heading", { name: "尚未创建项目" })).toBeVisible();
      }
    });

    const projectSeed = seedProjectWithCounts();
    const documentSeed = seedDocumentDetails();
    const processingSeed = seedProcessingFailure();
    const pollingSeed = seedProcessingPolling();
    const sourceSeed = seedSourceReader();
    const confidenceSeed = seedConfidenceLevels();
    const noSourceSeed = seedNoSourceActions();
    const longListsSeed = seedLongLists();
    projectIdsToDelete.push(
      projectSeed.id,
      documentSeed.project_id,
      processingSeed.project_id,
      pollingSeed.project_id,
      sourceSeed.project_id,
      confidenceSeed.project_id,
      noSourceSeed.project_id,
      ...longListsSeed.project_ids
    );

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "project-created",
      dataCommand: "scripts/seed_project_counts.py",
      viewports: [viewport.wide],
      prepare: async () => {
        await page.goto("/");
        await page.getByRole("button", { name: new RegExp(projectSeed.name) }).click();
        await expect(page.getByRole("heading", { name: projectSeed.name })).toBeVisible();
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "document-list",
      dataCommand: "scripts/seed_document_details.py",
      viewports: [viewport.desktop],
      prepare: async () => {
        await page.goto("/");
        await page.getByRole("button", { name: new RegExp(documentSeed.project_name) }).click();
        await expect(page.getByTestId("document-list").getByText("detail-completed.pdf")).toBeVisible();
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "document-health",
      dataCommand: "scripts/seed_document_details.py",
      viewports: [viewport.tablet],
      prepare: async () => {
        await page.goto("/");
        await page.getByRole("button", { name: new RegExp(documentSeed.project_name) }).click();
        await expect(page.getByTestId("document-list")).toContainText("PDF 文件损坏，无法读取");
        await expect(page.getByTestId("document-list")).toContainText("PDF 无可提取文字层，v0.2.0 不进入 OCR");
      }
    });

    await captureUploadingState(page, records, browserName, projectIdsToDelete, [viewport.mobile]);

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "processing-rail-running",
      dataCommand: "scripts/seed_processing_polling.py",
      viewports: [viewport.desktop],
      prepare: async () => {
        await page.goto("/");
        await page.getByRole("button", { name: new RegExp(pollingSeed.project_name) }).click();
        await expect(page.getByTestId(`processing-track-${pollingSeed.document_ids[0]}`)).toContainText("提取文字");
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "processing-failure-actions",
      dataCommand: "scripts/seed_processing_failure.py",
      viewports: [viewport.wide],
      prepare: async () => {
        await page.goto("/");
        await page.getByRole("button", { name: new RegExp(processingSeed.project_name) }).click();
        const row = page.getByTestId(`document-row-${processingSeed.reprocess_document_id}`);
        await expect(row.getByTestId(`document-failure-actions-${processingSeed.reprocess_document_id}`)).toBeVisible();
        await expect(row).toContainText("PDF 文件损坏，无法读取");
      }
    });

    await captureQuestionSearchState(page, records, browserName, sourceSeed, [viewport.compact]);

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "source-confidence-levels",
      dataCommand: "scripts/seed_confidence_levels.py",
      viewports: [viewport.tablet],
      prepare: async () => {
        await openQuestionProject(page, confidenceSeed.question_id, confidenceSeed.project_name);
        const sourceResults = page.getByTestId("source-results-list");
        await expect(sourceResults.getByText("强相关")).toBeVisible();
        await expect(sourceResults.getByText("可参考")).toBeVisible();
        await expect(sourceResults.getByText("低置信")).toBeVisible();
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "no-reliable-source",
      dataCommand: "scripts/seed_no_source_actions.py",
      viewports: [viewport.mobile],
      prepare: async () => {
        await openQuestionProject(page, noSourceSeed.question_id, noSourceSeed.project_name);
        await expect(page.getByTestId("no-source-actions")).toBeVisible();
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "focus-mode",
      dataCommand: "scripts/seed_source_reader.py",
      viewports: [viewport.desktop],
      prepare: async () => {
        await openQuestionProject(page, sourceSeed.question_id, sourceSeed.project_name);
        await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
        await page.getByRole("button", { name: "进入专注模式" }).click();
        await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "true");
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "source-detail",
      dataCommand: "scripts/seed_source_reader.py",
      viewports: [viewport.wide],
      prepare: async () => {
        await openQuestionProject(page, sourceSeed.question_id, sourceSeed.project_name);
        await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
        await expect(page.getByTestId("source-reader-source-text")).toContainText("source reader hit");
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "source-page-nav",
      dataCommand: "scripts/seed_source_reader.py",
      viewports: [viewport.compact],
      prepare: async () => {
        await openQuestionProject(page, sourceSeed.question_id, sourceSeed.project_name);
        await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
        await page.getByRole("button", { name: "下一页" }).click();
        await expect(page.getByTestId("source-reader-meta")).toContainText("第 2 / 2 页");
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "pdf-reader",
      dataCommand: "scripts/seed_source_reader.py",
      viewports: [viewport.tablet],
      prepare: async () => {
        await openQuestionProject(page, sourceSeed.question_id, sourceSeed.project_name);
        await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
        await expect(page.getByTestId("source-reader-pdf")).toBeVisible();
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "long-lists",
      dataCommand: "scripts/seed_long_lists.py",
      viewports: [viewport.mobile],
      prepare: async () => {
        await openQuestionProject(page, longListsSeed.question_id, longListsSeed.project_name);
        await expect(page.getByTestId("document-list").locator("[data-testid^='document-row-']")).toHaveCount(20);
        await expect(page.getByTestId("source-card")).toHaveCount(20);
      }
    });

    await captureVisualMatrixState({
      page,
      records,
      browserName,
      state: "mobile-workspace",
      dataCommand: "scripts/seed_source_reader.py",
      viewports: [viewport.mobile],
      prepare: async () => {
        await openQuestionProject(page, sourceSeed.question_id, sourceSeed.project_name);
        await expect(page.getByTestId("sidebar-nav")).toBeVisible();
        await expect(page.getByTestId("trace-workspace")).toBeVisible();
        await expect(page.getByTestId("evidence-preview")).toBeVisible();
      }
    });

    expect(records).toHaveLength(visualMatrixStates.length);
    expect(new Set(records.map((record) => record.state))).toEqual(new Set(visualMatrixStates));
    expect(new Set(records.map((record) => record.viewport))).toEqual(new Set(visualMatrixViewports.map((item) => `${item.width}x${item.height}`)));
    writeFileSync(
      resolve(evidenceDir, "manifest.json"),
      JSON.stringify(
        {
          version: "v0.2.0",
          git_commit: execFileSync("git", ["rev-parse", "HEAD"], { cwd: resolve("."), encoding: "utf-8" }).trim(),
          generated_at: utcIsoNow(),
          screenshots: records
        },
        null,
        2
      ),
      "utf-8"
    );
  } finally {
    for (const projectId of projectIdsToDelete) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
});

test("visual-source-reader-mobile：生成移动端来源全屏详情截图", async ({ page }) => {
  const seed = seedSourceReader();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "390x844-source-reader-mobile.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();

    const reader = page.getByTestId("source-reader");
    await expect(reader).toBeVisible();
    await expect(reader.getByRole("button", { name: "返回题目" })).toBeVisible();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
    await expect(page.getByTestId("source-reader-source-text")).toContainText("source reader hit");

    const box = await reader.boundingBox();
    expect(box?.x).toBeLessThanOrEqual(1);
    expect(box?.y).toBeLessThanOrEqual(1);
    expect(box?.width).toBeGreaterThanOrEqual(389);
    expect(box?.height).toBeGreaterThanOrEqual(843);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);

    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-mobile-workspace：生成窄屏工作台截图并检查无横向溢出", async ({ page }) => {
  const seed = seedSourceReader();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "390x844-mobile-workspace.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/?questionId=${seed.question_id}`);

    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).toBeVisible();
    await expect(page.getByTestId("trace-workspace")).toBeVisible();
    await expect(page.getByTestId("evidence-preview")).toBeVisible();
    await expect(page.getByTestId("material-library")).toBeVisible();
    await expect(page.getByTestId("source-card").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "新建项目" })).toBeVisible();
    await expect(page.getByRole("button", { name: "查找资料依据" })).toBeVisible();
    await expect(page.getByTestId("source-card").first().getByRole("link", { name: "PDF" })).toBeVisible();

    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);

    const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(hasHorizontalOverflow).toBe(false);

    const overflowingButtons = await page.evaluate(() =>
      Array.from(document.querySelectorAll("button, [role='button']"))
        .filter((element) => {
          const style = window.getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
        })
        .filter((element) => element.scrollWidth > element.clientWidth + 1)
        .map((element) => element.textContent?.trim() ?? element.getAttribute("aria-label") ?? "")
    );
    expect(overflowingButtons).toEqual([]);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-question-history-long-text：长题干历史列表不撑开页面", async ({ page }) => {
  const seed = seedQuestionHistoryLongText();
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    const history = page.getByTestId("question-history");
    const historyList = page.getByTestId("question-history-list");
    await expect(history).toBeVisible();
    await expect(page.getByTestId("question-history-item")).toHaveCount(20);
    await expect(page.getByTestId("question-history-item").first()).toContainText("第 01 题");
    await expect(page.getByTestId("question-history-item").nth(19)).toContainText("第 20 题");

    const metrics = await page.evaluate(() => {
      const list = document.querySelector('[data-testid="question-history-list"]');
      const workspace = document.querySelector('[data-testid="trace-workspace"]');
      const items = Array.from(document.querySelectorAll('[data-testid="question-history-item"]'));
      if (!list || !workspace || items.length === 0) {
        throw new Error("question history metrics target missing");
      }
      const itemBoxes = items.map((item) => item.getBoundingClientRect());
      return {
        listClientHeight: list.clientHeight,
        listScrollHeight: list.scrollHeight,
        workspaceRight: workspace.getBoundingClientRect().right,
        viewportWidth: document.documentElement.clientWidth,
        documentOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        maxItemHeight: Math.max(...itemBoxes.map((box) => box.height)),
        maxItemRight: Math.max(...itemBoxes.map((box) => box.right))
      };
    });
    expect(metrics.listClientHeight).toBeLessThanOrEqual(302);
    expect(metrics.listScrollHeight).toBeGreaterThan(metrics.listClientHeight);
    expect(metrics.maxItemHeight).toBeLessThanOrEqual(112);
    expect(metrics.maxItemRight).toBeLessThanOrEqual(metrics.viewportWidth + 1);
    expect(metrics.workspaceRight).toBeLessThanOrEqual(metrics.viewportWidth + 1);
    expect(metrics.documentOverflow).toBeLessThanOrEqual(1);

    await page.getByTestId("question-history-item").first().click();
    await expect(page.getByTestId("question-history-item").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("evidence-preview")).toContainText("未找到可靠来源");
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-question-history-research：历史题目可回看并重新检索替换当前结果", async ({ page }) => {
  const seed = seedQuestionHistoryResearch();
  try {
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(page.getByTestId("question-history-item")).toHaveCount(1);
    await page.getByTestId("question-history-item").first().click();
    await expect(page.getByTestId("question-history-item").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-card")).toHaveCount(1);
    await expect(page.getByTestId("source-card").first()).toContainText("old history source");
    await expect(page.getByTestId("source-card").first()).toContainText("强相关");

    const researchResponse = page.waitForResponse(
      (response) => response.url() === `${apiUrl}/questions/${seed.question_id}/research` && response.request().method() === "POST"
    );
    const researchButton = page.getByTestId("question-context-toolbar").getByRole("button", { name: "重新检索" });
    await researchButton.click();
    await expect(researchButton).toBeDisabled();
    await expect(page.getByTestId("question-loading")).toContainText("正在检索来源");
    const response = await researchResponse;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { id: number; status: string; failure_reason: string | null; matches: unknown[] };
    expect(body.id).toBe(seed.question_id);
    expect(body.status).toBe("failed");
    expect(body.failure_reason).toBe("题目向量生成失败");
    expect(body.matches).toEqual([]);

    await expect(page.getByText("题目向量生成失败")).toBeVisible();
    await expect(page.getByTestId("source-card")).toHaveCount(0);
    await expect(page.getByText("old history source")).toHaveCount(0);
    await expect(page.getByTestId("question-history-item").first()).toContainText("检索失败");
    await expect(page.getByTestId("question-history-item").first()).toContainText("0 条来源");

    const detailResponse = await page.request.get(`${apiUrl}/questions/${seed.question_id}`);
    expect(detailResponse.status()).toBe(200);
    const detail = (await detailResponse.json()) as { status: string; failure_reason: string | null; matches: unknown[] };
    expect(detail.status).toBe("failed");
    expect(detail.failure_reason).toBe("题目向量生成失败");
    expect(detail.matches).toEqual([]);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-question-scope-errors：检索范围错误展示固定文案且不产生伪结果", async ({ page }) => {
  const seed = seedQuestionScopeErrors();
  try {
    await page.goto("/");
    await page.getByRole("button", { name: new RegExp(seed.project_name) }).click();
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    await page.getByRole("button", { name: "指定资料" }).click();
    await page.getByTestId(`document-scope-option-${seed.searchable_document_id}`).locator("input").check();
    await expect(page.getByTestId(`document-scope-option-${seed.processing_document_id}`)).toContainText("资料尚未完成处理");
    await expect(page.getByTestId(`document-scope-option-${seed.unsearchable_document_id}`)).toContainText("资料不可检索");
    await page.getByTestId("question-text").fill("验证检索范围错误不会生成伪结果");

    for (const scenario of [
      { ids: [], detail: "检索范围不能为空", status: 400 },
      { ids: [seed.other_document_id], detail: "检索范围包含不可用资料", status: 400 },
      { ids: [seed.processing_document_id], detail: "检索范围包含不可用资料", status: 400 },
      { ids: [seed.unsearchable_document_id], detail: "检索范围包含不可用资料", status: 400 }
    ]) {
      const response = await submitQuestionWithScopeOverride(page, seed.project_id, scenario.ids);
      expect(response.status()).toBe(scenario.status);
      expect((await response.json()).detail).toBe(scenario.detail);
      await expect(page.getByText(scenario.detail)).toBeVisible();
      await expect(page.getByTestId("source-card")).toHaveCount(0);
      await expect(page.getByTestId("question-history-item")).toHaveCount(0);
      await expect(page.getByText("系统不会生成无来源答案。")).toHaveCount(0);
    }
  } finally {
    for (const projectId of [seed.project_id, seed.other_project_id]) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
});

test("visual-question-history-long-text：生成长题干历史布局截图", async ({ page }) => {
  const seed = seedQuestionHistoryLongText();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const desktopScreenshotPath = resolve(evidenceDir, "1440x900-question-history-long-text.png");
  const mobileScreenshotPath = resolve(evidenceDir, "390x844-question-history-long-text.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    for (const viewport of [
      { width: 1440, height: 900, screenshotPath: desktopScreenshotPath },
      { width: 390, height: 844, screenshotPath: mobileScreenshotPath }
    ]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/");
      await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
      await expect(page.getByTestId("question-history-item")).toHaveCount(20);
      await page.screenshot({ path: viewport.screenshotPath, fullPage: true });
      expect(statSync(viewport.screenshotPath).size).toBeGreaterThan(1000);

      const hardErrors = await page.evaluate(() => {
        const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
        const list = document.querySelector('[data-testid="question-history-list"]');
        const items = Array.from(document.querySelectorAll('[data-testid="question-history-item"]'));
        return {
          overflow,
          listHasInternalScroll: list ? list.scrollHeight > list.clientHeight : false,
          maxItemHeight: items.length ? Math.max(...items.map((item) => item.getBoundingClientRect().height)) : 0
        };
      });
      expect(hardErrors.overflow).toBeLessThanOrEqual(1);
      expect(hardErrors.listHasInternalScroll).toBe(true);
      expect(hardErrors.maxItemHeight).toBeLessThanOrEqual(112);
    }
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-no-source-actions：无可靠来源状态提供三个行动入口", async ({ page }) => {
  const seed = seedNoSourceActions();
  try {
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();

    const actions = page.getByTestId("no-source-actions");
    await expect(actions).toBeVisible();
    await expect(actions).toContainText("未找到可靠来源");
    await expect(actions).toContainText("当前资料中没有达到可信阈值的来源片段。");
    await expect(actions.getByRole("button", { name: /扩大资料范围/ })).toBeVisible();
    await expect(actions.getByRole("button", { name: /检查资料索引/ })).toContainText("no-source-scanned.pdf");
    await expect(actions.getByRole("button", { name: /修改题目表述/ })).toBeVisible();

    await actions.getByRole("button", { name: /扩大资料范围/ }).click();
    await expect(page.getByTestId("document-scope-selector").getByRole("button", { name: "指定资料" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("document-scope-list")).toBeVisible();
    await expect(page.getByTestId(`document-scope-option-${seed.unavailable_document_id}`)).toContainText("不可检索");

    await actions.getByRole("button", { name: /检查资料索引/ }).click();
    const unavailableRow = page.getByTestId(`document-row-${seed.unavailable_document_id}`);
    await expect(unavailableRow).toBeVisible();
    await expect(unavailableRow).toContainText("no-source-scanned.pdf");
    await expect(unavailableRow).toContainText("PDF 无可提取文字层，v0.2.0 不进入 OCR");
    await expect(unavailableRow).toHaveClass(/ring-\[\#d9b86f\]/);
    await expect(page.getByTestId("document-detail")).toContainText("no-source-scanned.pdf");

    await actions.getByRole("button", { name: /修改题目表述/ }).click();
    await expect(page.getByTestId("question-text")).toHaveValue(seed.question_text);
    const activeElementId = await page.evaluate(() => document.activeElement?.id);
    expect(activeElementId).toBe("question");
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("visual-no-source-actions：生成无可靠来源行动入口截图", async ({ page }) => {
  const seed = seedNoSourceActions();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const desktopScreenshotPath = resolve(evidenceDir, "1440x900-no-source-actions.png");
  const mobileScreenshotPath = resolve(evidenceDir, "390x844-no-source-actions.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    for (const viewport of [
      { width: 1440, height: 900, screenshotPath: desktopScreenshotPath },
      { width: 390, height: 844, screenshotPath: mobileScreenshotPath }
    ]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/?questionId=${seed.question_id}`);
      await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
      await expect(page.getByTestId("no-source-actions")).toBeVisible();
      await expect(page.getByTestId("no-source-actions").getByRole("button")).toHaveCount(3);
      await page.screenshot({ path: viewport.screenshotPath, fullPage: true });
      expect(statSync(viewport.screenshotPath).size).toBeGreaterThan(1000);

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
    }
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
});

test("v020-long-lists：项目资料题目和来源长列表在区域内滚动", async ({ page }) => {
  const seed = seedLongLists();
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(page.getByTestId("project-list").getByRole("button")).toHaveCount(20);
    await expect(page.getByTestId("document-list").locator("[data-testid^='document-row-']")).toHaveCount(20);
    await expect(page.getByTestId("question-history-item")).toHaveCount(20);
    await expect(page.getByTestId("source-card")).toHaveCount(20);

    const metrics = await longListMetrics(page);
    expect(metrics.projectList.scrolls).toBe(true);
    expect(metrics.documentList.scrolls).toBe(true);
    expect(metrics.questionHistory.scrolls).toBe(true);
    expect(metrics.sourceResults.scrolls).toBe(true);
    expect(metrics.horizontalOverflow).toBeLessThanOrEqual(1);
    expect(metrics.pageHeight).toBeLessThanOrEqual(1800);
  } finally {
    for (const projectId of seed.project_ids) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
});

test("visual-long-lists：生成长列表布局截图", async ({ page }) => {
  const seed = seedLongLists();
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const desktopScreenshotPath = resolve(evidenceDir, "1440x900-long-lists.png");
  const mobileScreenshotPath = resolve(evidenceDir, "390x844-long-lists.png");
  try {
    mkdirSync(evidenceDir, { recursive: true });
    for (const viewport of [
      { width: 1440, height: 900, screenshotPath: desktopScreenshotPath, maxPageHeight: 1800 },
      { width: 390, height: 844, screenshotPath: mobileScreenshotPath, maxPageHeight: 3000 }
    ]) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/?questionId=${seed.question_id}`);
      await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
      await expect(page.getByTestId("project-list").getByRole("button")).toHaveCount(20);
      await expect(page.getByTestId("document-list").locator("[data-testid^='document-row-']")).toHaveCount(20);
      await expect(page.getByTestId("question-history-item")).toHaveCount(20);
      await expect(page.getByTestId("source-card")).toHaveCount(20);

      const metrics = await longListMetrics(page);
      expect(metrics.projectList.scrolls).toBe(true);
      expect(metrics.documentList.scrolls).toBe(true);
      expect(metrics.questionHistory.scrolls).toBe(true);
      expect(metrics.sourceResults.scrolls).toBe(true);
      expect(metrics.horizontalOverflow).toBeLessThanOrEqual(1);
      expect(metrics.pageHeight).toBeLessThanOrEqual(viewport.maxPageHeight);

      await page.screenshot({ path: viewport.screenshotPath, fullPage: true });
      expect(statSync(viewport.screenshotPath).size).toBeGreaterThan(1000);
    }
  } finally {
    for (const projectId of seed.project_ids) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
});

test("v020-upload-indeterminate-progress：上传字节不可计算时展示非百分比流动线", async ({ page }) => {
  await installIndeterminateUploadProbe(page);
  let projectId: number | null = null;
  try {
    await page.goto("/");
    const projectName = await createProject(page, "非百分比上传项目");
    projectId = await projectIdByName(page, projectName);

    await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));
    const progressCard = page.getByTestId("upload-progress-card");
    await expect(progressCard).toBeVisible();
    await expect(progressCard).toHaveAttribute("data-progress-mode", "indeterminate");
    await expect(page.getByTestId("upload-paper-thumbnail")).toHaveCSS("width", "32px");
    await expect(page.getByTestId("upload-paper-thumbnail")).toHaveCSS("height", "42px");
    await expect(page.getByTestId("upload-progress-filename")).toContainText("text-layer-material.pdf");
    const fillRatio = await page.evaluate(() => {
      const line = document.querySelector<HTMLElement>("[data-testid='upload-progress-line']");
      const fill = document.querySelector<HTMLElement>("[data-testid='upload-progress-fill']");
      if (!line || !fill) return 0;
      return fill.getBoundingClientRect().width / line.getBoundingClientRect().width;
    });
    expect(fillRatio).toBeGreaterThan(0.39);
    expect(fillRatio).toBeLessThan(0.41);
    await expect(progressCard).not.toContainText("%");
    await expect(progressCard).not.toContainText("剩余");
    await expect(progressCard).not.toContainText("速度");
    await expect(page.getByTestId("document-list").locator("[data-testid^='document-row-']")).toHaveCount(0);
    await expect(page.getByTestId("processing-stage-node-uploaded")).toHaveCount(0);

    await expect(progressCard).toHaveCount(0, { timeout: 10_000 });
    await expect(page.getByTestId("material-library").getByText("text-layer-material.pdf")).toBeVisible();
    await expect(page.getByTestId("document-list").locator("[data-testid^='document-row-']")).toHaveCount(1);
  } finally {
    if (projectId) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
});

test("v020-processing-progress：真实上传后处理轨道最终完成", async ({ page }) => {
  await installUploadSendDelayProbe(page);
  let projectId: number | null = null;
  let projectName: string | null = null;
  try {
    await page.goto("/");
    projectName = await createProject(page, "正常处理进度项目");
    projectId = await projectIdByName(page, projectName);

    const uploadResponsePromise = page.waitForResponse(
      (response) => response.url() === `${apiUrl}/projects/${projectId}/documents` && response.request().method() === "POST"
    );
    await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));

    const progressCard = page.getByTestId("upload-progress-card");
    await expect(progressCard).toBeVisible();
    await expect(page.getByTestId("upload-paper-thumbnail")).toHaveCSS("width", "32px");
    await expect(page.getByTestId("upload-paper-thumbnail")).toHaveCSS("height", "42px");
    await expect(page.getByTestId("upload-progress-filename")).toContainText("text-layer-material.pdf");
    await expect(progressCard).not.toContainText("%");

    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.status()).toBe(200);
    const uploadedDocument = (await uploadResponse.json()) as UploadedDocument;
    expect(uploadedDocument.filename).toBe("text-layer-material.pdf");

    await expect(progressCard).toHaveCount(0, { timeout: 10_000 });
    await expect(page.getByTestId("material-library").getByText("text-layer-material.pdf")).toBeVisible();
    const track = page.getByTestId(`processing-track-${uploadedDocument.id}`);
    await expect(track).toBeVisible();
    for (const label of ["上传完成", "提取文字", "切块", "生成 embedding", "建立索引", "完成"]) {
      await expect(track).toContainText(label);
    }

    await expect(page.getByTestId("document-status").filter({ hasText: "完成" })).toBeVisible({ timeout: 120_000 });
    await expect(track.getByTestId("processing-stage-node-completed")).toContainText("完成");
    const documentResponse = await page.request.get(`${apiUrl}/documents/${uploadedDocument.id}`);
    expect(documentResponse.status()).toBe(200);
    const completedDocument = (await documentResponse.json()) as UploadedDocument;
    expect(completedDocument.status).toBe("completed");
    expect(completedDocument.processing_stage).toBe("completed");
    expect(completedDocument.failed_stage).toBeNull();
    expect(completedDocument.failure_code).toBeNull();
    expect(completedDocument.failure_reason).toBeNull();
    expect(completedDocument.searchable).toBe(true);
    expect(completedDocument.chunk_count).toBeGreaterThan(0);
  } finally {
    if (projectId) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    } else if (projectName !== null) {
      const projectsResponse = await page.request.get(`${apiUrl}/projects`);
      if (projectsResponse.ok()) {
        const projects = (await projectsResponse.json()) as Project[];
        const project = projects.find((item) => item.name === projectName);
        if (project) {
          const deleteResponse = await page.request.delete(`${apiUrl}/projects/${project.id}`);
          expect([200, 404]).toContain(deleteResponse.status());
        }
      }
    }
  }
});

test("visual-upload-indeterminate-progress：生成非百分比上传流动线截图", async ({ page }) => {
  await installIndeterminateUploadProbe(page);
  const evidenceDir = resolve("tmp/v0.2.0-visual-evidence");
  const screenshotPath = resolve(evidenceDir, "1440x900-upload-indeterminate-progress.png");
  mkdirSync(evidenceDir, { recursive: true });
  let projectId: number | null = null;

  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    const projectName = await createProject(page, "非百分比上传截图项目");
    projectId = await projectIdByName(page, projectName);
    await page.getByTestId("document-file").setInputFiles(resolve("tests/fixtures/text-layer-material.pdf"));

    const progressCard = page.getByTestId("upload-progress-card");
    await expect(progressCard).toBeVisible();
    await expect(progressCard).toHaveAttribute("data-progress-mode", "indeterminate");
    await expect(progressCard).not.toContainText("%");
    await expect(progressCard).not.toContainText("剩余");
    await expect(progressCard).not.toContainText("速度");

    await page.screenshot({ path: screenshotPath, fullPage: true });
    expect(statSync(screenshotPath).size).toBeGreaterThan(1000);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  } finally {
    if (projectId) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
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

test("v020-confidence-levels：来源结果展示三档置信层级", async ({ page }) => {
  const seed = seedConfidenceLevels();
  try {
    await page.goto(`/?questionId=${seed.question_id}`);
    await expect(page.getByRole("heading", { name: seed.project_name })).toBeVisible();
    await expect(page.getByTestId("source-card")).toHaveCount(3);

    await expect(page.getByTestId("source-card").nth(0)).toContainText("confidence-levels.pdf 第 1 页");
    await expect(page.getByTestId("source-card").nth(0)).toContainText("strong confidence source");
    await expect(page.getByTestId("source-card").nth(0).getByTestId("source-confidence-pill")).toHaveText("强相关");
    await expect(page.getByTestId("source-card").nth(0)).toContainText("pgvector 相似度 0.9100");

    await expect(page.getByTestId("source-card").nth(1)).toContainText("reference confidence source");
    await expect(page.getByTestId("source-card").nth(1).getByTestId("source-confidence-pill")).toHaveText("可参考");
    await expect(page.getByTestId("source-card").nth(1)).toContainText("pgvector 相似度 0.6300");

    await expect(page.getByTestId("source-card").nth(2)).toContainText("low confidence source");
    await expect(page.getByTestId("source-card").nth(2).getByTestId("source-confidence-pill")).toHaveText("低置信");
    await expect(page.getByTestId("source-card").nth(2)).toContainText("pgvector 相似度 0.4400");
    await expect(page.getByText("系统不会生成无来源答案。")).toHaveCount(0);

    const response = await page.request.get(`${apiUrl}/questions/${seed.question_id}`);
    expect(response.status()).toBe(200);
    const detail = (await response.json()) as QuestionDetail;
    expect(detail.matches.map((match) => match.confidence_label)).toEqual(["强相关", "可参考", "低置信"]);
  } finally {
    const deleteResponse = await page.request.delete(`${apiUrl}/projects/${seed.project_id}`);
    expect([200, 404]).toContain(deleteResponse.status());
  }
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

test("v020-core-loop v020-full-regression：真实上传处理检索来源阅读闭环", async ({ page }) => {
  let projectId: number | null = null;
  let projectName: string | null = null;
  try {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Suton" })).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).toBeVisible();
    await expect(page.getByTestId("trace-workspace")).toBeVisible();
    await expect(page.getByTestId("evidence-preview")).toBeVisible();

    projectName = await createProject(page, "v020 总回归真实闭环");
    projectId = await projectIdByName(page, projectName);
    await expect(page.getByTestId("project-context-name")).toContainText(projectName);

    await uploadMaterial(page);
    await expect(page.getByTestId("document-status").filter({ hasText: "完成" })).toBeVisible();
    await expect(page.getByTestId("document-detail-searchable")).toContainText("可检索");

    const question = readFileSync(resolve("tests/fixtures/question.txt"), "utf-8").trim();
    await page.getByTestId("question-text").fill(question);
    const activeProjectId = projectId;
    const questionResponsePromise = page.waitForResponse(
      (response) => response.url() === `${apiUrl}/projects/${activeProjectId}/questions` && response.request().method() === "POST"
    );
    await page.getByRole("button", { name: "查找资料依据" }).click();
    const questionResponse = await questionResponsePromise;
    expect(questionResponse.status()).toBe(200);

    await expect(page.getByText("pgvector 相似度").first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("question-context-toolbar")).toContainText(question);
    await expect(page.getByTestId("source-card").first()).toContainText("text-layer-material.pdf");
    await expect(page.getByTestId("source-card").first().getByTestId("source-confidence-pill")).toBeVisible();
    await expect(page.getByText("系统不会生成无来源答案。")).toHaveCount(0);

    await page.getByTestId("source-card").first().getByRole("button", { name: /text-layer-material\.pdf/ }).click();
    const reader = page.getByTestId("source-reader");
    await expect(reader).toBeVisible();
    await expect(page.getByTestId("source-reader-filename")).toContainText("text-layer-material.pdf");
    await expect(page.getByTestId("source-reader-meta")).toContainText(/第 \d+ \/ \d+ 页 · 排序 1 ·/);
    await expect(page.getByTestId("source-reader-source-text")).toBeVisible();
    await expect(page.getByTestId("source-reader-context")).toBeVisible();
    await expect(page.getByTestId("source-reader-pdf")).toHaveAttribute("src", /\/documents\/\d+\/file#page=\d+$/);

    await page.getByRole("button", { name: "进入专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "true");
    await expect(page.getByTestId("sidebar-nav")).toBeHidden();
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
    await expect(page.getByTestId("source-reader")).toBeVisible();

    await page.getByRole("button", { name: "退出专注模式" }).click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-focus-mode", "false");
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    await expect(page.getByTestId("source-card").first()).toHaveAttribute("aria-current", "true");
  } finally {
    if (projectId !== null) {
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    } else if (projectName !== null) {
      const projectsResponse = await page.request.get(`${apiUrl}/projects`);
      if (projectsResponse.ok()) {
        const projects = (await projectsResponse.json()) as Project[];
        const project = projects.find((item) => item.name === projectName);
        if (project) {
          const deleteResponse = await page.request.delete(`${apiUrl}/projects/${project.id}`);
          expect([200, 404]).toContain(deleteResponse.status());
        }
      }
    }
  }
});

test("v020-full-regression：串行覆盖无可靠来源和来源页码导航前端状态", async ({ page }) => {
  let noSourceSeed: NoSourceActionsSeed | null = null;
  let sourceSeed: SourceReaderSeed | null = null;
  try {
    noSourceSeed = seedNoSourceActions();
    sourceSeed = seedSourceReader();

    await page.goto(`/?questionId=${noSourceSeed.question_id}`);
    await expect(page.getByRole("heading", { name: noSourceSeed.project_name })).toBeVisible();
    await expect(page.getByTestId("no-source-actions")).toBeVisible();
    await expect(page.getByTestId("no-source-actions").getByRole("button")).toHaveCount(3);
    await expect(page.getByText("系统不会生成无来源答案。")).toBeVisible();

    await page.goto(`/?questionId=${sourceSeed.question_id}`);
    await expect(page.getByRole("heading", { name: sourceSeed.project_name })).toBeVisible();
    await page.getByTestId("source-card").first().getByRole("button", { name: /source-reader\.pdf/ }).click();
    const reader = page.getByTestId("source-reader");
    await expect(reader).toBeVisible();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 1 / 2 页 · 排序 1 · 强相关");
    await reader.getByRole("button", { name: "下一页" }).click();
    await expect(page.getByTestId("source-reader-meta")).toContainText("第 2 / 2 页 · 排序 1 · 强相关");
    await expect(reader.getByRole("button", { name: "回到命中页" })).toBeEnabled();
  } finally {
    for (const projectId of [noSourceSeed?.project_id, sourceSeed?.project_id]) {
      if (projectId === undefined) continue;
      const deleteResponse = await page.request.delete(`${apiUrl}/projects/${projectId}`);
      expect([200, 404]).toContain(deleteResponse.status());
    }
  }
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

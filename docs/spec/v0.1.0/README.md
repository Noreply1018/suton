# Suton v0.1.0 Spec

## 版本目标

v0.1.0 要验证 Suton 的最小可用闭环：

> 用户创建项目，上传带文字层的资料 PDF，系统解析并建立可检索资料索引；用户手动输入一道题，系统返回带来源的资料页码、片段和原始 PDF 页码入口。

本版本面向考前复习和课程速通场景中最常见的“从题目反查资料依据”需求。用户可见结果是一个 Web App 原型：左侧或主区域管理项目、资料和题目，右侧或结果区域展示可追溯的资料依据。

本版本明确不解决扫描件 OCR、试题 PDF 自动切题、AI 讲解、知识图谱、覆盖分析、引用完整性分析和移动端 APK。

后续版本再处理 OCR、自动切题、页图高亮、混合检索重排、多文件格式、任务批处理和更完整的分析面板。

## 范围分类

### 功能新增

- [项目创建与项目页](items/feature-001-project.md)
- [资料 PDF 上传与状态](items/feature-002-document-upload.md)
- [手动输入题目](items/feature-003-question-input.md)
- [资料依据结果展示](items/feature-004-source-results.md)

### 数据与接口变更

- [核心数据模型](items/data-001-core-model.md)

### 处理链路变更

- [PDF 文字提取、切块与索引](items/pipeline-001-document-processing.md)

### 验证与发布门禁

- [v0.1.0 验证门禁](items/gate-001-v0.1.0-validation.md)

## 行为兼容与约束

- v0.1.0 只要求支持有文字层的 PDF。
- v0.1.0 只要求本地单用户使用，不包含登录、权限、团队协作和多租户隔离。
- v0.1.0 只要求本地文件系统存储上传文件，不包含对象存储。
- v0.1.0 的题目来源为用户手动输入或粘贴，不包含试题 PDF 上传和自动切题。
- v0.1.0 的资料依据必须绑定文件、页码和原文片段；无来源结果不得展示。
- v0.1.0 必须使用最小 embedding 检索；关键词检索不参与结果排序，不得替代 embedding 检索。
- v0.1.0 不允许输出长篇 AI 讲解或无来源答案。

## 固定技术语义

v0.1.0 实现必须使用以下固定技术栈，不得在实现时临场替换：

- 前端：Next.js、React、Tailwind CSS、pnpm。
- 后端：Python FastAPI、uv。
- 数据库：PostgreSQL + pgvector。
- 后台任务：Redis + RQ。
- 文件存储：本地 `uploads/` 目录。
- PDF 文字层提取：PyMuPDF。
- 向量存储与相似度检索：pgvector。
- 浏览器端到端验证：Playwright。

以下语义在 v0.1.0 中保持阻塞，不得实现或验证相关链路，直到用户另行固定：

- embedding provider、模型名称、向量维度和调用方式。

## 固定验证资料

- 固定资料 PDF：`tests/fixtures/text-layer-material.pdf`。
- 固定试题来源 PDF：`tests/fixtures/question-source.pdf`。
- 固定样例题目文本：`tests/fixtures/question.txt`。

`tests/fixtures/question-source.pdf` 只作为人工摘录题目的来源证据，不进入 v0.1.0 自动切题或 OCR 链路。`tests/fixtures/question.txt` 必须由用户或人工核验流程从试题来源中摘录并确认；该文件缺失时，题目检索验证保持阻塞。

## 明确不包含的范围

- APK、PWA 和移动端专项适配。
- OCR 主链路、扫描版 PDF、拍照题目和图片资料识别。
- PPT、Word、图片、Markdown、HTML 等非 PDF 资料上传。
- 试题 PDF 上传、题目截图裁剪、自动切题。
- 大模型重排、AI 长篇讲解、AI 直接给答案。
- 知识图谱。
- 覆盖分析。
- 引用完整性分析。
- 错题本、学习计划、社区题库。
- 多用户、权限、团队协作。
- 对象存储、生产部署、CI/CD 发布、GitHub Release。
- bbox 高亮、公式结构理解、表格结构理解。

## UI 参考边界

用户提供的 UI 草案作为 v0.1.0 的视觉和信息架构参考，但不作为完整功能承诺。

v0.1.0 固定吸收：

- 左侧项目导航。
- 项目概览。
- 资料库入口。
- 题目输入或任务入口。
- 溯源结果预览。
- 资料依据卡片。

v0.1.0 不吸收：

- 知识图谱。
- 覆盖分析。
- 引用完整性。
- 复杂统计图表。
- 多题库批量进度。
- 自动索引进度百分比的完整统计体系。

## 验证总规则

- v0.1.0 实现必须提供可复现的本地验证命令，至少包括：

```text
make env-info
make reset-demo
make dev
make migrate
make process-demo
make verify-db
make verify-e2e
make test
```

- `make env-info` 必须输出 Node.js、pnpm、Python、uv、PostgreSQL、pgvector、Redis、RQ、embedding provider、Playwright 浏览器、操作系统和关键环境变量是否存在。
- `make reset-demo` 必须清理旧上传、旧索引和旧数据库记录。
- `make dev` 必须启动前端、后端、数据库连接和 Redis/RQ 后台处理能力；缺少任一条件时必须明确输出缺失条件并失败。
- `make migrate` 必须执行数据库迁移或初始化 schema。
- `make process-demo` 必须处理固定样例 PDF，并生成页面文本、chunk 和 embedding。
- `make verify-db` 必须执行数据库核验，并必须支持通过 `CHECK=<name>` 指定检查项目。
- `make verify-e2e` 必须执行 v0.1.0 最小闭环 Playwright 浏览器端到端验证。
- `make test` 必须执行 v0.1.0 相关自动化测试。
- 必须使用真实 Web 应用验证项目、上传、处理、题目输入和结果展示。
- 必须使用真实后端服务验证 API 行为，不允许只依赖 mock。
- 必须使用真实数据库验证项目、资料、页面、chunk、题目和匹配结果落库。
- 必须使用 `tests/fixtures/text-layer-material.pdf` 验证资料处理链路。样例 PDF 必须经 PyMuPDF 文字层提取核验。
- 必须使用 `tests/fixtures/question.txt` 验证题目到资料依据的检索结果。
- 每条资料依据必须包含文件名、页码、原文片段、pgvector 相似度分数、确定性命中原因和原始 PDF 页码入口。
- 没有明确来源的结果不得进入前端列表。
- 验证前必须清理旧上传、旧索引和旧数据库记录，避免依赖历史状态。

## 发布门禁

v0.1.0 发布前必须满足：

- 所有条目状态为已完成。
- 所有条目的验证矩阵结论为通过。
- 真实 Web 构建、服务启动、数据库连接、资料上传、PDF 处理、题目输入、资料依据展示通过。
- 固定样例 PDF 与固定样例题目的验收记录完整。
- 文档与实际行为一致。
- 工作区相关改动已完成 subagent 严格审计，且审计结论为通过。
- 审计通过后提交并推送到远端仓库。

## Spec 变更记录

| 时间 | 变更 | 来源 | 证据 |
|---|---|---|---|
| 2026-05-28 | 创建 v0.1.0 范围：有文字层 PDF、手动题目输入、最小 embedding 检索、来源结果展示；排除 OCR、自动切题、知识图谱、覆盖分析和引用完整性。 | 用户确认与本地 spec 编写 | 本文档与 `items/` 条目 |
| 2026-05-29 | 固定 v0.1.0 技术栈为 Next.js/React/Tailwind、FastAPI、PostgreSQL/pgvector、Redis/RQ、PyMuPDF、Playwright；固定资料与试题来源 fixture；embedding provider/model/dimension 保持阻塞待用户确认。 | 用户确认与本地 spec 收窄 | 本文档与 `tests/fixtures/` |

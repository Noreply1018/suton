# Suton v0.2.0 Spec

## 版本目标

v0.2.0 要把 Suton 从“能完成资料溯源的技术原型”升级为“用户愿意长期打开的简约高效复习工作台”。

本版本的核心不是增加更多 AI 能力，而是彻底重构前端体验、项目管理、资料管理、上传处理反馈、题目检索工作流和来源阅读体验。v0.2.0 必须清除 v0.1.0 前端设计遗留影响，重新建立视觉系统、布局系统和交互系统，并补齐资料健康度、来源置信层级、专注模式、无可靠来源行动入口、PDF 页码导航、失败修复入口和首次空项目体验。

v0.2.0 的一句话定义是：

> 以高级浅色自然系视觉、固定工作台布局和可追溯来源阅读为核心，重做 Suton 的完整前端体验。

本版本面向真实考前复习场景：用户需要管理多个课程项目、上传多份资料、持续输入和回看题目，并快速从检索结果进入对应 PDF 页和命中段落。

## 当前建设状态

v0.2.0 仍处于 spec 建设阶段，尚未进入实现期。条目状态只表示文档语义成熟度，不表示功能完成；验证矩阵中没有真实证据前不得把任何条目标记为“已完成”。

| 条目 | 状态 | 当前结论 | 下一步 |
|---|---|---|---|
| `design-001-frontend-rebuild.md` | 草案 | 视觉方向、设计 token、核心组件和旧前端清除契约已收紧 | 与实现期视觉 token 检查保持同步 |
| `design-002-workspace-layout.md` | 草案 | 桌面、平板、移动、滚动容器和专注模式布局契约已收紧 | 与实现期断点和恢复验证保持同步 |
| `feature-001-project-management.md` | 草案 | 项目命名、唯一性、重命名、删除交互和硬删除语义已收紧 | 与实现期 API 契约检查保持同步 |
| `feature-002-document-management.md` | 草案 | 资料删除、重处理、健康度、详情字段和检索范围语义已收紧 | 与实现期资料健康度和范围筛选验证保持同步 |
| `feature-003-processing-progress.md` | 草案 | 上传进度、处理阶段、失败入口、刷新恢复和轮询语义已收紧 | 与实现期处理阶段和视觉验证保持同步 |
| `feature-004-source-reader.md` | 草案 | 来源详情、PDF 页码导航和失败状态已固定 | 与数据接口条目保持字段级一致 |
| `feature-005-question-workflow.md` | 草案 | 历史题目、重新检索、无可靠来源、置信层级和题目响应契约已收紧 | 与实现期题目 API 和无来源行动入口验证保持同步 |
| `data-001-v020-model-api.md` | 草案 | 数据模型、项目/资料/题目接口形状、错误码、删除事务和迁移规则已进一步收紧 | 与实现期 API、DB 和总体验收门禁保持同步 |
| `gate-001-visual-quality.md` | 草案 | 视觉截图、硬错误、证据 manifest 和人工审美门禁已收紧 | 与实现期 `make verify-visual` 落地保持同步 |
| `gate-002-v020-validation.md` | 草案 | 总体验收命令、占位阻塞、证据归档和发布阻塞原则已收紧 | 与实现期真实验证 target 落地保持同步 |

## 范围分类

### 设计优化

- [前端彻底重构与视觉系统](items/design-001-frontend-rebuild.md)
- [工作台信息架构与布局约束](items/design-002-workspace-layout.md)
- [视觉质量与审美门禁](items/gate-001-visual-quality.md)

### 功能新增

- [项目管理完整化](items/feature-001-project-management.md)
- [资料管理完整化](items/feature-002-document-management.md)
- [上传与处理进度可视化](items/feature-003-processing-progress.md)
- [来源阅读与 PDF 详情视图](items/feature-004-source-reader.md)
- [题目历史与检索体验](items/feature-005-question-workflow.md)

### 数据与接口变更

- [v0.2.0 数据与接口约束](items/data-001-v020-model-api.md)

### 验证与发布门禁

- [v0.2.0 总体验收门禁](items/gate-002-v020-validation.md)

## 行为兼容与约束

- v0.2.0 继续遵守“资料来源优先”：展示给用户的依据必须绑定文件 ID、文件名、页码、chunk ID、原文片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因。
- v0.2.0 必须替换前端信息架构、组件结构、页面路由、样式系统和交互方式；v0.1.0 前端代码和布局不得保留为运行路径、备用路径或死代码。
- v0.2.0 必须保留 v0.1.0 已跑通的核心后端闭环：项目、资料 PDF 上传、PyMuPDF 文字层解析、chunk、embedding、pgvector 检索、Redis/RQ 后台处理和来源结果返回。
- v0.2.0 不允许把旧前端页面简单换色、套壳或局部修补后标记为完成；前端必须重构为新的工作台体验。旧前端实现内容必须被替换，未被新工作台使用的旧组件、旧样式和旧页面结构必须删除。
- 项目名称不得使用演示默认值污染真实使用流程。新建项目必须由用户输入名称。
- 同一工作区内项目名称必须唯一。
- 页面整体不得因为项目列表、资料列表、题目历史或结果列表无限拉长。桌面端固定为左侧项目栏、中间主工作区、右侧来源阅读区；项目列表、资料列表、题目历史和来源结果都必须在各自区域内滚动。移动端固定为底部三段导航：项目、检索、来源；来源阅读使用全屏详情层。
- v0.2.0 的视觉基调固定为 Nature 论文式高级浅色自然系：低饱和、清爽、克制、有纸张与学术产品气质；不得使用厚重暗色、廉价渐变、花哨紫蓝、卡片堆叠或默认模板感。
- v0.2.0 前端设计必须参考成熟产品的信息密度、留白、排版、导航和状态处理方法，但不得复制任何特定产品的布局、文案、图标组合、品牌元素或可识别视觉资产。参考对象只能作为设计质量标尺，不得作为抄袭来源。

## 固定验证资料

- 固定资料 PDF：`tests/fixtures/text-layer-material.pdf`。
- 固定试题来源 PDF：`tests/fixtures/question-source.pdf`。
- 固定样例题目文本：`tests/fixtures/question.txt`。
- 固定无匹配题目文本：`tests/fixtures/unmatched-question.txt`。
- 固定损坏 PDF：`tests/fixtures/broken.pdf`。
- 固定非 PDF 文件：`tests/fixtures/not-pdf.txt`。
- 固定扫描件 PDF：`tests/fixtures/scanned.pdf`。

v0.2.0 验证不得临时替换上述 fixture。若需要新增视觉或长列表 fixture，必须先写入本节和对应 item。

## 明确不包含的范围

- OCR 主链路、扫描版 PDF 识别、拍照题目识别。
- 自动切题、试题 PDF 上传和题目截图裁剪。
- AI 长篇讲解、无来源答案、AI 直接答题。
- 知识图谱、覆盖分析、引用完整性分析。
- APK、PWA 和移动端专项应用发布。
- 多用户、权限、团队协作、分享和云端同步。
- 对象存储、生产级运维、计费和账号体系。
- PDF bbox 高亮。v0.2.0 只要求跳转目标页、展示命中段落和上下文；bbox 高亮留给后续版本。

## 验证总规则

v0.2.0 发布前必须完成真实 Web、真实后端、真实数据库、真实 Redis/RQ、真实文件上传和真实浏览器验证。除 v0.1.0 既有验证命令外，v0.2.0 必须新增或更新以下验证：

```text
make env-info
make reset-demo
make migrate
make dev
make verify-e2e SCENARIO=v020-full-regression
make verify-api-contract CHECK=v020-model-api
make verify-db CHECK=v020-schema
make verify-visual CHECK=screenshot-matrix
make verify-visual CHECK=visual-hard-errors
make verify-visual CHECK=visual-evidence-manifest
make verify-visual CHECK=aesthetic-audit-record
make test
make evidence-package-with-tests
make verify-spec
make verify-secrets
```

当前 `make verify-spec` 对 v0.2.0 只执行草案结构检查，用于防止缺文件、缺字段和核心约束缺失；它不代表 v0.2.0 功能、视觉、数据库或 E2E 验证已经实现。v0.2.0 实现期必须把本 spec 中列出的 `SCENARIO=v020-*`、`CHECK=v020-*` 和 `make verify-visual CHECK=*` 全部落成真实验证，再将条目状态更新为已完成。

当前仓库尚未实现 `make verify-visual`、`make verify-api-contract` 和所有 `CHECK=v020-*` 检查；因此所有引用这些命令的 v0.2.0 验证矩阵行必须保持 `未验证 / 待补充 / 阻塞`。进入 v0.2.0 实现验收前，必须先把这些命令作为真实 Make target 或真实 `CHECK` 分支落地，且不得用空脚本、mock、dry-run 或只检查文件存在的脚本替代真实验证。

v0.2.0 发布证据必须执行 `make evidence-package-with-tests` 生成，并固定写入 `tmp/v0.2.0-evidence-latest.md`；证据必须包含必需命令、退出码、执行时间、Git commit、数据准备命令、证据路径和结论，并通过 `make verify-secrets` 确认不含 secret。

v0.2.0 还必须形成视觉证据：

- 桌面 viewport 截图：1440x900、1280x832。
- 紧凑桌面和窄屏 viewport 截图：1200x800、1024x768。
- 移动 viewport 截图：390x844。
- 主要状态截图：首次空项目、新建项目、资料列表、资料健康度、纸页入库上传中、处理轨道运行中、处理失败修复入口、题目检索、来源置信层级、无可靠来源、专注模式、来源详情、PDF 页码导航、PDF 阅读视图、长列表、移动工作台。
- 人工审美审计记录：必须明确结论为通过，否则不得发布。

视觉验收必须检查：

- 是否清除 v0.1.0 前端视觉遗留。
- 是否符合高级浅色自然系。
- 是否简约、高效、可长期使用。
- 是否存在文本溢出、重叠、错位、无限撑长页面、低价值大面积空白或默认模板感。
- 是否有清晰的当前项目、当前资料、当前题目和当前来源。

## 发布门禁

v0.2.0 发布前必须满足：

- 所有 v0.2.0 条目状态为已完成。
- 所有验证矩阵结论为通过。
- 前端旧设计已彻底删除，旧组件、旧样式和旧页面结构不再保留在运行路径或源码死角中。
- 新前端通过视觉质量与审美门禁。
- 项目管理、资料管理、上传进度、题目检索、来源阅读和 PDF 详情视图在真实浏览器中通过。
- 数据库迁移和兼容路径通过。
- 无来源结果不得展示。
- `make verify-spec` 和 `make verify-secrets` 通过；其中 `make verify-spec` 必须同时覆盖 v0.1.0 release gate 和 v0.2.0 spec 结构检查。
- 修改已追踪文件后已完成 subagent 严格审计，审计通过后完成 Git 提交。
- 若后续纳入远端仓库、tag、GitHub Release、镜像仓库或 CI，必须先新增对应 spec，并通过可追溯外部证据核验。

## Spec 变更记录

| 时间 | 变更 | 来源 | 证据 |
|---|---|---|---|
| 2026-06-01 | 创建 v0.2.0 范围：彻底前端重构、高级浅色自然系视觉、简约高效工作台、项目/资料管理完整化、上传进度、来源阅读、题目历史、视觉审美门禁；明确不做 OCR、自动切题、AI 长篇讲解、APK 和 bbox 高亮。 | 用户反馈与本地 spec 编写 | 本文档与 `items/` 条目 |
| 2026-06-01 | 增加当前建设状态表；开始冻结数据/API、题目检索和来源阅读字段级契约；明确状态表不代表功能完成。 | v0.2.0 spec 逐项建设 | 本文档与 `items/data-001-v020-model-api.md`、`items/feature-004-source-reader.md`、`items/feature-005-question-workflow.md` |
| 2026-06-01 | 细化项目管理、资料管理和处理进度：固定项目交互、名称边界、删除后选择规则、资料详情字段、健康度计算、检索范围禁用规则、处理阶段映射、上传进度和轮询恢复语义。 | v0.2.0 spec 逐项建设 | `items/feature-001-project-management.md`、`items/feature-002-document-management.md`、`items/feature-003-processing-progress.md` |
| 2026-06-01 | 细化前端设计、工作台布局和视觉门禁：固定设计 token、核心组件清单、断点布局、滚动容器、专注模式恢复、截图证据路径、manifest 和审美审计记录契约。 | v0.2.0 spec 逐项建设 | `items/design-001-frontend-rebuild.md`、`items/design-002-workspace-layout.md`、`items/gate-001-visual-quality.md` |
| 2026-06-01 | 细化题目工作流和数据/API 契约：固定题目详情响应、历史列表字段、重新检索事务、无可靠来源行动入口、题目失败字段和题目 API 验证矩阵。 | v0.2.0 spec 逐项建设 | `items/feature-005-question-workflow.md`、`items/data-001-v020-model-api.md` |
| 2026-06-01 | 细化总体验收门禁：固定 v0.2.0 验证 target 真实性、占位阻塞规则、证据归档字段、secret 禁止项和总验收清单 viewport 口径。 | v0.2.0 spec 逐项建设 | `items/gate-002-v020-validation.md`、`acceptance-checklist.md` |
| 2026-06-01 | 补齐数据/API 响应形状：固定 `document_pages`、项目对象、资料对象、`latest_status`、`text_quality_label`、项目 `updated_at` 更新语义和项目/资料响应字段验证矩阵。 | v0.2.0 spec 逐项建设 | `items/data-001-v020-model-api.md` |

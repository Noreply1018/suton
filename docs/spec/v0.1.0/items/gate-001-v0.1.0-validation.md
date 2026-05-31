# v0.1.0 验证门禁

- 类型：验证与发布门禁
- 状态：已完成
- 背景：v0.1.0 的目标是验证最小闭环，必须用固定资料和固定题目证明链路可运行。
- 当前问题：如果只凭页面静态展示或 mock 数据判断完成，无法证明 Suton 的资料溯源价值成立。
- 目标行为：发布前完成真实 Web、后端、数据库、资料处理和题目检索验证，并保留可追溯证据。
- 非目标：不包含生产部署、GitHub Release、CI/CD 强制通过、性能压测、移动端验证。
- 发布必要性：必须发布
- 用户可见影响：用户不会直接看到门禁，但门禁保证 v0.1.0 不是静态原型。
- 涉及模块：前端、后端、数据库、文件存储、处理任务、检索、文档。
- 配置、接口或数据结构变化：无。
- 兼容性要求：无特殊要求。
- 验收标准：
  - 准备固定有文字层 PDF `tests/fixtures/text-layer-material.pdf` 作为测试资料，并通过 PyMuPDF 文字层提取核验。
  - 准备固定试题来源 PDF `tests/fixtures/question-source.pdf`。
  - 准备固定样例题目 `tests/fixtures/question.txt`，并人工确认其来自 `tests/fixtures/question-source.pdf`。
  - 清理旧上传、旧索引、旧数据库记录后执行验证。
  - 真实启动前端、后端和数据库。
  - 完成项目创建、资料上传、资料处理、题目输入、资料依据展示。
  - 至少 1 条结果可追溯到文件名、页码、原文片段和原始 PDF 页码入口。
  - 所有 v0.1.0 条目验证矩阵结论为通过。
  - `make verify-spec` 和 `make verify-secrets` 通过。
  - 需要归档证据时使用 `make evidence-package` 或 `make evidence-package-with-tests` 生成脱敏证据包。
  - subagent 审计通过后才能提交发布相关改动。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 最小闭环验证 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实 FastAPI 后端；真实 Redis/RQ worker；真实 PostgreSQL/pgvector；本地文件系统；embedding provider、模型、维度和调用方式已固定并可用 | 已准备 `tests/fixtures/text-layer-material.pdf`、`tests/fixtures/question-source.pdf` 和 `tests/fixtures/question.txt`，已执行 `make reset-demo` | 执行 `make migrate`；执行 `make dev`；执行 `make process-demo FILE=tests/fixtures/text-layer-material.pdf`；执行 `make verify-e2e SCENARIO=minimal-loop QUESTION=tests/fixtures/question.txt`；执行 `make verify-db CHECK=source-lineage` | 返回至少 1 条可追溯资料依据，包含文件名、页码、片段和原始 PDF 页码入口 | 已验证：真实浏览器闭环返回可追溯资料依据，包含文件名、页码、片段、分数、命中原因和 PDF 页码入口 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`SCENARIO=minimal-loop make verify-e2e` 和 `make verify-db CHECK=source-lineage` 通过 | 通过 |
| 文档与行为一致 | 本地仓库；记录 `git status --short --branch`、`git rev-parse HEAD`、`make env-info` 输出 | 所有功能实现完成 | 对照 `docs/spec/v0.1.0/README.md` 和 `items/` 检查实现行为；执行 `make test` | 实际行为不超出或偏离 spec，未完成项未标记完成 | 已验证：v0.1.0 功能条目均已标记完成，验证矩阵引用真实命令证据；自动化测试通过 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make test` 通过 | 通过 |
| 审计与提交门禁 | Git 仓库、subagent 工具、GitHub 远端；记录 `git status --short --branch` 和 `git ls-remote --heads origin main` | 所有验证通过 | 派发 subagent 严格审计；审计通过后执行 `git add`、`git commit`、`git push`；推送完成后执行 `git ls-remote --heads origin main` | 审计结论通过，Git 远端包含发布提交；远端复核证据为推送后的 `git ls-remote` 命令输出，不写回同一个提交 | 已验证：v0.1.0 改动已完成 subagent 审计、提交、推送；远端 `main` 通过 `git ls-remote --heads origin main` 复核 | `docs/spec/v0.1.0/validation-2026-05-29.md`；推送后执行 `git ls-remote --heads origin main` | 通过 |

- 风险与回滚：若 embedding、数据库或服务启动无法在本机完成，必须标记阻塞并说明缺失条件，不得发布 v0.1.0。

# 核心数据模型

- 类型：数据与接口变更
- 状态：已完成
- 背景：v0.1.0 需要用最小数据模型串起项目、资料、页面、chunk、题目和匹配结果。
- 当前问题：没有稳定数据模型，处理链路和结果展示无法形成可追溯来源。
- 目标行为：系统具备最小数据对象，并保证每条资料依据能从题目追溯到资料文件、页码和原文片段。
- 非目标：不包含用户账号、权限、多租户、对象存储元数据、OCR bbox、复杂审计日志。
- 发布必要性：必须发布
- 用户可见影响：用户不会直接看到数据表，但会看到资料、题目和结果能稳定关联。
- 涉及模块：数据库、后端 API、处理链路、检索结果。
- 配置、接口或数据结构变化：新增 `projects`、`documents`、`document_pages`、`chunks`、`questions`、`question_matches`。
- 兼容性要求：无特殊要求。
- 验收标准：
  - `projects` 可以保存项目名称和创建时间。
  - `documents` 可以保存项目归属、文件名、类型、存储路径、页数和状态。
  - `document_pages` 可以保存资料页码和页面文本。
  - `chunks` 可以保存资料块文本、页码、section 标题和 embedding。
  - `questions` 可以保存项目归属和题目文本。
  - `question_matches` 可以保存题目、chunk、分数、排序、命中原因和来源片段。
  - 任何展示给用户的匹配结果都能追溯到 `document_id`、`page_no`、`chunk_id` 和 `source_text`。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 数据对象创建 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实后端；真实 PostgreSQL/pgvector；迁移命令可执行 | 已执行 `make reset-demo` | 执行 `make migrate`；执行 `make verify-db CHECK=schema-v0.1.0`，确认 `projects`、`documents`、`document_pages`、`chunks`、`questions`、`question_matches` | 所有 v0.1.0 必需数据对象存在 | 已验证：必需表、必需列和 pgvector extension 存在 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make verify-db CHECK=schema-v0.1.0` 通过 | 通过 |
| 来源链路追溯 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实后端；真实 PostgreSQL/pgvector；embedding provider、模型、维度和调用方式已固定并可用 | 已上传资料、完成索引并完成一次检索 | 执行 `make verify-db CHECK=source-lineage`，检查某条 `question_matches` 及关联的 `questions`、`chunks`、`document_pages`、`documents` 记录 | 可追溯到题目、chunk、资料、页码和来源片段 | 已验证：题目匹配可追溯到 question、chunk、document_page、document 和来源片段 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make verify-db CHECK=source-lineage` 通过 | 通过 |
| 缺少来源禁止展示 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector | 通过 `make verify-db CHECK=seed-match-missing-source` 构造缺失 `source_text` 或页码的数据 | 执行 `make dev`；执行 `make verify-e2e SCENARIO=missing-source-filter`；执行 `make verify-db CHECK=missing-source-not-visible` | 前端不展示该匹配结果 | 已验证：缺少来源字段的候选不从 API 返回，页面不展示 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make verify-e2e` 8 场景通过；`make verify-db CHECK=missing-source-not-visible` 通过 | 通过 |

- 风险与回滚：模型不应过早加入多用户和权限字段。若后续需要，应在独立版本 spec 中变更。

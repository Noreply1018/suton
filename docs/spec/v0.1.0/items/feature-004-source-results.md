# 资料依据结果展示

- 类型：功能新增
- 状态：已完成
- 背景：Suton 的核心体验是回答“这道题应该去资料哪里看”。结果展示必须克制，并以来源为中心。
- 当前问题：如果结果只给解释或只给相似文本，用户无法回到资料原文核验。
- 目标行为：系统返回前 5 条以内资料依据，前端展示文件名、页码、命中片段、pgvector 相似度分数、确定性命中原因和原始 PDF 页码入口。
- 非目标：不包含 AI 长篇讲解、答案生成、bbox 高亮、覆盖分析、引用完整性、知识图谱。
- 发布必要性：必须发布
- 用户可见影响：用户可以在结果区域看到可追溯的资料依据卡片，并打开原始 PDF 页码入口。
- 涉及模块：前端结果页或结果侧栏、后端检索 API、文件访问接口、数据库。
- 配置、接口或数据结构变化：新增或使用 `question_matches` 数据对象；结果 API 必须返回来源字段。
- 兼容性要求：无特殊要求。
- 验收标准：
  - 每条结果包含文件名、页码、命中片段、pgvector 相似度分数、确定性命中原因和原始 PDF 页码入口。
  - 结果数量最多展示 5 条。
  - 没有明确文件、页码或片段的结果不展示。
  - 原始 PDF 页码入口必须打开原始 PDF，并携带可核验页码。
  - 页面不展示长篇 AI 讲解和无来源答案。
  - 无匹配结果时展示空状态。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 展示资料依据 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector；embedding provider、模型、维度和调用方式已固定并可用 | 已完成 `tests/fixtures/text-layer-material.pdf` 索引，已输入固定样例题目 `tests/fixtures/question.txt` | 执行 `make dev`；执行 `make verify-db CHECK=question-matches-with-source`；执行 `make verify-e2e SCENARIO=source-results` | 展示 5 条以内结果，每条都有文件名、页码、片段、pgvector 相似度分数、确定性命中原因和原始 PDF 页码入口 | 已验证：页面展示来源结果，结果包含文件名、页码、片段、pgvector 相似度、命中原因和 PDF 页码入口 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`SCENARIO=minimal-loop make verify-e2e`、`make verify-db CHECK=question-matches-with-source` 通过 | 通过 |
| 无来源结果过滤 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector | 通过 `make verify-db CHECK=seed-match-missing-source` 构造缺少页码或片段的候选结果 | 执行 `make dev`；执行 `make verify-e2e SCENARIO=missing-source-filter` | 缺少来源字段的结果不展示 | 已验证：缺少来源字段的候选不从 API 返回，页面无该候选内容 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`missing-source-filter`、`missing-source-page` 场景通过 | 通过 |
| 空结果状态 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector；embedding provider、模型、维度和调用方式已固定并可用 | 已完成资料索引，准备明显无关题目 `tests/fixtures/unmatched-question.txt` | 执行 `make dev`；输入无关题目并检索；执行 `make verify-db CHECK=no-question-matches FILE=tests/fixtures/unmatched-question.txt`；执行 `make verify-e2e SCENARIO=empty-results` | 页面显示无匹配资料状态，不生成 AI 猜测 | 已验证：无关题目展示空结果，不生成无来源答案，数据库无匹配记录 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`empty-results` 场景和 `make verify-db CHECK=no-question-matches` 通过 | 通过 |

- 风险与回滚：覆盖分析、引用完整性和知识图谱容易误入本条目。若实现时出现这些需求，应移出 v0.1.0。

# 题目历史与检索体验

- 类型：功能新增
- 状态：草案
- 背景：真实复习不是一次性输入一道题，而是持续输入、回看和比较多道题的来源依据。
- 当前问题：题目输入和结果像一次性流程，缺少历史、重新检索、置信层级、空状态、无可靠来源状态和结果管理。
- 目标行为：用户可以查看题目历史，回看每道题最近一次检索的来源结果，重新检索，并在无可靠依据时得到清晰反馈。检索结果必须展示来源置信层级：`强相关`、`可参考`、`低置信`。无可靠来源时展示高级空状态和三个行动入口：扩大资料范围、检查资料索引、修改题目表述。检索过程必须简约高效，不展示无来源答案。重新检索会替换该题当前可见结果。
- 非目标：不包含错题本、学习计划、题目标签体系、自动切题、AI 答案生成。
- 发布必要性：必须发布
- 用户可见影响：用户可以持续使用 Suton 做多道题的资料溯源，并回到历史题目。
- 涉及模块：前端题目输入、题目历史、检索结果、后端题目 API、数据库、检索。
- 配置、接口或数据结构变化：题目记录必须支持历史查询、重新检索和关联最近一次来源结果。来源结果必须包含 `confidence_level` 字段，固定枚举为 `strong`、`reference`、`low`；该字段由后端基于 pgvector 相似度分数生成：`strong` 为 score >= 0.72，`reference` 为 0.55 <= score < 0.72，`low` 为 0.40 <= score < 0.55。score < 0.40 或没有结果时不得展示来源结果，必须进入无可靠来源状态。接口字段和错误码以 `data-001-v020-model-api.md` 为准。
- 兼容性要求：已有 v0.1.0 题目记录必须迁移为历史题目；若存在旧来源结果，则作为该题最近一次检索结果展示。
- 检索工作流契约：
  - 新题检索使用 `POST /projects/{project_id}/questions`；重新检索使用 `POST /questions/{question_id}/research`。
  - 题目文本 trim 后不能为空；空题目返回 HTTP 400，`detail` 固定为 `题目不能为空`。
  - 检索范围由 `document_ids` 指定；为 `null` 时使用当前项目全部 `completed` 且 `searchable = true` 的资料；为空数组时返回 HTTP 400，`detail` 固定为 `检索范围不能为空`。
  - 指定资料不属于当前项目、资料未完成或 `searchable = false` 时返回 HTTP 400，`detail` 固定为 `检索范围包含不可用资料`。
  - 当前项目没有可检索资料时返回 HTTP 409，`detail` 固定为 `需先上传并处理资料`。
  - 后端最多返回前 8 条 score >= 0.40 的来源结果；排序固定为 score 降序，score 相同按 chunk ID 升序。
  - 没有 score >= 0.40 的来源结果时，题目状态固定为 `no_reliable_source`，响应中 `matches` 为空数组。
  - 重新检索请求体固定为 `{ "document_ids": number[] | null }`，错误契约与新题检索一致；重新检索成功后，该题旧结果必须从当前可见结果中消失；若重新检索得到无可靠来源，历史题目仍保留，但显示无可靠来源状态。
  - 题目历史只展示题目文本、最近检索时间、状态、结果数量和最高置信层级；不在历史列表中展开长片段。
  - 前端不得显示 AI 生成答案、推测答案或与来源无关的讲解。
- 验收标准：
  - 用户可以输入新题目并检索。
  - 检索时展示明确 loading 状态。
  - 检索失败展示可理解错误。
  - 结果列表按 `强相关`、`可参考`、`低置信` 展示来源置信层级，视觉上使用轻量层级，不使用花哨标签。
  - 没有可靠来源时展示空状态，不展示猜测答案。
  - 无可靠来源空状态固定展示三个行动入口：扩大资料范围、检查资料索引、修改题目表述。
  - 题目历史可见，且不撑长页面。
  - 点击历史题目可回看最近一次检索结果。
  - 用户可以重新检索历史题目，重新检索后替换该题当前可见结果。
  - 检索范围筛选对新题检索和历史题重新检索都生效。
  - 历史列表中的长题目文本必须截断或换行处理，不得撑开布局。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 新题检索 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-question-search QUESTION=tests/fixtures/question.txt` | 返回带来源结果、置信层级和清晰 loading 状态 | 未验证 | 待补充 | 阻塞 |
| 无可靠来源 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已准备 `tests/fixtures/unmatched-question.txt` | 执行 `make verify-e2e SCENARIO=v020-question-no-source QUESTION=tests/fixtures/unmatched-question.txt` | 页面展示无可靠来源状态和三个行动入口，不展示猜测答案 | 未验证 | 待补充 | 阻塞 |
| 历史与重新检索 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已存在多道题目记录 | 执行 `make verify-e2e SCENARIO=v020-question-history-research` | 历史题目展示最近一次检索结果；重新检索后替换该题当前可见结果 | 未验证 | 待补充 | 阻塞 |
| 置信层级 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、Linux、Playwright 浏览器 | 验证脚本在真实 PostgreSQL/pgvector 中创建 1 个测试项目、1 份测试资料、3 个固定 1024 维向量 chunk 和 1 个固定查询向量，三条候选 score 分别落入 `strong`、`reference`、`low` 区间；该测试不调用 embedding provider | 执行 `make verify-e2e SCENARIO=v020-confidence-levels`；执行 `make verify-db CHECK=v020-confidence-levels` | 来源结果按固定向量 score 生成 `strong`、`reference`、`low`，前端展示强相关、可参考、低置信 | 未验证 | 待补充 | 阻塞 |
| 检索范围错误 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已存在当前项目和至少一份不可用或跨项目资料 | 执行 `make verify-e2e SCENARIO=v020-question-scope-errors`；执行 `make verify-api-contract CHECK=v020-question-scope-errors` | 空范围、跨项目资料、未完成资料和不可检索资料均返回固定错误，页面不产生伪结果 | 未验证 | 待补充 | 阻塞 |
| 长题目历史布局 | Node.js、pnpm、真实 Web、Linux、Playwright 浏览器、390px 和 1440px viewport | 已创建包含长题干的多道历史题目 | 执行 `make verify-e2e SCENARIO=v020-question-history-long-text`；执行 `make verify-visual CHECK=question-history-long-text` | 历史列表不撑开页面，不遮挡操作入口，长文本截断或换行符合布局 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：题目历史可能膨胀成错题本。v0.2.0 只保存和回看检索工作流，不做学习管理。

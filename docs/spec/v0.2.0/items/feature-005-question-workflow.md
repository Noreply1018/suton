# 题目历史与检索体验

- 类型：功能新增
- 状态：草案
- 背景：真实复习不是一次性输入一道题，而是持续输入、回看和比较多道题的来源依据。
- 当前问题：题目输入和结果像一次性流程，缺少历史、重新检索、空状态、无可靠来源状态和结果管理。
- 目标行为：用户可以查看题目历史，回看每道题最近一次检索的来源结果，重新检索，并在无可靠依据时得到清晰反馈。检索过程必须简约高效，不展示无来源答案。重新检索会替换该题当前可见结果。
- 非目标：不包含错题本、学习计划、题目标签体系、自动切题、AI 答案生成。
- 发布必要性：必须发布
- 用户可见影响：用户可以持续使用 Suton 做多道题的资料溯源，并回到历史题目。
- 涉及模块：前端题目输入、题目历史、检索结果、后端题目 API、数据库、检索。
- 配置、接口或数据结构变化：题目记录必须支持历史查询、重新检索和关联最近一次来源结果。
- 兼容性要求：已有 v0.1.0 题目记录必须迁移为历史题目；若存在旧来源结果，则作为该题最近一次检索结果展示。
- 验收标准：
  - 用户可以输入新题目并检索。
  - 检索时展示明确 loading 状态。
  - 检索失败展示可理解错误。
  - 没有可靠来源时展示空状态，不展示猜测答案。
  - 题目历史可见，且不撑长页面。
  - 点击历史题目可回看最近一次检索结果。
  - 用户可以重新检索历史题目，重新检索后替换该题当前可见结果。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 新题检索 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-question-search QUESTION=tests/fixtures/question.txt` | 返回带来源结果，loading 状态清晰 | 未验证 | 待补充 | 阻塞 |
| 无可靠来源 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已准备 `tests/fixtures/unmatched-question.txt` | 执行 `make verify-e2e SCENARIO=v020-question-no-source QUESTION=tests/fixtures/unmatched-question.txt` | 页面展示无可靠来源状态，不展示猜测答案 | 未验证 | 待补充 | 阻塞 |
| 历史与重新检索 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已存在多道题目记录 | 执行 `make verify-e2e SCENARIO=v020-question-history-research` | 历史题目展示最近一次检索结果；重新检索后替换该题当前可见结果 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：题目历史可能膨胀成错题本。v0.2.0 只保存和回看检索工作流，不做学习管理。

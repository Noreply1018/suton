# v0.1.0 验证门禁

- 类型：验证与发布门禁
- 状态：草案
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
  - 准备至少 1 份固定有文字层 PDF 作为测试资料。
  - 准备至少 1 道固定样例题目。
  - 清理旧上传、旧索引、旧数据库记录后执行验证。
  - 真实启动前端、后端和数据库。
  - 完成项目创建、资料上传、资料处理、题目输入、资料依据展示。
  - 至少 1 条结果可追溯到文件名、页码、原文片段和原页入口。
  - 所有 v0.1.0 条目验证矩阵结论为通过。
  - subagent 审计通过后才能提交发布相关改动。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 最小闭环验证 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector；本地文件系统；embedding provider 可用并记录模型和维度 | 已准备 `tests/fixtures/text-layer.pdf` 和 `tests/fixtures/question.txt`，已执行 `make reset-demo` | 执行 `make migrate`；执行 `make dev`；执行 `make process-demo FILE=tests/fixtures/text-layer.pdf`；执行 `make verify-e2e SCENARIO=minimal-loop QUESTION=tests/fixtures/question.txt`；执行 `make verify-db CHECK=source-lineage` | 返回至少 1 条可追溯资料依据，包含文件名、页码、片段和原页入口 | 待验证 | 待填写 | 阻塞 |
| 文档与行为一致 | 本地仓库；记录 `git status --short --branch`、`git rev-parse HEAD`、`make env-info` 输出 | 所有功能实现完成 | 对照 `docs/spec/v0.1.0/README.md` 和 `items/` 检查实现行为；执行 `make test` | 实际行为不超出或偏离 spec，未完成项未标记完成 | 待验证 | 待填写 | 阻塞 |
| 审计与提交门禁 | Git 仓库、subagent 工具、GitHub 远端；记录 `git status --short --branch` 和 `git ls-remote --heads origin main` | 所有验证通过 | 派发 subagent 严格审计；审计通过后执行 `git add`、`git commit`、`git push`；再执行 `git ls-remote --heads origin main` | 审计结论通过，Git 远端包含发布提交 | 待验证 | 待填写 | 阻塞 |

- 风险与回滚：若 embedding、数据库或服务启动无法在本机完成，必须标记阻塞并说明缺失条件，不得发布 v0.1.0。

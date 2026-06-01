# v0.2.0 总体验收门禁

- 类型：验证与发布门禁
- 状态：草案
- 背景：v0.2.0 同时涉及前端重构、数据语义、后台状态、资料管理和来源阅读，必须建立总体验收门禁。
- 当前问题：如果只验证单个功能，可能遗漏视觉质量、工作台布局、删除一致性、来源阅读和无来源保护。
- 目标行为：发布前完成真实 Web、真实后端、真实数据库、真实 Redis/RQ、真实文件系统、真实浏览器、视觉截图、人工审美审计和 subagent 严格审计。当前草案阶段的 `make verify-spec` 只要求覆盖 v0.2.0 文件结构、字段和核心约束；实现完成前不得把草案结构检查当作功能或视觉通过。
- 非目标：不包含生产环境压测、远端发布、GitHub Release、镜像发布；若后续决定发布镜像，必须单独补充发布门禁。
- 发布必要性：必须发布
- 用户可见影响：用户不会直接看到门禁，但门禁保证 v0.2.0 不是换皮原型。
- 涉及模块：前端、后端、数据库、Redis/RQ、文件存储、检索、PDF 阅读、测试、文档。
- 配置、接口或数据结构变化：无直接变化；本条目约束验证流程。
- 兼容性要求：不得降低 v0.1.0 已验证的来源约束和真实服务要求。
- 验收标准：
  - 所有 v0.2.0 条目完成。
  - `make env-info`、`make reset-demo`、`make migrate`、`make verify-e2e`、`make test` 通过。
  - 项目创建、重命名、删除和重名拦截通过。
  - 资料上传、删除、重新处理、详情展示和检索范围筛选通过。
  - 上传与处理进度可视化通过。
  - 题目历史、重新检索、无可靠来源状态通过。
  - 来源阅读与 PDF 详情视图通过。
  - 视觉截图矩阵和人工审美审计通过。
  - `make verify-spec` 和 `make verify-secrets` 通过；`make verify-spec` 同时覆盖 v0.1.0 release gate 和 v0.2.0 spec 结构检查。
  - 修改已追踪文件后完成 subagent 严格审计并提交。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 功能总回归 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、真实 Redis/RQ、真实文件系统、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已执行 `make reset-demo` 和 `make migrate`；固定 fixture 存在 | 执行 `make verify-e2e SCENARIO=v020-full-regression` | v0.2.0 核心工作流全部通过 | 未验证 | 待补充 | 阻塞 |
| 自动化测试 | Node.js、pnpm、Python、uv、Linux、本地开发环境 | 依赖安装完成，v0.2.0 的 `SCENARIO=v020-*`、`CHECK=v020-*` 和 `make verify-visual CHECK=*` 已实现为真实验证 | 执行 `make test`；执行 `make verify-spec`；执行 `make verify-secrets` | 测试和门禁均通过，且 `make verify-spec` 覆盖 v0.2.0 结构检查 | 未验证 | 待补充 | 阻塞 |
| 发布前审计 | Git 仓库、subagent 工具、Linux | 所有实现和验证完成 | 派发 subagent 严格审计；根据审计结果修复；执行 `git status --short --branch`；执行 `git commit` | 审计通过，工作区无未提交的已追踪改动 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：若任何真实服务、视觉审计或来源约束无法验证，v0.2.0 必须阻塞，不得以局部成功替代发布结论。

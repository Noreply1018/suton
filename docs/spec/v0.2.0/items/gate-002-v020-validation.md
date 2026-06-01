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
- 验证命令契约：
  - v0.2.0 实现期必须提供真实 `make verify-visual`、`make verify-api-contract` 和 `make verify-db` target；缺少任一 target 时发布门禁固定为阻塞。
  - `make verify-e2e SCENARIO=v020-full-regression` 必须串行覆盖项目管理、资料管理、上传处理、题目检索、来源阅读、无可靠来源、专注模式和 PDF 页码导航；任一子场景失败时该命令失败。
  - `make verify-api-contract CHECK=v020-model-api` 必须覆盖项目、资料、题目、来源详情和 PDF 文件接口的请求体、响应字段、HTTP 状态码和固定 `detail` 文案。
  - `make verify-db CHECK=v020-schema` 必须校验 v0.2.0 数据模型字段、枚举、唯一约束、外键、pgvector 维度和迁移后兼容字段；删除暂存目录契约由 `make verify-db CHECK=v020-delete-trash-cleanup` 覆盖。
  - `make verify-visual CHECK=screenshot-matrix`、`make verify-visual CHECK=visual-hard-errors`、`make verify-visual CHECK=visual-evidence-manifest` 和 `make verify-visual CHECK=aesthetic-audit-record` 必须全部通过；任一缺失或使用 mock 页面时发布门禁固定为阻塞。
  - `make test` 必须包含后端测试、前端 lint/typecheck 和已落地的 v0.2.0 自动化检查；不得用只执行 v0.1.0 测试的结果宣称 v0.2.0 通过。
  - `make verify-spec` 在草案阶段只证明 spec 结构有效；实现期发布前还必须确认所有 v0.2.0 验证矩阵行都有真实证据、实际结果和通过结论。
- 占位阻塞契约：
  - 当前仓库尚未实现的 `make verify-visual`、除 `v020-project-document-api`、`v020-document-detail-fields`、`v020-document-reprocess-api`、`v020-delete-api`、`v020-document-scope-disabled`、`v020-pdf-file-api`、`v020-project-name-limits`、`v020-question-scope-errors`、`v020-question-history-api`、`v020-question-detail-api`、`v020-question-research-scope-errors`、`v020-question-embedding-failure-api`、`v020-question-api`、`v020-stale-source` 和 `v020-model-api` 以外的 `make verify-api-contract CHECK=v020-*`、除 `v020-schema`、`v020-confidence-levels`、`v020-confidence-level-fields`、`v020-project-name-migration`、`v020-project-hard-delete`、`v020-document-hard-delete`、`v020-delete-consistency`、`v020-delete-trash-cleanup`、`v020-document-reprocess-no-duplicates`、`v020-document-health-fields`、`v020-document-health`、`v020-processing-failure-fields`、`v020-processing-embedding-failure-stage`、`v020-source-detail-fields`、`v020-question-research-consistency` 和 `v020-reprocess-research-consistency` 以外的 `make verify-db CHECK=v020-*`、除 `v020-first-empty-project`、`v020-project-create`、`v020-project-unique-name`、`v020-project-name-limits`、`v020-project-rename-delete`、`v020-project-delete-selection`、`v020-document-delete`、`v020-document-health` 和 `v020-document-detail-fields` 以外的 `make verify-e2e SCENARIO=v020-*` 不得被空 target、只打印文本、只检查文件存在、跳过真实服务或 dry-run 替代。
  - 若某个验证 target 尚未实现，对应验证矩阵行必须保持 `未验证 / 待补充 / 阻塞`；不得因为 `make verify-spec` 通过而改为通过。
  - 发布前必须生成 `tmp/v0.2.0-evidence-latest.md`；该文件必须列出每个必需命令、退出码、执行时间、Git commit、数据准备命令、证据路径和结论。
  - 证据文件不得包含 API key、token、password、Cookie、Authorization header 或真实用户隐私数据。
  - 远端仓库、tag、GitHub Release、镜像仓库和 CI 状态不属于本条目当前发布范围；若后续纳入，必须先新增对应 spec 和可追溯核验证据。
- 验收标准：
  - 所有 v0.2.0 条目完成。
  - `make env-info`、`make reset-demo`、`make migrate`、`make verify-e2e SCENARIO=v020-full-regression`、`make test` 通过。
  - 项目创建、重命名、删除和重名拦截通过。
  - 资料上传、删除、重新处理、详情展示和检索范围筛选通过。
  - 上传与处理进度可视化通过。
  - 题目历史、重新检索、无可靠来源状态通过。
  - 来源阅读与 PDF 详情视图通过。
  - 视觉截图矩阵和人工审美审计通过。
  - v0.2.0 API 契约、数据库契约、视觉门禁和总回归命令均为真实验证，不是占位脚本。
  - `tmp/v0.2.0-evidence-latest.md` 记录所有必需命令和证据路径，且不包含 secret。
  - `make verify-spec` 和 `make verify-secrets` 通过；`make verify-spec` 同时覆盖 v0.1.0 release gate 和 v0.2.0 spec 结构检查。
  - 修改已追踪文件后完成 subagent 严格审计并提交。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 功能总回归 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、真实 Redis/RQ、真实文件系统、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已执行 `make reset-demo` 和 `make migrate`；固定 fixture 存在 | 执行 `make verify-e2e SCENARIO=v020-full-regression` | v0.2.0 核心工作流全部通过 | 未验证 | 待补充 | 阻塞 |
| 自动化测试 | Node.js、pnpm、Python、uv、Linux、本地开发环境 | 依赖安装完成，v0.2.0 的 `SCENARIO=v020-*`、`CHECK=v020-*` 和 `make verify-visual CHECK=*` 已实现为真实验证 | 执行 `make test`；执行 `make verify-spec`；执行 `make verify-secrets` | 测试和门禁均通过，且 `make verify-spec` 覆盖 v0.2.0 结构检查 | 未验证 | 待补充 | 阻塞 |
| 验证 target 真实性 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、真实 Redis/RQ、Linux | v0.2.0 验证命令已实现 | 执行 `make verify-api-contract CHECK=v020-model-api`；执行 `make verify-db CHECK=v020-schema`；执行 `make verify-visual CHECK=screenshot-matrix`；执行 `make verify-visual CHECK=visual-hard-errors`；执行 `make verify-visual CHECK=visual-evidence-manifest`；执行 `make verify-visual CHECK=aesthetic-audit-record` | 所有 v0.2.0 API、数据库、视觉和审美检查为真实服务验证，且缺失 target 会失败 | 未验证 | 待补充 | 阻塞 |
| 证据归档 | Git 仓库、Linux、本地证据目录、secret 扫描工具 | 所有验证命令已执行完成 | 执行 `make evidence-package-with-tests`；执行 `make verify-secrets` | `tmp/v0.2.0-evidence-latest.md` 包含命令、退出码、执行时间、Git commit、数据准备命令、证据路径和结论，且不包含 secret | 未验证 | 待补充 | 阻塞 |
| 发布前审计 | Git 仓库、subagent 工具、Linux | 所有实现和验证完成 | 派发 subagent 严格审计；根据审计结果修复；执行 `git status --short --branch`；执行 `git commit` | 审计通过，工作区无未提交的已追踪改动 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：若任何真实服务、视觉审计或来源约束无法验证，v0.2.0 必须阻塞，不得以局部成功替代发布结论。

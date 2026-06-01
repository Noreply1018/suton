# v0.2.0 数据与接口约束

- 类型：数据与接口变更
- 状态：草案
- 背景：v0.2.0 增加项目重命名/删除、资料删除/重处理、资料健康度、处理进度、题目历史、来源置信层级和来源详情，需要固定数据与接口语义。
- 当前问题：如果接口语义不固定，前端重构会依赖临时行为，资料删除、重新处理和来源详情容易出现不一致。
- 目标行为：v0.2.0 固定项目、资料、处理状态、题目、来源置信层级和来源详情的数据语义。所有会影响删除、重处理、唯一性、资料健康度和来源展示的行为必须可验证。
- 非目标：不包含多用户租户模型、权限模型、对象存储模型、云同步模型。
- 发布必要性：必须发布
- 用户可见影响：用户操作项目、资料和题目时状态一致，不出现删除后仍可检索、重处理重复结果或历史结果打不开的混乱体验。
- 涉及模块：数据库、后端 API、后台任务、检索、前端数据访问。
- 配置、接口或数据结构变化：必须新增或调整项目唯一性、资料处理阶段、失败详情、资料健康度、资料删除/重处理、题目历史、来源置信层级、来源详情相关字段和接口。
- 兼容性要求：v0.1.0 数据必须迁移到 v0.2.0 结构；重名项目按项目 ID 升序保留第一条原名，其余项目追加 `（迁移 2）`、`（迁移 3）` 后缀；迁移前必须备份或可重建本地 demo 数据。
- 验收标准：
  - 项目名称唯一性有数据库唯一约束。
  - 项目删除采用硬删除，并覆盖关联资料、页面文本、chunk、embedding、题目、来源结果和上传文件。
  - 资料删除采用硬删除，并覆盖文件、页面文本、chunk、embedding 和结果可见性。
  - 重新处理资料不会产生重复有效 chunk。
  - 资料处理阶段可持久化。
  - 资料处理失败时必须持久化 `failed_stage`、`failure_reason` 和 `failure_code`；失败详情接口必须返回这三个字段，`failure_reason` 用于用户可读展示，`failure_code` 用于自动化验证和后续修复入口判断。
  - 资料健康度接口返回页数、可提取文字页数、文字层质量、chunk 数和可检索状态。
  - 来源结果接口返回 `confidence_level`，固定枚举为 `strong`、`reference`、`low`。
  - 来源详情接口返回完整来源字段：文件 ID、文件名、页码、chunk ID、原文片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因。
  - 无来源时接口返回空结果；来源失效时接口返回明确错误；两种场景均不返回伪来源。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 数据迁移 | Python、uv、真实 PostgreSQL、Linux、v0.1.0 样例数据 | 已准备 v0.1.0 数据库状态 | 执行 `make migrate`；执行 `make verify-db CHECK=v020-schema`；执行 `make verify-db CHECK=v020-project-name-migration` | 数据迁移成功，关键记录可读取 | 未验证 | 待补充 | 阻塞 |
| 删除一致性 | Python、uv、真实 PostgreSQL/pgvector、真实文件系统、Linux | 已存在项目、资料、chunk、题目和结果 | 执行 `make verify-db CHECK=v020-delete-consistency` | 删除后不存在可见失效来源或重复索引 | 未验证 | 待补充 | 阻塞 |
| 来源详情接口 | Python、uv、真实 FastAPI、真实 PostgreSQL、真实文件存储、Linux | 已处理 `tests/fixtures/text-layer-material.pdf` 并检索 `tests/fixtures/question.txt` | 执行 `make verify-db CHECK=v020-source-detail-fields` | 返回文件 ID、文件名、页码、chunk ID、片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因 | 未验证 | 待补充 | 阻塞 |
| 资料健康度与置信层级字段 | Python、uv、真实 FastAPI、真实 PostgreSQL/pgvector、Linux | 已处理 `tests/fixtures/text-layer-material.pdf`，并已生成来源结果 | 执行 `make verify-db CHECK=v020-document-health-fields`；执行 `make verify-db CHECK=v020-confidence-level-fields` | 资料接口返回健康度字段，来源结果接口返回合法 `confidence_level` | 未验证 | 待补充 | 阻塞 |
| 失败详情字段 | Python、uv、真实 FastAPI、真实 PostgreSQL、Linux | 已上传并处理失败 `tests/fixtures/broken.pdf` | 执行 `make verify-db CHECK=v020-processing-failure-fields` | 资料记录和失败详情接口返回 `failed_stage`、`failure_reason`、`failure_code` | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：数据语义一旦含糊会导致前端状态混乱。实现前必须先固定接口和迁移策略。

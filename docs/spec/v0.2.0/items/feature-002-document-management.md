# 资料管理完整化

- 类型：功能新增
- 状态：草案
- 背景：资料是 Suton 检索依据。真实复习中用户会上传多份 PDF，需要删除错误资料、重新处理失败资料、查看处理详情并筛选检索范围。
- 当前问题：PDF 不能删除，不能重新处理，资料列表会向下撑长页面，资料详情不足，检索范围不够可控。
- 目标行为：用户可以删除 PDF、重新处理 PDF、查看资料详情，并按资料文件筛选检索范围。资料列表必须固定在工作台区域内，不得撑长页面。资料删除采用硬删除：资料记录、页面文本、chunk、embedding、关联来源结果和上传文件一并删除；题目记录保留但不再展示该资料来源。
- 非目标：不包含非 PDF 文件上传、对象存储、批量重命名、资料文件夹、资料分享。
- 发布必要性：必须发布
- 用户可见影响：用户可以清理错误资料、修复失败处理，并控制题目检索在哪些资料中发生。
- 涉及模块：前端资料管理、后端资料 API、数据库、文件存储、后台任务、检索。
- 配置、接口或数据结构变化：资料接口必须支持删除、重新处理、详情查询和检索范围参数；数据库必须保存处理详情和最近处理时间。
- 兼容性要求：删除资料后不得继续在检索结果中展示该资料来源；重新处理必须在同一事务语义下废弃旧页面文本、chunk、embedding 和旧来源结果，再写入新处理结果，避免重复索引。
- 验收标准：
  - PDF 可以删除，删除前有确认。
  - 删除后资料列表、数据库、文件存储和检索结果保持一致。
  - 任一上传文件删除失败时资料删除失败，数据库不得留下半删除状态。
  - PDF 可以重新处理。
  - 重新处理后旧页面文本、chunk、embedding 和旧来源结果不再参与检索或展示。
  - 资料详情展示文件名、页数、chunk 数、处理状态、失败原因、最近处理时间。
  - 检索时可以选择全部资料或指定资料。
  - 资料列表不撑长页面。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 删除资料 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、本地文件系统、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-delete`；执行 `make verify-db CHECK=v020-document-hard-delete` | 资料删除成功，检索结果不再返回该资料 | 未验证 | 待补充 | 阻塞 |
| 重新处理 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 Redis/RQ、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-reprocess`；执行 `make verify-db CHECK=v020-document-reprocess-no-duplicates` | 旧索引被替换，不出现重复 chunk，旧来源结果不再展示 | 未验证 | 待补充 | 阻塞 |
| 检索范围筛选 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已上传两份资料且均完成索引，其中包含 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-scope-search` | 结果只来自选中的资料范围 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：资料删除和重新处理容易破坏来源一致性。若文件、数据库和向量索引不能一致更新，必须阻塞。

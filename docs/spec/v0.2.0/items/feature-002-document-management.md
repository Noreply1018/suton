# 资料管理完整化

- 类型：功能新增
- 状态：草案
- 背景：资料是 Suton 检索依据。真实复习中用户会上传多份 PDF，需要删除错误资料、重新处理失败资料、查看处理详情并筛选检索范围。
- 当前问题：PDF 不能删除，不能重新处理，资料列表会向下撑长页面，资料详情不足，检索范围不够可控，用户也无法判断一份资料是否适合检索。
- 目标行为：用户可以删除 PDF、重新处理 PDF、查看资料详情，并按资料文件筛选检索范围。资料列表必须固定在工作台区域内，不得撑长页面。每份资料必须展示资料健康度：页数、文字层质量、chunk 数和可检索状态。资料删除采用硬删除：资料记录、页面文本、chunk、embedding、关联来源结果和上传文件一并删除；题目记录保留但不再展示该资料来源。
- 非目标：不包含非 PDF 文件上传、对象存储、批量重命名、资料文件夹、资料分享。
- 发布必要性：必须发布
- 用户可见影响：用户可以清理错误资料、修复失败处理，判断资料是否可检索，并控制题目检索在哪些资料中发生。
- 涉及模块：前端资料管理、后端资料 API、数据库、文件存储、后台任务、检索。
- 配置、接口或数据结构变化：资料接口必须支持删除、重新处理、详情查询、资料健康度查询和检索范围参数；数据库必须保存处理详情、最近处理时间、页数、可提取文字页数、chunk 数和可检索状态。文字层质量按 `可提取文字页数 / 总页数` 计算，不做四舍五入：`良好` 为 ratio >= 0.90，`一般` 为 0.50 <= ratio < 0.90，`不足` 为 0 < ratio < 0.50，`不可检索` 为 ratio = 0。
- 兼容性要求：删除资料后不得继续在检索结果中展示该资料来源；重新处理必须在同一事务语义下废弃旧页面文本、chunk、embedding 和旧来源结果，再写入新处理结果，避免重复索引。
- 资料列表与详情契约：
  - 资料列表固定按 `created_at DESC, id DESC` 排序，显示在中间主工作区的资料区域内；超过区域高度时只滚动资料列表，不滚动整页。
  - 每份资料行固定展示文件名、处理状态、页数、文字层质量、chunk 数、可检索状态和最近处理时间；文件名超过一行时中间截断，保留扩展名。
  - 资料详情入口固定为点击资料行；详情层在桌面端显示在主工作区内，移动端显示为全屏详情层。
  - 资料详情字段固定为：文件名、内容类型、页数、可提取文字页数、文字层质量、chunk 数、可检索状态、处理状态、处理阶段、失败阶段、失败码、失败原因、创建时间、最近处理时间。
  - `text_quality` 计算使用 `extractable_page_count / page_count` 的原始小数值，不做百分比取整；`page_count = 0` 时固定为 `unsearchable`；`extractable_page_count` 不得大于 `page_count`。
  - `searchable = true` 仅当 `status = completed`、`chunk_count > 0` 且 `text_quality` 不是 `unsearchable`；其他状态固定为 `false`。
  - 扫描件 PDF 不进入 OCR；若 PyMuPDF 无可提取文字层，资料状态固定为 `unsupported`，`text_quality = unsearchable`，`searchable = false`，`failure_code = no_text_layer`，`failure_reason = PDF 无可提取文字层，v0.2.0 不进入 OCR`。
- 删除与重处理契约：
  - 资料删除必须使用 `data-001-v020-model-api.md` 定义的删除暂存区两阶段流程；删除成功后资料列表立即移除该资料。
  - 资料删除确认固定使用 `Dialog` 组件；标题为 `删除资料`，正文为 `将删除该 PDF、页面文本、索引和相关来源结果。题目记录会保留。`，危险确认按钮文案为 `删除资料`，取消按钮文案为 `取消`。
  - 删除资料只删除该资料关联的 `question_matches`，保留 `questions`；历史题目再次打开时不得展示已删除资料来源。
  - 重新处理不得删除、移动或覆盖原上传 PDF 文件；重新处理只替换该资料的页面文本、chunk、embedding 和关联来源结果。
  - 重新处理入口只在 `completed`、`failed`、`unsupported` 状态展示；`uploaded` 和 `processing` 状态不展示重新处理入口；绕过前端对 `uploaded` 或 `processing` 资料调用重处理接口时，后端按 `data-001-v020-model-api.md` 返回 HTTP 409 和 `资料正在处理`。
  - 重新处理提交成功后资料状态固定回到 `uploaded`，`processing_stage = uploaded`，并重新进入处理轨道；旧健康度字段在新处理完成前保留但界面必须标记为 `重新处理中`。
  - 资料删除和重新处理的 API 字段、错误状态与 `detail` 文案以 `data-001-v020-model-api.md` 为准。
- 检索范围契约：
  - 新题检索和历史题重新检索都必须使用同一套资料范围选择控件。
  - 检索范围控件固定为 `SegmentedControl` 加资料多选列表：两段文案固定为 `全部可检索资料` 和 `指定资料`；默认选中 `全部可检索资料`，请求体发送 `document_ids = null`。
  - 切换到 `指定资料` 时展示当前项目资料多选列表；资料行按 `created_at DESC, id DESC` 排序，行内固定展示文件名、`text_quality_label`、`chunk_count` 和可检索状态。
  - 指定资料模式下，用户只能勾选当前项目内 `searchable = true` 的资料；不可检索资料在选择器中显示为禁用行，并展示禁用原因，禁用原因固定按优先级取：`status != completed` 展示 `资料尚未完成处理`，`text_quality = unsearchable` 展示 `资料不可检索`，`chunk_count = 0` 展示 `暂无可检索片段`。
  - 指定资料模式下至少选择一份资料时，请求体发送所选资料 ID 数组，数组按资料行当前排序输出；未选择任何资料时提交按钮禁用。
  - 若绕过前端提交空数组，后端按 `data-001-v020-model-api.md` 返回 `检索范围不能为空`。
- 验收标准：
  - PDF 可以删除，删除前有确认。
  - 删除后资料列表、数据库、文件存储和检索结果保持一致。
  - 任一上传文件删除失败时资料删除失败，数据库不得留下半删除状态。
  - PDF 可以重新处理。
  - 重新处理后旧页面文本、chunk、embedding 和旧来源结果不再参与检索或展示。
  - 资料详情展示文件名、页数、文字层质量、chunk 数、可检索状态、处理状态、失败原因、最近处理时间。
  - 资料列表中每份资料以一行固定健康信息展示：`页数 · 文字层质量 · chunk 数 · 可检索状态`。
  - 检索范围控件以 `全部可检索资料` 和 `指定资料` 两段切换，默认范围为全部可检索资料，指定资料模式使用资料多选列表。
  - 不可检索资料不能被选入检索范围。
  - 资料列表不撑长页面。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 删除资料 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、本地文件系统、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-delete`；执行 `make verify-api-contract CHECK=v020-delete-api`；执行 `make verify-db CHECK=v020-document-hard-delete` | 资料删除成功，检索结果不再返回该资料 | 资料删除 API 响应、固定错误文案、文件删除和失败回滚已验证；DB 级联与题目保留检查已验证；E2E 已验证删除确认固定文案、资料列表移除、题目记录保留且题目详情不再返回该资料来源 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_project_counts.py`、`backend/app/main.py`、`scripts/verify_api_contract.py`、`scripts/verify_db.py`、本地命令输出 | 通过 |
| 重新处理 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 Redis/RQ、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-reprocess`；执行 `make verify-api-contract CHECK=v020-document-reprocess-api`；执行 `make verify-db CHECK=v020-document-reprocess-no-duplicates`；执行 `make verify-db CHECK=v020-reprocess-research-consistency` | 旧索引被替换，不出现重复 chunk，旧来源结果不再展示 | API/DB 重置检查已验证错误契约、成功响应、旧页面/chunk/来源清理、原 PDF 保留、题目保留，并已与题目重新检索一致性串行聚合验证；前端资料详情已验证 `completed`、`failed`、`unsupported` 三态展示重新处理入口，`processing` 状态不展示；`make verify-e2e SCENARIO=v020-document-reprocess` 已在有效 DashScope 凭据环境中通过，覆盖已完成资料点击重新处理、状态回到 `uploaded`、界面标记 `重新处理中`、Redis/RQ worker 再次处理完成、失败字段清空、可检索和 chunk 持久化 | `backend/app/main.py`、`backend/app/processing.py`、`scripts/verify_api_contract.py`、`scripts/verify_db.py`、`frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、本地命令输出 | 通过 |
| 检索范围筛选 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL/pgvector、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已上传两份资料且均完成索引，其中包含 `tests/fixtures/text-layer-material.pdf` 和 `tests/fixtures/question-source.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-scope-search` | 结果只来自选中的资料范围 | `make verify-e2e SCENARIO=v020-document-scope-search` 已在有效 DashScope 凭据环境中通过，覆盖真实 UI 创建项目、上传两份固定 PDF、等待 worker 完成索引、切换到指定资料、只勾选 `question-source.pdf`、提交固定题目、断言请求体 `document_ids` 只包含选中资料且响应所有来源均来自选中资料 | `frontend/e2e/v010.spec.ts`、本地命令输出 | 通过 |
| 资料健康度 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已上传并处理 `tests/fixtures/text-layer-material.pdf` 和 `tests/fixtures/scanned.pdf` | 执行 `make verify-e2e SCENARIO=v020-document-health`；执行 `make verify-db CHECK=v020-document-health` | 资料列表和详情展示页数、文字层质量、chunk 数和可检索状态，扫描件显示不可检索或失败原因 | DB 健康度字段检查已验证；E2E 已验证完成、失败和 scanned/unsupported 资料在列表展示页数、文字层质量、chunk 数、可检索状态和失败原因 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_document_details.py`、`backend/app/processing.py`、`scripts/verify_db.py`、本地命令输出 | 通过 |
| 资料详情字段 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已上传并处理完成、失败、unsupported 三类资料 | 执行 `make verify-e2e SCENARIO=v020-document-detail-fields`；执行 `make verify-api-contract CHECK=v020-document-detail-fields` | 详情展示固定字段；API 不返回 `storage_path`；失败和 unsupported 资料展示固定失败码与原因 | API 契约已验证；E2E 已验证资料详情展示文件名、内容类型、页数、可提取文字页数、文字层质量、chunk 数、可检索状态、处理状态、处理阶段、失败阶段、失败码、失败原因、创建时间和最近处理时间 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_document_details.py`、`scripts/verify_api_contract.py`、本地命令输出 | 通过 |
| 不可检索资料范围 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 当前项目存在 `searchable = false` 的资料和至少一份可检索资料 | 执行 `make verify-e2e SCENARIO=v020-document-scope-disabled`；执行 `make verify-api-contract CHECK=v020-document-scope-disabled` | 不可检索资料在选择器中禁用；后端拒绝把不可检索资料作为检索范围 | API 契约已验证；E2E 已验证默认全部可检索资料、指定资料多选、不可检索资料禁用原因和未选择时提交禁用 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`backend/app/main.py`、`scripts/verify_api_contract.py`、本地命令输出 | 通过 |

- 风险与回滚：资料删除和重新处理容易破坏来源一致性。若文件、数据库和向量索引不能一致更新，必须阻塞。

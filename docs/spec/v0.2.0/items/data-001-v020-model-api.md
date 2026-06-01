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
- 兼容性要求：v0.1.0 数据必须迁移到 v0.2.0 结构；项目名迁移按项目 ID 升序逐条处理：`trim` 固定为 Python `str.strip()`；`base` 固定为对原名执行 `str.strip()` 后，若为空则替换为 `迁移项目 {id}`，再按 Python `str` Unicode code point 截断到前 80 个字符得到的字符串；若 `base` 已存在，则从 `n = 2` 开始生成后缀 `（迁移 {n}）`，候选名固定为 `base[:80 - len(suffix)] + suffix`，取第一个未被占用的候选名；`len` 固定为 Python `str` 的 Unicode code point 长度；迁移前必须备份或可重建本地 demo 数据。
- 数据模型契约：
  - `workspaces` 不在 v0.2.0 新增；单用户工作区固定为字符串常量 `local-default`，所有唯一性以该默认工作区为边界。
  - `projects` 必须包含 `id`、`workspace_id`、`name`、`created_at`、`updated_at`；`workspace_id` 固定写入 `local-default`；数据库必须建立 `(workspace_id, name)` 唯一约束。
  - `projects.name` 保存 trim 后名称，长度固定为 1 至 80 个字符；超过 80 个字符时后端不得截断用户输入，必须返回固定错误。
  - `documents` 必须包含 `id`、`project_id`、`filename`、`content_type`、`storage_path`、`page_count`、`extractable_page_count`、`chunk_count`、`text_quality`、`searchable`、`status`、`processing_stage`、`failed_stage`、`failure_code`、`failure_reason`、`created_at`、`processed_at`、`updated_at`。
  - `documents.status` 固定枚举为 `uploaded`、`processing`、`completed`、`failed`、`unsupported`、`deleting`；`documents.processing_stage` 固定枚举为 `uploaded`、`extracting_text`、`chunking`、`embedding`、`indexing`、`completed`、`failed`。
  - `documents.failed_stage` 在失败时等于失败发生前正在执行的非终态阶段，只能是 `uploaded`、`extracting_text`、`chunking`、`embedding`、`indexing`；未失败时为 `NULL`。
  - `documents.failure_code` 固定枚举为 `invalid_pdf`、`unsupported_file_type`、`no_text_layer`、`extract_text_failed`、`chunking_failed`、`embedding_failed`、`indexing_failed`、`storage_missing`、`delete_file_failed`、`unknown_processing_error`；未失败时为 `NULL`。
  - `documents.failure_reason` 必须按 `failure_code` 固定映射：`invalid_pdf` 为 `PDF 文件损坏，无法读取`；`unsupported_file_type` 为 `文件类型不受支持`；`no_text_layer` 为 `PDF 无可提取文字层，v0.2.0 不进入 OCR`；`extract_text_failed` 为 `提取文字失败`；`chunking_failed` 为 `切块失败`；`embedding_failed` 为 `生成 embedding 失败`；`indexing_failed` 为 `建立索引失败`；`storage_missing` 为 `资料文件不存在`；`delete_file_failed` 为 `资料文件删除失败`；`unknown_processing_error` 为 `资料处理失败`。
  - `documents.text_quality` 固定枚举为 `good`、`fair`、`poor`、`unsearchable`，展示文案分别为 `良好`、`一般`、`不足`、`不可检索`。
  - `document_pages` 必须包含 `id`、`document_id`、`page_no`、`raw_text`、`normalized_text`、`char_count`、`created_at`；`page_no` 从 1 开始；同一资料内 `(document_id, page_no)` 必须唯一。
  - `document_pages.normalized_text` 必须等于对 `raw_text` 执行正则替换 `re.sub(r"[ \t]+", " ", raw_text).strip()` 后的结果；`char_count` 必须等于 `len(normalized_text)`。
  - `chunks` 必须包含 `id`、`document_id`、`page_id`、`page_no`、`text`、`page_start_char`、`page_end_char`、`embedding`、`embedding_provider`、`embedding_model`、`embedding_dimension`、`embedding_call`、`created_at`；`page_start_char` 和 `page_end_char` 是 chunk 在规范化页文本中的半开区间 `[start, end)`。
  - `questions` 必须包含 `id`、`project_id`、`text`、`status`、`failure_code`、`failure_reason`、`last_search_at`、`created_at`、`updated_at`；`status` 固定枚举为 `searching`、`completed`、`no_reliable_source`、`failed`；`failure_code` 固定枚举为 `embedding_failed`、`source_context_failed`、`search_failed`。
  - `questions.failure_reason` 必须按 `failure_code` 固定映射：`embedding_failed` 为 `题目向量生成失败`；`source_context_failed` 为 `来源上下文生成失败`；`search_failed` 为 `题目检索失败`；未失败时 `failure_code` 和 `failure_reason` 均为 `NULL`。
  - `question_matches` 必须包含 `id`、`question_id`、`chunk_id`、`document_id`、`page_no`、`score`、`rank`、`confidence_level`、`hit_reason`、`source_text`、`context_before`、`context_after`、`created_at`。
  - `question_matches.confidence_level` 固定枚举为 `strong`、`reference`、`low`；展示文案分别为 `强相关`、`可参考`、`低置信`。
  - `question_matches.source_text` 固定保存完整命中 chunk 文本，写入前执行 trim，不截断、不摘要、不改写。
  - 结果上下文固定由命中 chunk 所在页的 `document_pages.normalized_text` 和 chunk offset 生成；保留换行，不合并段落。
  - chunk 写入时必须同时写入 `page_start_char` 和 `page_end_char`。`context_before` 为规范化页文本中 `page_start_char` 前最多 300 个字符，`context_after` 为 `page_end_char` 后最多 300 个字符；不足 300 个字符时返回实际剩余文本，不跨页、不跨文件生成上下文。
  - 若 `page_start_char`、`page_end_char` 越界，或规范化页文本的 `[page_start_char, page_end_char)` 片段与 `chunks.text` 不一致，本次题目检索必须失败：`questions.status` 写入 `failed`，`questions.failure_code` 写入 `source_context_failed`，`questions.failure_reason` 写入 `来源上下文生成失败`，且不得写入该题任何 `question_matches`。
- 接口契约：
  - 项目对象字段固定为 `id`、`workspace_id`、`name`、`document_count`、`question_count`、`latest_status`、`created_at`、`updated_at`；`document_count` 为当前项目未硬删除资料总数，覆盖 `uploaded`、`processing`、`completed`、`failed`、`unsupported`、`deleting`；`question_count` 为当前项目未硬删除题目总数，覆盖 `searching`、`completed`、`no_reliable_source`、`failed`。
  - `latest_status` 固定枚举为 `empty`、`processing`、`failed`、`ready`，计算优先级固定为：无资料时 `empty`，存在 `uploaded`、`processing` 或 `deleting` 资料时 `processing`，存在 `failed` 或 `unsupported` 资料且不存在处理中或删除中资料时 `failed`，其余为 `ready`。
  - `projects.updated_at` 在项目创建、重命名、上传资料、删除资料、重新处理资料、新题检索和重新检索成功返回题目详情对象时更新为当前数据库时间；只读查询不得更新。
  - 资料对象字段固定为 `id`、`project_id`、`filename`、`content_type`、`page_count`、`extractable_page_count`、`chunk_count`、`text_quality`、`text_quality_label`、`searchable`、`status`、`processing_stage`、`failed_stage`、`failure_code`、`failure_reason`、`created_at`、`processed_at`、`updated_at`；`text_quality_label` 必须由后端按 `text_quality` 映射生成：`good` 为 `良好`，`fair` 为 `一般`，`poor` 为 `不足`，`unsearchable` 为 `不可检索`；接口不得返回 `storage_path`。
  - `GET /projects` 返回项目对象数组，按 `updated_at DESC, id DESC` 排序。
  - `POST /projects` 请求体为 `{ "name": string }`；名称 trim 后为空返回 HTTP 400，`detail` 固定为 `项目名称不能为空`；名称超过 80 个字符返回 HTTP 400，`detail` 固定为 `项目名称不能超过 80 个字符`；成功返回项目对象；重名返回 HTTP 409，`detail` 固定为 `项目名称已存在`。
  - `PATCH /projects/{project_id}` 请求体为 `{ "name": string }`；名称 trim 后与原名完全一致时返回当前项目对象且不更新时间戳；空名返回 HTTP 400，`detail` 固定为 `项目名称不能为空`；名称超过 80 个字符返回 HTTP 400，`detail` 固定为 `项目名称不能超过 80 个字符`；项目不存在返回 HTTP 404，`detail` 固定为 `项目不存在`；重名返回 HTTP 409，`detail` 固定为 `项目名称已存在`。
  - `DELETE /projects/{project_id}` 执行硬删除；成功返回 `{ "deleted": true, "project_id": number }`；项目不存在返回 HTTP 404，`detail` 固定为 `项目不存在`；任一上传文件进入删除暂存区失败时返回 HTTP 500，`detail` 固定为 `项目文件删除失败`，数据库事务必须回滚。
  - `GET /projects/{project_id}/documents` 返回资料对象数组，按 `created_at DESC, id DESC` 排序；项目不存在返回 HTTP 404，`detail` 固定为 `项目不存在`。
  - `GET /documents/{document_id}` 返回资料对象；资料不存在返回 HTTP 404，`detail` 固定为 `资料不存在`。
  - `POST /projects/{project_id}/documents` 仅接受 PDF；项目不存在返回 HTTP 404，`detail` 固定为 `项目不存在`；非 PDF 返回 HTTP 400，`detail` 固定为 `v0.2.0 只支持上传 PDF 文件`；空文件返回 HTTP 400，`detail` 固定为 `上传文件不能为空`；文件写入本地存储失败返回 HTTP 500，`detail` 固定为 `资料文件保存失败`；成功后返回资料对象，`status` 为 `uploaded`，`processing_stage` 为 `uploaded`。
  - `POST /documents/{document_id}/reprocess` 清除该资料旧页面文本、chunk、embedding 和关联来源结果后重新排队处理；资料不存在返回 HTTP 404，`detail` 固定为 `资料不存在`；资料文件不存在返回 HTTP 404，`detail` 固定为 `资料文件不存在`；资料状态为 `uploaded` 或 `processing` 时返回 HTTP 409，`detail` 固定为 `资料正在处理`；重新排队失败返回 HTTP 500，`detail` 固定为 `资料重新处理排队失败`；成功返回资料对象，`status` 为 `uploaded`，`processing_stage` 为 `uploaded`。
  - `DELETE /documents/{document_id}` 执行硬删除；成功返回 `{ "deleted": true, "document_id": number }`；资料不存在返回 HTTP 404，`detail` 固定为 `资料不存在`；上传文件进入删除暂存区失败时返回 HTTP 500，`detail` 固定为 `资料文件删除失败`，数据库事务必须回滚。
  - `POST /projects/{project_id}/questions` 请求体为 `{ "text": string, "document_ids": number[] | null }`；项目不存在返回 HTTP 404，`detail` 固定为 `项目不存在`；题目文本 trim 后为空返回 HTTP 400，`detail` 固定为 `题目不能为空`；`document_ids` 为 `null` 表示全部已完成且可检索资料；空数组返回 HTTP 400，`detail` 固定为 `检索范围不能为空`；指定资料跨项目、未完成或不可检索时返回 HTTP 400，`detail` 固定为 `检索范围包含不可用资料`；当前项目没有可检索资料时返回 HTTP 409，`detail` 固定为 `需先上传并处理资料`；请求校验通过后返回 HTTP 200 题目详情对象，包括 `completed`、`no_reliable_source` 和 `failed` 三种检索完成状态。
  - 题目详情对象字段固定为 `id`、`project_id`、`text`、`status`、`failure_code`、`failure_reason`、`last_search_at`、`created_at`、`updated_at`、`matches`；`matches` 数组项字段固定为 `id`、`question_id`、`document_id`、`document_filename`、`page_no`、`chunk_id`、`score`、`rank`、`confidence_level`、`confidence_label`、`hit_reason`、`source_text`、`context_before`、`context_after`、`pdf_url`。
  - `GET /projects/{project_id}/questions` 返回题目历史，按 `last_search_at DESC, id DESC` 排序；数组项字段固定为 `id`、`project_id`、`text`、`status`、`failure_code`、`failure_reason`、`last_search_at`、`updated_at`、`match_count`、`top_confidence_level`、`top_confidence_label`；项目不存在返回 HTTP 404，`detail` 固定为 `项目不存在`。
  - `POST /questions/{question_id}/research` 请求体为 `{ "document_ids": number[] | null }`；`document_ids` 为 `null` 表示当前项目全部已完成且可检索资料；空数组返回 HTTP 400，`detail` 固定为 `检索范围不能为空`；题目不存在返回 HTTP 404，`detail` 固定为 `题目不存在`；资料跨项目、未完成或不可检索时返回 HTTP 400，`detail` 固定为 `检索范围包含不可用资料`；请求校验通过后在同一事务内删除该题旧 `question_matches`、写入新结果、更新 `questions.status` 和 `last_search_at`，并返回 HTTP 200 题目详情对象，包括 `completed`、`no_reliable_source` 和 `failed` 三种检索完成状态。
  - `GET /questions/{question_id}` 返回题目详情对象；题目不存在返回 HTTP 404，`detail` 固定为 `题目不存在`；score < 0.40 的候选不得返回。
  - `GET /questions/{question_id}/matches/{match_id}` 返回来源详情；资料或 chunk 已删除时返回 HTTP 404，`detail` 固定为 `来源已失效`。
  - `GET /documents/{document_id}/file` 返回 PDF 文件；文件缺失时返回 HTTP 404，`detail` 固定为 `资料文件不存在`。
- 删除事务与一致性规则：
  - 上传文件删除采用固定两阶段流程，不允许实现为“先删数据库后删文件”或“先删文件后删数据库”的单阶段流程。
  - 删除开始时在 `UPLOAD_DIR/.delete-trash/{operation_id}/` 下创建删除暂存目录；`operation_id` 固定为 `{object_type}-{object_id}-{txid}`，`object_type` 只能是 `project` 或 `document`，`object_id` 为十进制 ID，`txid` 为 PostgreSQL `txid_current()` 返回值；该值只包含 ASCII 小写字母、数字和连字符。
  - 数据库事务开始后，后端以 `FOR UPDATE` 锁定待删除项目或资料及其资料记录，收集所有 `storage_path`；每个文件必须位于 `UPLOAD_DIR` 内。
  - 在同一数据库事务内，后端先把每个待删除文件用原子 rename 移动到删除暂存目录；任一文件不存在、越界、rename 失败或暂存目录创建失败时，必须把已移动文件按原路径移回，回滚数据库事务，并返回固定删除失败 `detail`。
  - 所有文件进入删除暂存目录后，后端删除数据库记录并提交事务；提交成功后递归删除该 `operation_id` 暂存目录。
  - 数据库提交失败时，后端必须把暂存目录内文件移回原路径并回滚事务；移回失败时记录后端错误日志，接口仍返回 HTTP 500，`detail` 为对应固定删除失败文案，验证必须能发现该错误。
  - 事务提交成功但暂存目录最终清理失败时，不回滚数据库；后端必须保留暂存目录并记录日志，后续 `make verify-db CHECK=v020-delete-trash-cleanup` 必须能发现并清理该残留。
  - 项目硬删除和资料硬删除必须在数据库事务内删除相关记录；文件进入删除暂存目录是数据库删除前的必经步骤。文件进入暂存目录失败时，数据库不得提交半删除状态。
  - 资料重处理不得移动、删除或替换原上传 PDF 文件；重处理必须在数据库事务内删除旧 `document_pages`、`chunks` 和该资料关联的 `question_matches`，再创建新的处理任务；旧 `questions` 保留。
  - 重新检索题目必须先删除该题旧 `question_matches`，再写入新结果；检索失败时题目状态为 `failed`，旧结果不得继续作为当前结果展示。
  - 来源结果只允许引用当前仍存在、状态为 `completed` 且 `searchable = true` 的资料。
- 验收标准：
  - 项目名称唯一性有数据库唯一约束。
  - 项目删除采用硬删除，并覆盖关联资料、页面文本、chunk、embedding、题目、来源结果和上传文件。
  - 资料删除采用硬删除，并覆盖文件、页面文本、chunk、embedding 和结果可见性。
  - 重新处理资料不会产生重复有效 chunk。
  - 资料处理阶段可持久化。
  - 资料处理失败时必须持久化 `failed_stage`、`failure_reason` 和 `failure_code`；失败详情接口必须返回这三个字段，`failure_reason` 用于用户可读展示，`failure_code` 用于自动化验证和后续修复入口判断。
  - 资料健康度接口返回页数、可提取文字页数、文字层质量、chunk 数和可检索状态。
  - 项目列表和资料列表接口返回字段、排序和 `latest_status`、`text_quality_label` 文案符合本条目接口契约。
  - 来源结果接口返回 `confidence_level`，固定枚举为 `strong`、`reference`、`low`。
  - 来源详情接口返回完整来源字段：文件 ID、文件名、页码、chunk ID、原文片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因。
  - 无来源时接口返回空结果；来源失效时接口返回明确错误；两种场景均不返回伪来源。
  - 所有新增和调整接口遵守本条目接口契约，错误状态返回固定 HTTP 状态码和固定 `detail` 文案。
  - 题目详情、题目历史和重新检索接口返回字段与 `feature-005-question-workflow.md` 完全一致。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 数据迁移 | Python、uv、真实 PostgreSQL、Linux、v0.1.0 样例数据 | 已准备 v0.1.0 数据库状态 | 执行 `make migrate`；执行 `make verify-db CHECK=v020-schema`；执行 `make verify-db CHECK=v020-project-name-migration` | 数据迁移成功，关键记录可读取 | schema 与项目名称迁移 DB 检查已验证，完整 v0.1.0 样例迁移未验证 | `scripts/migrate.py`、`scripts/verify_db.py`、本地命令输出 | 阻塞 |
| 删除一致性 | Python、uv、真实 PostgreSQL/pgvector、真实文件系统、Linux | 已存在项目、资料、chunk、题目和结果 | 执行 `make verify-db CHECK=v020-delete-consistency` | 删除后不存在可见失效来源或重复索引 | 未验证 | 待补充 | 阻塞 |
| 来源详情接口 | Python、uv、真实 FastAPI、真实 PostgreSQL、真实文件存储、Linux | 已处理 `tests/fixtures/text-layer-material.pdf` 并检索 `tests/fixtures/question.txt` | 执行 `make verify-db CHECK=v020-source-detail-fields` | 返回文件 ID、文件名、页码、chunk ID、片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因 | API/DB 字段检查已验证，来源阅读 E2E 未验证 | `backend/app/main.py`、`scripts/verify_db.py`、本地命令输出 | 阻塞 |
| 资料健康度与置信层级字段 | Python、uv、真实 FastAPI、真实 PostgreSQL/pgvector、Linux | 已处理 `tests/fixtures/text-layer-material.pdf`，并已生成来源结果 | 执行 `make verify-db CHECK=v020-document-health-fields`；执行 `make verify-db CHECK=v020-confidence-level-fields` | 资料接口返回健康度字段，来源结果接口返回合法 `confidence_level` | 资料健康度字段和置信层级接口字段 DB/API 检查已验证，完整题目接口未验证 | `backend/app/main.py`、`backend/app/processing.py`、`scripts/verify_db.py`、本地命令输出 | 阻塞 |
| 失败详情字段 | Python、uv、真实 FastAPI、真实 PostgreSQL、Linux | 已上传并处理失败 `tests/fixtures/broken.pdf` | 执行 `make verify-db CHECK=v020-processing-failure-fields` | 资料记录和失败详情接口返回 `failed_stage`、`failure_reason`、`failure_code` | 未验证 | 待补充 | 阻塞 |
| 接口契约 | Python、uv、真实 FastAPI、真实 PostgreSQL、本地文件系统、Linux | 已执行 `make migrate` 并准备项目、资料和题目样例 | 执行 `make verify-api-contract CHECK=v020-model-api` | 所有 v0.2.0 项目、资料、题目和来源接口字段、HTTP 状态码、固定错误文案符合 spec | 未验证 | 待补充 | 阻塞 |
| 重处理与重新检索一致性 | Python、uv、真实 FastAPI、真实 PostgreSQL/pgvector、真实 Redis/RQ、Linux | 已处理资料并保存题目来源结果 | 执行 `make verify-db CHECK=v020-reprocess-research-consistency` | 资料重处理删除旧索引和旧来源；题目重新检索替换当前结果；旧题目记录保留 | 未验证 | 待补充 | 阻塞 |
| 删除暂存清理 | Python、uv、真实 FastAPI、真实 PostgreSQL、本地文件系统、Linux | 已执行项目删除和资料删除场景 | 执行 `make verify-db CHECK=v020-delete-trash-cleanup` | 已提交删除不残留可恢复来源；删除暂存目录为空或只包含可追踪失败日志记录 | 未验证 | 待补充 | 阻塞 |
| 题目接口字段 | Python、uv、真实 FastAPI、真实 PostgreSQL/pgvector、Linux | 已准备题目检索、重新检索、无可靠来源和失败样例 | 执行 `make verify-api-contract CHECK=v020-question-api` | 题目详情、历史列表、重新检索响应、失败字段、置信文案和无可靠来源状态符合 spec | 未验证 | 待补充 | 阻塞 |
| 项目与资料响应字段 | Python、uv、真实 FastAPI、真实 PostgreSQL、Linux | 已准备空项目、处理中资料、失败资料和已完成资料 | 执行 `make migrate`；执行 `make verify-api-contract CHECK=v020-project-document-api` | 项目对象、资料对象、排序、`latest_status`、`text_quality_label`、`updated_at` 更新语义和 `storage_path` 隐藏规则符合 spec | 已验证通过 | `backend/app/main.py`、`scripts/verify_api_contract.py`、本地命令输出 | 通过 |

- 风险与回滚：数据语义一旦含糊会导致前端状态混乱。实现前必须先固定接口和迁移策略。

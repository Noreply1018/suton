# 来源阅读与 PDF 详情视图

- 类型：功能新增
- 状态：草案
- 背景：Suton 的核心价值是从题目定位到资料依据。v0.1.0 只在结果列表中展示片段，用户难以深入阅读命中页和上下文。
- 当前问题：检索结果只能在右侧小区域查看，无法详细打开命中的页面和段落，阅读体验不足。
- 目标行为：用户点击来源结果后进入来源阅读视图。该视图必须展示 PDF 目标页、命中段落、上下文、文件名、页码和命中原因。PDF 阅读必须成为一等体验，而不是列表里的小片段。PDF 阅读视图必须提供极简页码导航：突出当前命中页，支持上一页、下一页和回到命中页。
- 非目标：不包含 bbox 高亮、公式结构理解、表格结构理解、PDF 编辑、批注同步。
- 发布必要性：必须发布
- 用户可见影响：用户可以从题目结果直接打开对应 PDF 页，并围绕命中段落继续阅读。
- 涉及模块：前端来源结果、PDF 阅读视图、后端文件访问接口、资料片段接口、数据库。
- 配置、接口或数据结构变化：来源结果详情接口必须返回文件 ID、文件名、页码、chunk ID、原文片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因。字段名、错误码和失效来源行为以 `data-001-v020-model-api.md` 的接口契约为准。
- 兼容性要求：无来源结果不得进入阅读视图；被删除资料的旧结果不得打开为有效来源。
- 来源详情契约：
  - 入口固定为点击来源结果行，不新增独立路由作为唯一入口；浏览器 URL 不随来源切换变化，页面可用性不得依赖用户手写 URL。
  - 桌面端来源阅读区固定在工作台右侧；专注模式下阅读区扩大，但仍保留当前题目和来源结果列表。
  - 移动端点击来源结果后打开全屏详情层；详情层顶部必须提供返回当前题目的入口。
  - 来源结果列表中当前打开的来源行必须标记为选中状态；用户点击另一条来源结果时，同一阅读区原地替换 PDF 页、命中段落、上下文和来源元信息，不重置当前题目和检索范围。
  - PDF 页入口固定使用 `GET /documents/{document_id}/file#page={page_no}` 形式；`page_no` 从 1 开始。
  - 来源详情响应必须包含 `document_id`、`filename`、`page_no`、`chunk_id`、`source_text`、`context_before`、`context_after`、`pdf_url`、`score`、`rank`、`confidence_level`、`hit_reason`。
  - 前端打开来源详情时必须具备该资料的 `page_count`；若当前状态未缓存资料对象，必须调用 `GET /documents/{document_id}` 取得 `page_count`，不得用固定页数或未知总页数替代。
  - `source_text` 必须为完整命中 chunk 文本，trim 后返回，不截断、不摘要、不由 AI 改写。
  - `context_before` 和 `context_after` 必须按 `data-001-v020-model-api.md` 中固定的规范化页文本和 chunk offset 算法生成；前端只展示后端返回值，不自行重新生成上下文。
  - `hit_reason` 必须是确定性命中原因，不得生成无来源解释。
  - 资料已删除、chunk 已删除或来源结果已被重处理清除时，来源详情接口返回 HTTP 404，`detail` 固定为 `来源已失效`，前端展示 `来源已失效` 错误状态，不得展示缓存片段伪装为可打开来源。
  - PDF 文件不存在时，`GET /documents/{document_id}/file` 返回 HTTP 404，`detail` 固定为 `资料文件不存在`，前端展示 `资料文件不存在` 错误状态，不得展示缓存 PDF 或缓存片段伪装为可打开来源。
- PDF 阅读控件契约：
  - `PdfReaderShell` 顶部工具栏从左到右固定为文件名、页码状态、上一页 IconButton、下一页 IconButton、回到命中页按钮；文件名超过一行时中间截断并保留扩展名。
  - 页码状态文案固定为 `第 {current_page} / {page_count} 页`；`page_count` 来自资料详情的 `page_count`，不得为空或缺失；若无法取得 `page_count`，来源阅读视图必须阻塞并展示后端 `detail`，不得降级为未知总页数。
  - 打开来源详情时 `current_page` 固定初始化为来源 `page_no`，命中页固定为该 `page_no`；命中页状态使用 `StatusPill` 展示 `命中页`。
  - 上一页按钮使用 `ChevronLeft` 图标，`aria-label` 固定为 `上一页`；`current_page <= 1` 时 disabled。
  - 下一页按钮使用 `ChevronRight` 图标，`aria-label` 固定为 `下一页`；存在 `page_count` 且 `current_page >= page_count` 时 disabled。
  - 回到命中页按钮文案固定为 `回到命中页`；`current_page = page_no` 时 disabled。
  - 页码变化只更新 PDF 文件 URL hash 中的 `page` 值和页码状态，不重新请求来源详情，不改变命中段落与上下文。
  - PDF 文件接口返回 `资料文件不存在` 时，阅读区错误状态固定使用 `AlertTriangle` 图标、标题 `资料文件不存在`、正文 `无法打开原 PDF 文件。`；来源详情接口返回 `来源已失效` 时，错误状态固定使用 `AlertTriangle` 图标、标题 `来源已失效`、正文 `该来源已被删除或重新处理。`。
- 验收标准：
  - 点击任一来源结果可打开详情视图。
  - 详情视图展示 PDF 目标页。
  - 详情视图展示命中段落和上下文。
  - 详情视图展示文件名、页码、命中原因、相似度分数和排序位置。
  - 用户可以在不同来源结果之间切换。
  - PDF 阅读视图展示极简页码导航，当前命中页必须突出。
  - 用户可以前后翻页，并可以一键回到命中页。
  - PDF 加载失败时展示 `资料文件不存在` 错误状态。
  - 不要求 bbox 高亮，但目标页和命中段落必须明确。
  - 移动端全屏详情层必须提供返回当前题目的入口，返回后题目和已选来源不丢失。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 打开来源详情 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、真实 PostgreSQL、Linux、Playwright 浏览器 | 已处理 `tests/fixtures/text-layer-material.pdf` 并检索 `tests/fixtures/question.txt` 得到来源结果 | 执行 `make verify-e2e SCENARIO=v020-source-reader-open`；执行 `make verify-db CHECK=v020-source-detail-fields` | PDF 跳转目标页，详情展示命中段落、上下文、相似度分数、排序位置和确定性命中原因 | API/DB 字段检查已验证；E2E 已验证点击来源结果打开来源阅读区，展示 PDF 页入口、命中段落、上下文、相似度分数、排序位置、置信层级和确定性命中原因 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_source_reader.py`、`backend/app/main.py`、`scripts/verify_db.py`、本地命令输出 | 通过 |
| 切换来源 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 至少存在两条来源结果 | 执行 `make verify-e2e SCENARIO=v020-source-reader-switch` | PDF 页和段落详情随选择更新 | E2E 已验证两条真实来源结果之间切换时，来源阅读区原地替换 PDF 页、页码、命中段落、上下文、相似度分数、排序位置、置信层级和命中原因 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_source_reader.py`、本地命令输出 | 通过 |
| PDF 失败状态 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、Linux、Playwright 浏览器 | 已通过测试场景构造文件缺失状态，且固定资料 PDF `tests/fixtures/text-layer-material.pdf` 存在 | 执行 `make verify-e2e SCENARIO=v020-source-reader-file-missing`；执行 `make verify-api-contract CHECK=v020-pdf-file-api` | 页面展示 `资料文件不存在` 错误状态，不伪造内容 | PDF 文件接口 API 契约已验证固定 PDF 成功返回、资料不存在和文件缺失错误；E2E 已验证来源详情可打开但原 PDF 文件缺失时，前端展示固定 `资料文件不存在` 错误状态且不展示 PDF 阅读 iframe | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_source_file_missing.py`、`backend/app/main.py`、`scripts/verify_api_contract.py`、本地命令输出 | 通过 |
| 页码导航 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、真实 PostgreSQL、Linux、Playwright 浏览器 | 已处理 `tests/fixtures/text-layer-material.pdf` 并打开来源详情 | 执行 `make verify-e2e SCENARIO=v020-source-reader-page-nav`；执行 `make verify-visual CHECK=source-page-nav` | 当前命中页突出，上一页、下一页和回到命中页可用 | 未验证 | 待补充 | 阻塞 |
| 移动端来源详情 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、真实 PostgreSQL、Linux、Playwright 浏览器、390x844 viewport | 已处理 `tests/fixtures/text-layer-material.pdf` 并检索 `tests/fixtures/question.txt` 得到来源结果 | 执行 `make verify-e2e SCENARIO=v020-source-reader-mobile`；执行 `make verify-visual CHECK=source-reader-mobile` | 点击来源后打开全屏详情层；返回后当前题目和已选来源不丢失 | 未验证 | 待补充 | 阻塞 |
| 来源失效 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、本地文件系统、Linux、Playwright 浏览器 | 已生成来源结果后删除对应资料或重处理清除旧 chunk | 执行 `make verify-e2e SCENARIO=v020-source-reader-stale-source`；执行 `make verify-api-contract CHECK=v020-stale-source` | 来源详情返回 HTTP 404；前端展示失效状态，不展示缓存片段伪来源 | API 契约已验证；E2E 已验证旧来源结果可见但来源详情返回 `来源已失效` 时，前端展示固定失效错误状态且不展示 PDF 阅读 iframe 或缓存命中片段 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_stale_source.py`、`backend/app/main.py`、`scripts/verify_api_contract.py`、本地命令输出 | 通过 |

- 风险与回滚：PDF 阅读视图实现复杂。若无法完成高级阅读控件，仍必须完成目标页打开、段落详情和上下文展示，不得退回小片段列表。

# 上传与处理进度可视化

- 类型：功能新增
- 状态：草案
- 背景：资料处理包含上传、解析、切块、embedding 和索引建立。用户需要知道系统是否还在工作、卡在哪一步、是否失败。
- 当前问题：上传和处理过程缺少可视化进度感，用户只能看到粗略状态文字，无法判断系统是否正在工作、卡在哪一步、是否需要等待、重试或处理错误；处理失败时也缺少直接修复入口。
- 目标行为：资料上传和后台处理必须展示一个有视觉存在感的“纸页入库”进度组件，而不是只切换状态文字。上传时，资料以一张浅色纸页或资料条的形式进入资料库，纸页边缘出现基于真实上传进度的细线填充；无法取得浏览器上传字节进度时，使用明确的非百分比流动线表示“正在传输”，不得显示伪百分比。上传完成后，同一个视觉对象接入处理轨道，轨道按固定阶段依次点亮：上传完成、提取文字、切块、生成 embedding、建立索引、完成。失败时必须在失败节点旁展示三个修复入口：重新处理、删除资料、查看失败原因。状态必须来自真实上传事件、后端任务和数据库记录，不得只在前端伪造。
- 非目标：不包含精确百分比、断点续传、后台通知中心、邮件通知。
- 发布必要性：必须发布
- 用户可见影响：用户上传 PDF 后能看到资料正在进入系统并被索引的连续视觉过程，而不是只看到几段状态文字；失败时能明确看到失败阶段和原因。
- 涉及模块：前端上传组件、资料状态 UI、后端上传 API、后台任务、数据库。
- 配置、接口或数据结构变化：资料处理状态必须表达以下固定阶段：上传完成、提取文字、切块、生成 embedding、建立索引、完成、失败。
- 兼容性要求：刷新页面后必须能从后端恢复真实状态；不能只依赖前端内存。
- 阶段契约：
  - 后端持久化阶段使用 `data-001-v020-model-api.md` 固定枚举：`uploaded`、`extracting_text`、`chunking`、`embedding`、`indexing`、`completed`、`failed`。
  - 前端展示文案固定映射为：`uploaded` 显示 `上传完成`，`extracting_text` 显示 `提取文字`，`chunking` 显示 `切块`，`embedding` 显示 `生成 embedding`，`indexing` 显示 `建立索引`，`completed` 显示 `完成`，`failed` 显示 `失败`。
  - 后台任务进入每个阶段前必须先写入 `documents.processing_stage`；阶段完成后才能进入下一阶段。
  - `completed` 时 `documents.status = completed`、`processing_stage = completed`、`failed_stage = NULL`、`failure_code = NULL`、`failure_reason = NULL`。
  - `failed` 或 `unsupported` 时 `processing_stage = failed`，`failed_stage` 固定为失败发生前正在执行的非终态阶段，`failure_code` 和 `failure_reason` 必须非空。
  - `failure_reason` 必须严格使用 `data-001-v020-model-api.md` 中 `failure_code` 的固定映射文案，不得拼接动态异常文本；动态异常详情只能进入后端日志。
  - `unsupported` 用于真实 PDF 但无文字层的资料；非 PDF 上传在上传 API 层返回 HTTP 400，不创建资料记录。
- 上传进度契约：
  - 浏览器通过 XMLHttpRequest upload progress 事件取得 `loaded` 和 `total` 且 `lengthComputable = true` 时，细线填充宽度固定为 `loaded / total`，显示范围限制在 0% 到 100%，不显示数字百分比。
  - `lengthComputable = false`、`total = 0` 或运行环境无法提供字节进度时，细线进入非百分比流动线状态，前端不得显示百分比、剩余时间或伪速度。
  - 上传 API 返回成功前，资料不得出现在处理轨道的 `上传完成` 节点之后；上传 API 成功后，资料对象按后端返回的 `status` 和 `processing_stage` 渲染。
  - 上传失败时不创建资料行；前端在上传区域展示错误文案，非 PDF 固定显示 `v0.2.0 只支持上传 PDF 文件`。
- 状态恢复与轮询契约：
  - 前端刷新后必须通过 `GET /projects/{project_id}/documents` 和 `GET /documents/{document_id}` 恢复状态，不得从 localStorage、sessionStorage 或内存缓存恢复处理阶段。
  - 处理中资料轮询间隔固定为 1500ms；同一项目内多个处理中资料共用一次资料列表轮询请求，不得为每份资料单独创建轮询请求。
  - 资料进入 `completed`、`failed` 或 `unsupported` 后停止轮询该资料。
  - 用户点击 `查看失败原因` 时打开资料详情层，并定位到失败阶段、失败码和失败原因区域。
  - 用户点击 `重新处理` 时调用 `POST /documents/{document_id}/reprocess`；点击 `删除资料` 时调用 `DELETE /documents/{document_id}`。
- 验收标准：
  - 上传开始时出现“纸页入库”视觉组件，包含浅色纸页或资料条、细线进度和文件名。
  - 浏览器能提供上传字节进度时，细线填充必须使用真实上传进度。
  - 浏览器不能提供上传字节进度时，必须使用非百分比流动线表示正在传输，不得显示伪百分比。
  - 上传完成后，同一个视觉对象进入处理轨道，不得突兀切换成纯文字列表。
  - 处理轨道固定展示上传完成、提取文字、切块、生成 embedding、建立索引、完成六个节点。
  - 当前节点有轻量动效，已完成节点有明确完成态，失败节点有明确失败态。
  - 动效必须克制、平滑、符合 Nature 论文式高级浅色自然系，不得使用廉价彩虹进度条、大面积闪烁、旋转加载器堆叠或强干扰动画。
  - 失败状态展示可理解原因，并固定提供重新处理、删除资料、查看失败原因三个入口。
  - 页面刷新后状态不丢失。
  - 多资料处理时每份资料状态独立。
  - 处理中资料轮询不为每份资料重复发起独立列表请求。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 正常处理进度 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 Redis/RQ、真实 PostgreSQL、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已创建项目并准备 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-processing-progress`；执行 `make verify-db CHECK=v020-processing-stages`；执行 `make verify-visual CHECK=processing-progress-visual` | 页面展示“纸页入库”视觉、真实上传进度或非百分比传输线、真实处理轨道，并最终完成 | 未验证 | 待补充 | 阻塞 |
| 失败状态 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 准备 `tests/fixtures/broken.pdf` | 执行 `make verify-e2e SCENARIO=v020-processing-failure` | 页面展示失败状态、可理解原因、重新处理、删除资料、查看失败原因入口 | 未验证 | 待补充 | 阻塞 |
| 刷新恢复 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已上传 `tests/fixtures/text-layer-material.pdf` 且资料正在处理或已失败 | 执行 `make verify-e2e SCENARIO=v020-processing-refresh` | 页面恢复后端记录的真实状态 | 未验证 | 待补充 | 阻塞 |
| 非百分比上传 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 测试场景拦截上传进度事件并固定 `lengthComputable = false` | 执行 `make verify-e2e SCENARIO=v020-upload-indeterminate-progress`；执行 `make verify-visual CHECK=upload-indeterminate-progress` | 页面展示非百分比流动线，不展示伪百分比、剩余时间或伪速度 | 未验证 | 待补充 | 阻塞 |
| 轮询合并 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 当前项目存在 3 份处理中资料 | 执行 `make verify-e2e SCENARIO=v020-processing-polling-coalesced` | 前端以项目资料列表为单位轮询，不为每份资料创建独立轮询请求 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：如果无法获取真实阶段，不得用假百分比替代；必须修复后端状态记录后再继续实现。

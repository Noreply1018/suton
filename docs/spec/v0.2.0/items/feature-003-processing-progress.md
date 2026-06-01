# 上传与处理进度可视化

- 类型：功能新增
- 状态：草案
- 背景：资料处理包含上传、解析、切块、embedding 和索引建立。用户需要知道系统是否还在工作、卡在哪一步、是否失败。
- 当前问题：上传和处理过程缺少进度感，用户只能看到粗略状态，无法判断是否需要等待、重试或处理错误。
- 目标行为：资料上传和后台处理必须展示阶段式进度。状态必须来自真实后端任务和数据库记录，不得只在前端伪造。
- 非目标：不包含精确百分比、断点续传、后台通知中心、邮件通知。
- 发布必要性：必须发布
- 用户可见影响：用户上传 PDF 后能看到清晰的处理阶段、当前状态和失败原因。
- 涉及模块：前端上传组件、资料状态 UI、后端上传 API、后台任务、数据库。
- 配置、接口或数据结构变化：资料处理状态必须表达以下固定阶段：上传完成、提取文字、切块、生成 embedding、建立索引、完成、失败。
- 兼容性要求：刷新页面后必须能从后端恢复真实状态；不能只依赖前端内存。
- 验收标准：
  - 上传开始、上传完成、等待处理、处理中、完成、失败均有清晰 UI。
  - 后台阶段至少覆盖提取文字、切块、生成 embedding、建立索引。
  - 失败状态展示可理解原因。
  - 页面刷新后状态不丢失。
  - 多资料处理时每份资料状态独立。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 正常处理进度 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 Redis/RQ、真实 PostgreSQL、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已创建项目并准备 `tests/fixtures/text-layer-material.pdf` | 执行 `make verify-e2e SCENARIO=v020-processing-progress`；执行 `make verify-db CHECK=v020-processing-stages` | 页面展示真实阶段并最终完成 | 未验证 | 待补充 | 阻塞 |
| 失败状态 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 准备 `tests/fixtures/broken.pdf` | 执行 `make verify-e2e SCENARIO=v020-processing-failure` | 页面展示失败状态和可理解原因 | 未验证 | 待补充 | 阻塞 |
| 刷新恢复 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已上传 `tests/fixtures/text-layer-material.pdf` 且资料正在处理或已失败 | 执行 `make verify-e2e SCENARIO=v020-processing-refresh` | 页面恢复后端记录的真实状态 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：如果无法获取真实阶段，不得用假百分比替代；必须修复后端状态记录后再继续实现。

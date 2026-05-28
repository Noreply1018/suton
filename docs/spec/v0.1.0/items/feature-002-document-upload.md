# 资料 PDF 上传与状态

- 类型：功能新增
- 状态：草案
- 背景：资料 PDF 是 Suton 建立课程知识库的输入。v0.1.0 只支持有文字层的 PDF。
- 当前问题：没有资料上传和状态反馈，用户无法知道资料是否进入处理链路。
- 目标行为：用户可以在项目内上传 PDF，系统保存原文件，创建资料记录，并展示上传、处理和失败状态。
- 非目标：不包含 OCR、扫描版 PDF 识别、PPT/Word/图片上传、批量上传优化、对象存储、断点续传。
- 发布必要性：必须发布
- 用户可见影响：用户可以在资料库页面上传 PDF，并看到文件名、页数、处理状态和失败原因。
- 涉及模块：前端资料库页面、文件上传 API、文件存储、数据库、后台任务入口。
- 配置、接口或数据结构变化：新增 `documents` 数据对象；新增上传接口；本地 `uploads/` 作为文件存储目录。
- 兼容性要求：无特殊要求。
- 验收标准：
  - 用户只能上传 PDF 文件。
  - 上传成功后原文件保存到本地文件存储。
  - 数据库创建 `documents` 记录。
  - 页面展示文件名、页数、状态。
  - 非 PDF 文件被拒绝，并显示可理解错误。
  - 处理失败时页面展示失败状态和失败原因。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 上传有文字层 PDF | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector；本地文件系统 `uploads/` 可写 | 已执行 `make reset-demo` 和 `make migrate`；已创建项目；准备固定样例 PDF `tests/fixtures/text-layer.pdf` | 执行 `make dev`；在资料库上传 `tests/fixtures/text-layer.pdf`；执行 `make verify-db CHECK=document-uploaded FILE=tests/fixtures/text-layer.pdf`；执行 `make verify-db CHECK=uploaded-file-exists FILE=tests/fixtures/text-layer.pdf` | 文件保存到 `uploads/`，页面展示文件名、页数和处理中或完成状态 | 待验证 | 待填写 | 阻塞 |
| 拒绝非 PDF | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector | 已创建项目，准备 `tests/fixtures/not-pdf.txt` | 执行 `make dev`；在资料库上传 `tests/fixtures/not-pdf.txt`；执行 `make verify-db CHECK=document-count-unchanged` | 上传被拒绝，数据库不创建资料记录，页面展示错误 | 待验证 | 待填写 | 阻塞 |
| 处理失败展示 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector；本地文件系统 `uploads/` 可写 | 准备损坏 PDF `tests/fixtures/broken.pdf` | 执行 `make dev`；上传 `tests/fixtures/broken.pdf`；执行 `make process-demo FILE=tests/fixtures/broken.pdf EXPECT_FAILURE=1`；执行 `make verify-db CHECK=document-failed FILE=tests/fixtures/broken.pdf` | 页面展示失败状态和失败原因 | 待验证 | 待填写 | 阻塞 |

- 风险与回滚：文件上传容易引入格式和大小范围膨胀。若实现压力过大，应仅保留单文件 PDF 上传和基础状态。

# PDF 文字提取、切块与索引

- 类型：处理链路变更
- 状态：已完成
- 背景：题目溯源依赖可检索的资料内容。v0.1.0 只处理有文字层的 PDF。
- 当前问题：未解析和索引资料时，题目无法反查到页码和片段。
- 目标行为：系统对已上传 PDF 使用 PyMuPDF 提取文字层，按页生成基础 chunk；单页文本超过 2000 个 Unicode 字符时只在同一页内按段落切分并合并为不超过 2000 个 Unicode 字符的 chunk，为 chunk 建立 embedding 索引，并将处理状态写回资料记录。
- 非目标：不包含 OCR、扫描件处理、表格结构理解、公式结构解析、图片内容理解、LLM rerank、完整 hybrid search。
- 发布必要性：必须发布
- 用户可见影响：用户可以看到资料从处理中变为完成，随后题目检索可以返回该资料中的页码和片段。
- 涉及模块：FastAPI 后端、Redis、RQ worker、PyMuPDF PDF 解析、chunk 生成、embedding、PostgreSQL、pgvector 检索索引。
- 配置、接口或数据结构变化：新增 RQ 处理任务入口；`documents` 状态流转；`document_pages` 和 `chunks` 写入。
- 兼容性要求：无特殊要求。
- 验收标准：
  - 系统能使用 PyMuPDF 识别并处理有文字层 PDF。
  - 系统按页保存页面文本。
  - 系统默认每页生成 1 个基础 chunk；单页文本超过 2000 个 Unicode 字符时，只允许在该页内按段落切分，并合并为不超过 2000 个 Unicode 字符的多个 chunk。
  - 每个 chunk 保留 `document_id`、`page_no` 和 `text`。
  - 每个可检索 chunk 必须生成 embedding。
  - embedding 必须记录 provider、模型名称、向量维度和调用方式。
  - 处理成功后资料状态为完成。
  - 无文字层或提取文本为空的 PDF 在 v0.1.0 中标记失败或不支持，不自动进入 OCR。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 处理有文字层 PDF | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实 FastAPI 后端；真实 Redis/RQ worker；真实 PostgreSQL/pgvector；本地文件系统；embedding provider、模型、维度和调用方式已固定并可用 | 已上传固定样例 PDF `tests/fixtures/text-layer-material.pdf` | 执行 `make dev`；执行 `make process-demo FILE=tests/fixtures/text-layer-material.pdf`；执行 `make verify-db CHECK=document-processed FILE=tests/fixtures/text-layer-material.pdf`；执行 `make verify-db CHECK=chunk-embeddings FILE=tests/fixtures/text-layer-material.pdf` | 写入页面文本、chunks 和 embedding，资料状态为完成 | 已验证：PyMuPDF 提取文字层，写入页面文本、chunk 和 DashScope 1024 维 embedding，资料状态完成 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make process-demo`、`document-processed`、`chunk-embeddings` 通过 | 通过 |
| 拒绝无文字层 PDF | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实后端；真实 PostgreSQL/pgvector；本地文件系统 | 已上传扫描版或无文字层 PDF `tests/fixtures/scanned.pdf` | 执行 `make dev`；执行 `make process-demo FILE=tests/fixtures/scanned.pdf EXPECT_UNSUPPORTED=1`；执行 `make verify-db CHECK=document-unsupported FILE=tests/fixtures/scanned.pdf` | 资料状态为失败或不支持，并记录原因，不触发 OCR | 已验证：扫描件 fixture 标记为不支持并记录原因，不触发 OCR | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make process-demo FILE=tests/fixtures/scanned.pdf EXPECT_UNSUPPORTED=1` 和 `document-unsupported` 通过 | 通过 |
| chunk 来源完整 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实后端；真实 PostgreSQL/pgvector | 已完成固定样例 PDF 处理 | 执行 `make verify-db CHECK=chunk-source-complete FILE=tests/fixtures/text-layer-material.pdf` | 每个 chunk 都有资料 ID、页码、文本、embedding provider、模型名称和向量维度 | 已验证：固定资料所有 chunk 具备资料 ID、页码、文本、embedding provider、模型名称和 1024 维度 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make verify-db CHECK=chunk-source-complete` 通过 | 通过 |

- 风险与回滚：embedding 依赖可能受网络或模型服务影响。若无法可靠使用外部服务，必须标记阻塞，不得把关键词检索伪装为已完成 embedding 检索。

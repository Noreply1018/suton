# Suton v0.1.0 验证记录（2026-05-29）

## 环境基线

- 本地分支：`main...origin/main [ahead 6]`（验证开始前）。
- 运行环境：Linux WSL2。
- `make env-info` 已执行两次：
  - 普通 shell 环境显示 `DASHSCOPE_API_KEY exists: no`。
  - 真实闭环验证时仅通过命令环境变量注入凭据，`make env-info` 显示 `DASHSCOPE_API_KEY exists: yes`。
- 工具版本：
  - Node.js `v22.22.2`
  - pnpm `10.33.0`
  - Python `3.12.3`
  - uv `0.11.7`
  - Docker `29.5.2`
  - RQ `2.9.0`
  - Playwright `1.60.0`
- embedding 固定语义：
  - provider：DashScope
  - model：`text-embedding-v4`
  - dimension：1024
  - base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`

## 固定 fixture 核验

通过 `make test` 中的 `scripts/tests/test_fixtures.py` 自动核验：

- `tests/fixtures/text-layer-material.pdf`：57 页，存在可提取文字层。
- `tests/fixtures/question-source.pdf`：6 页，存在可提取文字层。
- `tests/fixtures/question.txt`：非空。
- `tests/fixtures/scanned.pdf`：1 页，文字层为空。
- `tests/fixtures/broken.pdf`：PyMuPDF 打开失败，作为损坏 PDF fixture。
- `tests/fixtures/not-pdf.txt` 和 `tests/fixtures/unmatched-question.txt` 存在。

## 已执行命令与结果

以下命令均在仓库根目录执行；需要 embedding 的命令仅通过当前命令环境变量注入凭据，未写入文件。

```text
make env-info
```

结果：基础工具和固定 embedding 配置可见；普通 shell 中凭据不存在。

```text
make test
```

结果：`15 passed, 1 warning`；前端 `tsc --noEmit` lint/typecheck 通过。

```text
make verify-db CHECK=schema-v0.1.0
```

结果：通过；确认 v0.1.0 必需表、必需列和 pgvector extension。

```text
make verify-e2e
```

结果：真实 Web、FastAPI、PostgreSQL/pgvector、Redis/RQ 和本地文件系统闭环通过；8 个 Playwright 场景全部通过。

```text
SCENARIO=minimal-loop make verify-e2e
```

结果：仅运行 `minimal-loop/source-results` 场景，1 个 Playwright 场景通过。

```text
make reset-demo
make migrate
make process-demo FILE=tests/fixtures/text-layer-material.pdf
make verify-db CHECK=document-processed FILE=tests/fixtures/text-layer-material.pdf
make verify-db CHECK=chunk-embeddings FILE=tests/fixtures/text-layer-material.pdf
make verify-db CHECK=chunk-source-complete FILE=tests/fixtures/text-layer-material.pdf
```

结果：固定资料 PDF 处理完成，写入页面文本、chunk 和 DashScope 1024 维 embedding。

```text
make process-demo FILE=tests/fixtures/scanned.pdf EXPECT_UNSUPPORTED=1
make verify-db CHECK=document-unsupported FILE=tests/fixtures/scanned.pdf
```

结果：扫描件标记为不支持，未进入 OCR。

```text
make process-demo FILE=tests/fixtures/broken.pdf EXPECT_FAILURE=1
make verify-db CHECK=document-failed FILE=tests/fixtures/broken.pdf
```

结果：损坏 PDF 标记为失败并记录失败原因。

```text
make verify-db CHECK=document-uploaded FILE=tests/fixtures/text-layer-material.pdf
make verify-db CHECK=uploaded-file-exists FILE=tests/fixtures/text-layer-material.pdf
make verify-db CHECK=question-created FILE=tests/fixtures/question.txt
make verify-db CHECK=question-matches-with-source
make verify-db CHECK=source-lineage
make verify-db CHECK=missing-source-not-visible
make verify-db CHECK=no-question-matches FILE=tests/fixtures/unmatched-question.txt
make verify-db CHECK=project-count-unchanged
make verify-db CHECK=document-count-unchanged
make verify-db CHECK=question-count-unchanged
```

结果：全部通过。

## 结论

- v0.1.0 最小闭环已经在真实 Web、真实后端、真实 PostgreSQL/pgvector、真实 Redis/RQ、真实文件系统和真实 DashScope embedding 下通过。
- 固定资料 PDF、固定题目、资料上传、资料处理、题目输入、来源结果展示、空结果、缺来源过滤、非 PDF 拒绝、损坏 PDF 失败、扫描件不支持均有本地可复现验证。
- 发布门禁中的远端状态以推送后的 `git ls-remote --heads origin main` 命令输出为准；该证据不写回同一个已推送提交，避免验证记录自引用。

# 更新日志

这里记录 Suton 每个版本中值得用户关注的变化。

## [未发布]

## [0.1.0] - 2026-05-31

### 最小闭环

- 支持创建项目，并在项目内管理资料和题目。
- 支持上传带文字层的 PDF 资料，使用 PyMuPDF 提取页面文本。
- 支持按页和页内段落切块，并通过 DashScope `text-embedding-v4` 生成 1024 维 embedding。
- 使用 PostgreSQL + pgvector 保存 chunk 和向量索引，使用 Redis + RQ 执行后台资料处理。
- 支持手动输入一道题，并返回最多 5 条带来源的资料依据。
- 每条资料依据包含文件名、页码、原文片段、pgvector 相似度、确定性命中原因和原始 PDF 页码入口。
- 不展示无来源答案，不生成长篇 AI 讲解。

### 容器发布

- 新增 Suton app Docker 镜像构建，镜像内包含 Next.js 前端、FastAPI 后端和 RQ worker。
- 新增 `docker-compose.prod.yml`，一键拉起 Suton app、PostgreSQL/pgvector 和 Redis。
- 新增 GitHub Actions release workflow，tag 发布时推送 GHCR 镜像并创建 GitHub Release；Docker Hub 在配置 secret 后自动启用。
- 新增 Docker Hub 描述文档和 changelog release notes 提取脚本。

### 验证

- `make test`
- `make verify-e2e`
- `SCENARIO=minimal-loop make verify-e2e`
- `make verify-spec`
- `make verify-secrets`
- 容器镜像构建与 `docker-compose.prod.yml` 真实闭环验证。

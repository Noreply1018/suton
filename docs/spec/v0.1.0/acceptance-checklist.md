# Suton v0.1.0 总验收清单

本清单用于每次 v0.1.0 范围实现、验证或发布前建立统一完成标准。任何一项无法取得真实证据时，结论只能是阻塞，不能写成已完成。

## 1. 范围与语义

- 已读取 `AGENTS.md`、`.agents/skills/suton-spec-gate/SKILL.md`、`docs/spec/v0.1.0/README.md` 和相关 `items/*.md`。
- 所有本次涉及条目状态、目标行为、非目标、验收标准和验证矩阵一致。
- spec 中没有会影响实现选择的开放语义；若存在，先修 spec 或询问用户。
- v0.1.0 不引入 OCR、自动切题、AI 长篇讲解、知识图谱、覆盖分析、引用完整性、生产部署、CI/CD 发布或 GitHub Release。

## 2. 本地工具与环境

- `make env-info` 已执行并保留输出。
- Docker、PostgreSQL、pgvector、Redis、RQ、Node.js、pnpm、Python、uv、Playwright 浏览器均可核验。
- `DATABASE_URL`、`REDIS_URL`、embedding provider、model、dimension、base URL 与 spec 一致。
- `DASHSCOPE_API_KEY` 只通过命令环境变量注入；不得写入仓库文件、验证记录或证据包。

## 3. 真实闭环验证

- 验证前执行 `make reset-demo`，清理旧上传、旧索引和旧数据库记录。
- 执行 `make migrate`，确认 schema 和 pgvector 可用。
- 执行 `make process-demo FILE=tests/fixtures/text-layer-material.pdf`，确认页面文本、chunk 和 embedding 生成。
- 执行 `make verify-e2e`，确认真实浏览器、真实 FastAPI、真实 PostgreSQL/pgvector、真实 Redis/RQ 和本地文件系统闭环。
- 执行 `SCENARIO=minimal-loop make verify-e2e`，确认最小闭环单场景可独立复现。
- 执行 `make test`，确认后端测试、脚本测试、前端 lint 和 typecheck 通过。

## 3.1 UI 参考图风格验收

- 对照 `docs/assets/ui/suton-trace-request-ui-draft.png` 执行首屏 UI 验收。
- 前端必须具备三栏信息架构：左侧 Suton 导航、中间溯源请求工作区、右侧证据预览面板。
- 前端必须保留资料库入口、资料上传、手动题目输入、资料依据结果展示和空结果状态。
- 视觉语言必须贴近参考图的浅色纸感背景、青绿色主色、紧凑信息密度、节点化来源候选和右侧证据面板。
- UI 验收不得把知识图谱、覆盖分析、引用完整性或复杂统计图表升级为 v0.1.0 真实功能承诺。
- UI 相关 Playwright 断言必须覆盖左侧导航、中间溯源工作区、右侧证据预览、资料上传入口、题目输入入口和来源结果卡片。

## 4. 数据与边界检查

- `make verify-db CHECK=schema-v0.1.0` 通过。
- `make verify-db CHECK=source-lineage` 通过。
- `make verify-db CHECK=question-matches-with-source` 通过。
- `make verify-db CHECK=missing-source-not-visible` 通过。
- `make verify-db CHECK=no-question-matches FILE=tests/fixtures/unmatched-question.txt` 通过。
- 扫描件 fixture、损坏 PDF fixture、非 PDF fixture 的拒绝或失败路径均有证据。

## 5. 门禁辅助工具

- `make verify-spec` 通过，确认 spec item 状态、验证矩阵和验证记录引用一致。
- `make verify-secrets` 通过，确认 Git 已追踪文本文件中没有疑似真实 key、token、secret 或 password。
- 需要形成证据包时执行 `make evidence-package`；需要把 `make test` 一并纳入证据包时执行 `make evidence-package-with-tests`。

## 6. 审计、提交与远端

- 修改已追踪文件后，必须派发 subagent 严格审计。
- 审计不通过时先修复，再重新审计。
- 审计通过后提交改动，不得把已追踪文件改动停留在未提交状态。
- 推送后执行 `git ls-remote --heads origin main`，远端 `main` 必须指向目标提交。
- 远端复核证据以推送后的外部命令输出为准，不要求写回同一个提交，避免自引用。

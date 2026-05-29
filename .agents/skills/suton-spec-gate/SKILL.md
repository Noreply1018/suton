---
name: suton-spec-gate
description: Suton 项目门禁技能。Use when Codex works in the Suton repository on v0.1.0 scope, implementation, validation, tools, external state, specs, or release readiness, especially when blockers, missing tools, ambiguous semantics, fixtures, Docker/PostgreSQL/pgvector/Redis, embedding provider, Git remote state, CI, tags, or GitHub Release status may affect correctness.
---

# Suton Spec Gate

## 核心规则

当必需事实、工具、外部状态、fixture、凭据、语义决策或验证路径无法可靠确认时，先停止，再报告阻塞。

不得在门禁阻塞时开始实现、标记 spec 已就绪、标记验证通过、发布、打 tag、推送，或声称目标完成。阻塞报告必须使用中文，包含具体证据、已尝试的核验路径、已尝试的合理替代路径，以及需要用户补充的决策、权限、工具、凭据、样例或外部证据。

## 推进前核验

在实现或实质修改 v0.1.0 行为前，必须执行：

1. 读取 `AGENTS.md`、`docs/spec/v0.1.0/README.md` 和相关 `docs/spec/v0.1.0/items/*.md`。
2. 读取 `docs/spec/v0.1.0/acceptance-checklist.md`，建立本次总验收清单。
3. 检查 `git status --short --branch`。
4. 用命令核验本地必需工具，不得凭印象假设。
5. 涉及外部状态时，用可追溯证据核验，例如 `git ls-remote`、GitHub/registry/CI 查询，或用户提供的可信日志。
6. 找出目标范围内的所有开放语义。只要 spec 允许多个有效实现，先停止并修订 spec 或询问用户，不得先写代码。

## v0.1.0 固定栈

除非先修改 spec，否则 v0.1.0 固定为：

- 前端：Next.js + React + Tailwind CSS + pnpm。
- 后端：Python FastAPI + uv。
- 数据库：PostgreSQL + pgvector。
- 后台任务：Redis + RQ。
- 文件存储：本地 `uploads/`。
- PDF 文字层提取：PyMuPDF。
- 浏览器端到端验证：Playwright。
- OCR、自动切题、知识图谱、覆盖分析、引用完整性分析、长篇 AI 讲解、移动端 APK 不属于 v0.1.0。

## 阻塞条件

以下任一条件成立时，必须立即停止并报告阻塞：

- Docker、PostgreSQL、pgvector、Redis、Node.js、pnpm、Python、uv、Playwright 浏览器或必需 Make target 缺失或无法核验。
- 当前任务依赖 `DATABASE_URL`、`REDIS_URL`、embedding 凭据或其他关键环境变量，但它们缺失或无法核验。
- 当前任务会生成或验证 embedding，但 embedding provider、模型、维度或调用方式尚未在 spec 中固定。
- `tests/fixtures/text-layer-material.pdf`、`tests/fixtures/question-source.pdf` 或 `tests/fixtures/question.txt` 等必需 fixture 缺失。
- spec 对实现必须选择的行为仍保留“或”“可选”“建议”“推荐”“兜底”“可以使用”等选择空间。
- 结果会依赖 mock，但 spec 要求真实 Web App、真实后端、真实数据库、真实 pgvector、真实 Redis 或真实文件。
- 远端仓库、tag、release、CI 或 registry 状态无法通过可追溯证据核验。

## 变更纪律

- 用户要求审计时，只审计，不修改文件。
- 修改文件后必须派发 subagent 严格审计；若 subagent 工具不可用，停止并报告阻塞。
- 在 Git 仓库中，已追踪文件改动通过审计后必须提交，不得把完成改动留在未提交状态。
- 未核验远端状态前，不得声称 push、tag、release 或远端完成。
- 修改 v0.1.0 spec、验证记录、门禁脚本或发布流程后，至少执行 `make verify-spec` 和 `make verify-secrets`。
- 需要归档完成性证据时，执行 `make evidence-package`；若需要把测试结果纳入同一证据包，执行 `make evidence-package-with-tests`。
- 任何证据包、验证记录和最终回复不得包含真实 API key、token、secret 或 password。

## 阻塞报告格式

```text
阻塞：<一句话说明>
已核验：<命令、文件、证据>
已尝试替代路径：<若无可写“无合理替代路径”>
不能继续的原因：<关联到 spec 或门禁>
需要用户提供：<权限、工具、凭据、样例、决策或外部证据>
```

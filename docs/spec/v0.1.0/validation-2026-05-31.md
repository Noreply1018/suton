# Suton v0.1.0 UI 验证记录（2026-05-31）

## 验证范围

本记录补充验证 `ui-001-reference-fidelity`。目标是确认 v0.1.0 前端从通用表单式原型改造为接近用户参考图的资料溯源工作台，同时不引入知识图谱、覆盖分析、引用完整性、OCR、自动切题或 AI 长篇讲解等已排除功能。

## 已执行命令与结果

```text
pnpm --filter @suton/web typecheck
```

结果：通过。

```text
pnpm --filter @suton/web lint
```

结果：通过。

```text
make dev
pnpm exec playwright screenshot --viewport-size=1440,900 http://127.0.0.1:3000 tmp/suton-ui-check.png
```

结果：首屏截图已人工核对，页面具备左侧 Suton 品牌导航、中间节点化溯源请求工作区、右侧证据预览、底部资料概览和题目输入入口，视觉语言贴近参考图的浅色纸感背景、青绿色主色、低饱和分隔线和紧凑信息密度。

```text
make verify-e2e
```

结果：8 个 Playwright 场景全部通过。验证覆盖真实 Next.js 前端、真实 FastAPI 后端、真实 PostgreSQL/pgvector、真实 Redis/RQ、本地文件系统和 DashScope embedding。新增 UI 断言覆盖左侧导航、中间溯源工作区、右侧证据预览、资料库入口、来源结果卡片和 PDF 页码入口。

```text
make verify-spec
```

结果：通过；`ui-001-reference-fidelity` 状态、验证矩阵、UI 验证记录和发布门禁引用一致。

```text
make verify-secrets
```

结果：通过；Git 已追踪文本文件中未发现疑似真实 API key、token、secret 或 password。

```text
make test
```

结果：`21 passed, 1 warning`；前端 `tsc --noEmit` lint/typecheck 通过。

## 结论

- `ui-001-reference-fidelity` 已完成。
- v0.1.0 前端已经从通用表单式原型改造为资料溯源工作台。
- UI 改造没有扩大 v0.1.0 功能范围；覆盖分析、知识图谱和引用完整性仍只是非目标，不作为真实功能承诺。
- 真实最小闭环、文件上传、题目输入、来源结果、空结果、缺来源过滤、非 PDF 拒绝、损坏 PDF 失败路径仍通过。
- `make verify-spec`、`make verify-secrets` 和 `make test` 均通过。

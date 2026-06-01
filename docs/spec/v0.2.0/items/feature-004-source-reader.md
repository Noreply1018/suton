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
- 配置、接口或数据结构变化：来源结果详情接口必须返回文件 ID、文件名、页码、chunk ID、原文片段、上下文、PDF 页入口、pgvector 相似度分数、排序位置和确定性命中原因。
- 兼容性要求：无来源结果不得进入阅读视图；被删除资料的旧结果不得打开为有效来源。
- 验收标准：
  - 点击任一来源结果可打开详情视图。
  - 详情视图展示 PDF 目标页。
  - 详情视图展示命中段落和上下文。
  - 详情视图展示文件名、页码、命中原因、相似度分数和排序位置。
  - 用户可以在不同来源结果之间切换。
  - PDF 阅读视图展示极简页码导航，当前命中页必须突出。
  - 用户可以前后翻页，并可以一键回到命中页。
  - PDF 加载失败时展示错误状态。
  - 不要求 bbox 高亮，但目标页和命中段落必须明确。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 打开来源详情 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、真实 PostgreSQL、Linux、Playwright 浏览器 | 已处理 `tests/fixtures/text-layer-material.pdf` 并检索 `tests/fixtures/question.txt` 得到来源结果 | 执行 `make verify-e2e SCENARIO=v020-source-reader-open` | PDF 跳转目标页，详情展示命中段落、上下文、相似度分数、排序位置和确定性命中原因 | 未验证 | 待补充 | 阻塞 |
| 切换来源 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 至少存在两条来源结果 | 执行 `make verify-e2e SCENARIO=v020-source-reader-switch` | PDF 页和段落详情随选择更新 | 未验证 | 待补充 | 阻塞 |
| PDF 失败状态 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、Linux、Playwright 浏览器 | 已通过测试场景构造文件缺失或访问失败状态 | 执行 `make verify-e2e SCENARIO=v020-source-reader-file-missing` | 页面展示可理解错误，不伪造内容 | 未验证 | 待补充 | 阻塞 |
| 页码导航 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实文件存储、真实 PostgreSQL、Linux、Playwright 浏览器 | 已处理 `tests/fixtures/text-layer-material.pdf` 并打开来源详情 | 执行 `make verify-e2e SCENARIO=v020-source-reader-page-nav`；执行 `make verify-visual CHECK=source-page-nav` | 当前命中页突出，上一页、下一页和回到命中页可用 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：PDF 阅读视图实现复杂。若无法完成高级阅读控件，仍必须完成目标页打开、段落详情和上下文展示，不得退回小片段列表。

# 视觉质量与审美门禁

- 类型：验证与发布门禁
- 状态：草案
- 背景：v0.2.0 的核心目标之一是显著提升界面美感。视觉质量不能只靠主观口头评价，必须进入发布门禁。
- 当前问题：v0.1.0 前端丑、杂、长、缺少层级，且没有视觉验收规则约束。
- 目标行为：v0.2.0 发布前必须通过视觉质量门禁，包括截图矩阵、人工审美审计、响应式检查、状态覆盖和旧设计清除检查。审计不通过时不得发布。
- 非目标：不包含像素级设计稿还原、第三方设计奖项评审、A/B 测试。
- 发布必要性：必须发布
- 用户可见影响：用户获得明显更简约、更高级、更愿意使用的界面。
- 涉及模块：前端、Playwright、截图证据、文档、审计流程。
- 配置、接口或数据结构变化：需要新增或更新视觉截图验证脚本和审计记录路径。
- 兼容性要求：视觉门禁不得替代功能测试；必须与真实功能闭环一起通过。
- 证据路径契约：
  - 视觉截图归档根目录固定为 `tmp/v0.2.0-visual-evidence/`，发布证据包必须复制到 `tmp/v0.2.0-evidence-latest.md`。
  - 截图文件命名固定为 `{viewport}-{state}.png`，其中 viewport 只能是 `1440x900`、`1280x832`、`1200x800`、`1024x768`、`390x844`。
  - `state` 固定枚举为：`first-empty-project`、`project-created`、`document-list`、`document-health`、`paper-ingest-uploading`、`processing-rail-running`、`processing-failure-actions`、`question-search`、`source-confidence-levels`、`no-reliable-source`、`focus-mode`、`source-detail`、`source-page-nav`、`pdf-reader`、`long-lists`、`mobile-workspace`。
  - 每张截图必须同时记录对应 URL、viewport、浏览器、Git commit、数据准备命令和截图时间；元数据文件固定为 `tmp/v0.2.0-visual-evidence/manifest.json`。
  - `manifest.json` 顶层固定为对象：`version` 必须等于 `v0.2.0`；`git_commit` 为 40 位提交 SHA；`generated_at` 为 UTC ISO-8601 字符串；`screenshots` 为数组。每个截图对象必须包含 `state`、`viewport`、`path`、`url`、`browser`、`data_command`、`captured_at`；`state` 和 `viewport` 必须属于本条目固定枚举；`path` 必须指向存在的 PNG 文件。
  - 人工审美审计记录固定为 `docs/spec/v0.2.0/visual-audit.md`；实现期创建该文件前，视觉门禁保持阻塞。
  - `visual-audit.md` Markdown 结构固定为一级标题 `# Suton v0.2.0 视觉审计记录`，并依次包含二级标题 `## 审计元信息`、`## 截图矩阵结论`、`## 问题列表`、`## 修复记录`、`## 最终结论`；`## 最终结论` 下第一行必须为 `结论：通过` 或 `结论：失败`。
- 视觉禁区：
  - 禁止厚重暗色背景、紫蓝主导渐变、彩虹进度条、大面积玻璃拟态、装饰性渐变球、默认 SaaS 卡片堆叠、营销 hero、无意义插画和可识别第三方产品布局复制。
  - 禁止通过隐藏内容、缩小字号到 11px 以下、牺牲可读性或关闭状态展示来通过截图。
  - 禁止把视觉审计建立在 mock 页面、静态截图或未连接真实后端的数据上；视觉截图必须来自真实 Web 应用。
- 自动检查契约：
  - `make verify-visual CHECK=screenshot-matrix` 必须启动真实浏览器并生成所有必需截图和 manifest；截图矩阵固定为每个 `state` 至少一张截图，且整体覆盖全部固定 viewport，不要求 `state` 与 viewport 形成 16x5 全笛卡尔积。
  - `make verify-visual CHECK=visual-hard-errors` 必须使用 Playwright 在每个固定 viewport 执行 DOM 检查：`document.documentElement.scrollWidth - document.documentElement.clientWidth > 1` 判定为横向滚动失败；任一可见 `button` 或 `[role="button"]` 的 `scrollWidth - clientWidth > 1` 判定为按钮文字溢出失败；任一带 `data-v020-check-overflow="true"` 的可见元素 `scrollWidth - clientWidth > 1` 或 `scrollHeight - clientHeight > 1` 判定为文本溢出失败；任一带 `data-v020-critical-region` 的可见元素矩形相交面积大于较小矩形面积 10% 判定为关键区域重叠失败；`main` 可见面积小于 viewport 面积 35% 判定为空白主体失败；`document.documentElement.scrollHeight > document.documentElement.clientHeight + 1` 判定为浏览器级纵向滚动失败。
  - `make verify-visual CHECK=visual-evidence-manifest` 必须校验 `manifest.json` 完整契约：`version` 等于 `v0.2.0`，`git_commit` 为 40 位提交 SHA，`generated_at` 和每个 `captured_at` 为 UTC ISO-8601 字符串，每个截图对象包含全部固定字段，`state` 和 `viewport` 属于本条目固定枚举，`path` 指向存在的 PNG 文件。
  - `make verify-visual CHECK=aesthetic-audit-record` 必须读取 `docs/spec/v0.2.0/visual-audit.md`，只有最终结论为 `通过` 时才通过。
  - `make verify-visual CHECK=legacy-frontend-removed` 必须同时检查源码和真实页面截图，不得只用文本搜索。
- 验收标准：
  - 生成 1440x900、1280x832、1200x800、1024x768、390x844 viewport 截图。
  - 覆盖首次空项目、新建项目、资料管理、资料健康度、纸页入库上传中、处理轨道运行中、处理失败修复入口、题目检索、来源置信层级、无可靠来源、专注模式、来源详情、PDF 页码导航、PDF 阅读视图、长列表、移动工作台。
  - 截图和 DOM 检查中无横向滚动、文本溢出、按钮溢出、关键区域重叠、空白主体和浏览器级无限纵向滚动。
  - 界面符合 Nature 论文式高级浅色自然系。
  - 界面参考成熟产品的信息密度、留白、排版、导航和状态处理方法，但没有复制特定产品的布局、文案、图标组合、品牌元素或可识别视觉资产。
  - 人工审美审计记录必须写明结论、问题和修复结果。
  - 审美审计结论必须为通过。
  - 审计人员必须明确确认旧前端设计不再影响 v0.2.0。
  - 视觉证据 manifest 和审计记录路径符合本条目契约。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 截图矩阵 | Node.js、pnpm、Playwright 浏览器、Linux、真实 Web、1440x900、1280x832、1200x800、1024x768、390x844 viewport | v0.2.0 UI 实现完成并准备固定 fixture 数据 | 执行 `make verify-visual CHECK=screenshot-matrix` | 所有主状态截图生成，且无布局硬错误 | 已落地真实 Playwright target，启动真实 Web、FastAPI、PostgreSQL、Redis/RQ 和固定 seed，生成 `tmp/v0.2.0-visual-evidence/manifest.json` 与 16 张 PNG 截图；截图覆盖 16 个固定状态和 1440x900、1280x832、1200x800、1024x768、390x844 五个固定 viewport，每张截图前执行布局硬错误检查 | `Makefile`、`frontend/e2e/v010.spec.ts`、`frontend/app/page.tsx`、`frontend/app/globals.css`、`tmp/v0.2.0-visual-evidence/manifest.json`、本地命令 `CHECK=screenshot-matrix make verify-visual` | 通过 |
| 人工审美审计 | 截图证据、真实浏览器、审计记录模板、subagent 工具 | 截图矩阵已生成 | 派发 subagent 严格审计；执行 `make verify-visual CHECK=aesthetic-audit-record` | 审计结论为通过；若失败则修复后复审 | 已落地真实 `aesthetic-audit-record` 校验 target，会读取固定 `docs/spec/v0.2.0/visual-audit.md` 结构并要求最终结论为 `结论：通过`；截图矩阵和人工审美审计记录尚未生成，target 当前按契约失败 | `Makefile`、`scripts/verify_visual_gate.py`、本地预期失败命令输出 | 阻塞 |
| 旧设计清除 | Node.js、pnpm、本地源码、真实运行页面、Linux | v0.2.0 前端实现完成 | 执行 `make verify-visual CHECK=legacy-frontend-removed` | 旧前端布局和视觉语言不再参与运行路径，旧组件、旧样式和旧页面结构已删除 | 已验证源码不包含旧演示文案和旧原型全局类；真实 Web 页面使用新工作台三分区运行路径，DOM 不包含旧原型类，并生成非空截图证据 | `frontend/e2e/v010.spec.ts`、`frontend/app/page.tsx`、`frontend/app/globals.css`、`tmp/v0.2.0-visual-evidence/1440x900-legacy-frontend-removed.png`、本地命令输出 | 通过 |
| 视觉硬错误 | Node.js、pnpm、Playwright 浏览器、Linux、真实 Web、截图证据 | 固定来源阅读 seed 可准备真实页面状态 | 执行 `make verify-visual CHECK=visual-hard-errors` | 无横向滚动、文本溢出、按钮溢出、关键区域重叠、空白主体或浏览器级无限纵向滚动 | 已落地真实 Playwright target，使用真实 Web、FastAPI、PostgreSQL 和固定来源 seed 覆盖 1440x900、1280x832、1200x800、1024x768、390x844；检查 `documentElement` 横向/纵向滚动、可见按钮溢出、标记文本溢出、标记关键区域重叠和 `main` 可见面积；移动端工作台已改为视口内三段滚动以消除浏览器级纵向滚动 | `Makefile`、`frontend/e2e/v010.spec.ts`、`frontend/app/globals.css`、本地命令 `CHECK=visual-hard-errors make verify-visual` | 通过 |
| 证据 manifest | Node.js、pnpm、Linux、本地证据文件 | 截图矩阵已生成 | 执行 `make verify-visual CHECK=visual-evidence-manifest` | `manifest.json` 包含每张截图的 URL、viewport、浏览器、Git commit、数据准备命令和截图时间 | 已落地并通过真实 `visual-evidence-manifest` 校验 target，校验 v0.2.0 版本、40 位 Git SHA、UTC 时间、截图 state/viewport 枚举、PNG 文件存在、元数据字段完整、16 个固定 state 全覆盖和 5 个固定 viewport 全覆盖 | `Makefile`、`scripts/verify_visual_gate.py`、`tmp/v0.2.0-visual-evidence/manifest.json`、本地命令 `CHECK=visual-evidence-manifest make verify-visual` | 通过 |

- 风险与回滚：视觉门禁包含主观判断。为降低争议，必须结合截图证据、明确禁区和人工审计记录；用户明确不满意时不得发布。

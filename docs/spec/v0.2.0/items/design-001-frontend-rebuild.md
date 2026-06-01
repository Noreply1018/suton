# 前端彻底重构与视觉系统

- 类型：设计优化
- 状态：草案
- 背景：v0.1.0 前端完成了最小闭环，但视觉粗糙、排版松散、信息堆叠明显，用户缺少继续使用的意愿。v0.2.0 必须把前端从原型重构为简约高效的复习工作台。
- 当前问题：旧前端视觉不高级，布局像技术验证页面，项目、资料、题目和结果被平铺堆叠；页面容易被列表拉长；默认项目名和演示感影响真实使用；首次空项目缺少直接、漂亮的开始入口。
- 目标行为：删除旧前端设计和旧布局影响，重新实现前端视觉系统。新 UI 必须采用 Nature 论文式高级浅色自然系，整体克制、清爽、适合长时间复习。用户进入应用后首先看到的是一个有明确当前项目、资料状态、题目检索和来源入口的工作台，而不是演示页面和长列表。首次空项目必须展示安静的工作台空态，主行动固定为“添加第一份课程资料”，不得用大段说明文字占据首屏。设计过程必须参考成熟产品的信息密度、留白、排版、导航和状态处理方法，但不得复制任何特定产品的布局、文案、图标组合、品牌元素或可识别视觉资产。
- 非目标：不包含营销落地页、品牌官网、复杂动效、3D 场景、深色主题、多主题切换。
- 发布必要性：必须发布
- 用户可见影响：用户看到全新的 Suton 工作台界面，旧版前端视觉和排版不再出现。
- 涉及模块：前端页面、前端组件、样式系统、Playwright 截图验证、文档。
- 配置、接口或数据结构变化：无直接后端接口要求；如实现需要调整前端路由或组件结构，必须保持核心 API 行为可用。
- 兼容性要求：必须保持 v0.1.0 核心后端闭环可用；不要求兼容 v0.1.0 前端 DOM、CSS 类名或组件结构。
- 视觉系统契约：
  - 前端实现必须继续使用 Next.js、React、Tailwind CSS 和 `lucide-react`，不得引入新的 UI 组件库作为主视觉系统。
  - 颜色 token 固定为：页面背景 `#f7f6f1`，纸面背景 `#fffefa`，主文本 `#1f2933`，次级文本 `#667085`，弱文本 `#8a9488`，细线 `#d8ddd2`，主强调 `#2f6f4e`，主强调悬停 `#285f43`，浅强调底 `#e7f0e8`，警示 `#b54708`，错误 `#b42318`，信息 `#3b5b7a`。
  - 颜色实现必须通过 CSS custom properties 暴露上述 token，命名固定为 `--color-page-bg`、`--color-paper-bg`、`--color-text-main`、`--color-text-muted`、`--color-text-subtle`、`--color-line`、`--color-accent`、`--color-accent-hover`、`--color-accent-soft`、`--color-warning`、`--color-danger`、`--color-info`。
  - 页面根背景只能使用 `--color-page-bg`，主要内容面只能使用 `--color-paper-bg`；主强调色只能用于主按钮、当前选中、链接、图标和细线，不得作为整页背景或大面积渐变；错误、警示和信息色只用于状态。
  - 字体使用系统 sans 字体栈：`Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`；不得引入远程字体。
  - 字号固定为：页面标题 22px/30px，区块标题 16px/24px，正文 14px/22px，辅助文字 12px/18px，标签 11px/16px；不得使用 viewport 单位控制字号。
  - 字重固定为 400、500、600 三档；页面内不得使用 700 以上字重。
  - 圆角固定为：输入框、按钮、列表项和详情面板 6px；重复项卡片最大 8px；不得使用大圆角胶囊作为主要视觉语言。
  - 阴影只允许用于浮层和全屏详情层，固定为 `0 16px 40px rgba(31, 41, 51, 0.10)`；常规工作台区域不得依赖阴影分层。
  - 图标统一使用 `lucide-react`，线宽固定 1.75px；IconButton、Toolbar、ListRow 和 StatusPill 内图标固定为 16px；Dialog、Sheet、EmptyState 和一级区域标题旁图标固定为 18px；不可用手写 SVG 替代已有 lucide 图标。
  - 旧前端相关页面结构、演示文案、默认项目名、旧 CSS 类名和未被新工作台使用的组件必须删除；不得保留隐藏运行路径或源码死角。
- 组件契约：
  - 必须建立并使用统一的 Button、IconButton、TextInput、Textarea、Select、SegmentedControl、StatusPill、EmptyState、Dialog、Sheet、ListRow、Toolbar、ProgressRail、SourceResult、PdfReaderShell 组件。
  - 主要操作按钮只用于创建项目、上传资料、检索题目和确认危险操作；普通工具操作使用图标按钮并提供 `aria-label`。
  - 状态标签只能使用低饱和底色和文本，不使用亮色实心标签。
  - 空状态文案每个状态最多 2 行正文，正文每行不超过 28 个中文字符；首次空项目主行动文案固定为 `添加第一份课程资料`。
  - 表单错误展示在输入框下方；后端返回 `detail` 时必须原样展示 `detail`；前端本地校验只允许使用本条目固定文案：项目名为空展示 `请输入项目名称`，项目名超过 80 个字符展示 `项目名称不能超过 80 个字符`，题目为空展示 `请输入题目`，未选择文件展示 `请选择 PDF 文件`，非 PDF 文件展示 `仅支持 PDF 文件`。
- 旧前端清除契约：
  - v0.2.0 实现完成时，`frontend/app/page.tsx` 必须只渲染新工作台入口，不得保留 v0.1.0 长页面布局。
  - 新前端源码不得包含 `v0.1.0`、`演示项目`、`默认项目`、`Demo`、`placeholder project` 作为可见 UI 文案。
  - `frontend/app/globals.css` 中不得保留未被新组件使用的旧页面全局类；Tailwind utility 可以继续使用，但必须服务于新组件结构。
- 验收标准：
  - 旧前端页面设计、布局和样式不再参与运行路径。
  - 新前端不以 v0.1.0 页面为基础做局部换色。
  - 视觉基调符合 Nature 论文式高级浅色自然系，低饱和、清爽、克制。
  - 不使用厚重暗色、廉价渐变、紫蓝主导、卡片堆叠或默认 SaaS 模板感。
  - 字体、间距、对齐、按钮、输入框、列表、状态标签和空状态形成统一系统。
  - 新前端使用本条目固定颜色、字号、圆角、图标和组件契约。
  - 首次空项目展示简洁空态，主行动为“添加第一份课程资料”，不出现大段教学说明。
  - 参考成熟产品的设计质量，但不存在可识别抄袭对象。
  - 所有主页面在 `1440x900`、`1280x832`、`1200x800`、`1024x768`、`390x844` viewport 下无文本溢出、重叠或错位。
  - 人工审美审计结论为通过。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 旧前端清除 | Node.js、pnpm、真实浏览器、Linux、本地前端源码 | v0.2.0 前端实现完成 | 执行 `pnpm --filter @suton/web lint`；执行 `pnpm --filter @suton/web typecheck`；执行 `make verify-visual CHECK=legacy-frontend-removed` | 旧页面布局、样式和演示感不再出现，运行路径使用新工作台 UI | 未验证 | 待补充 | 阻塞 |
| 视觉系统验收 | Node.js、pnpm、Playwright 浏览器、Linux、1440x900、1280x832、1200x800、1024x768、390x844 viewport | 已启动真实 Web 应用并准备 `tests/fixtures/text-layer-material.pdf`、`tests/fixtures/question.txt`、`tests/fixtures/unmatched-question.txt` | 执行 `make verify-visual CHECK=visual-system` | 截图符合 Nature 论文式高级浅色自然系，未命中视觉禁区，且无溢出、遮挡或错位 | 未验证 | 待补充 | 阻塞 |
| 回归核心闭环 | Node.js、pnpm、Python、uv、真实 FastAPI、真实 PostgreSQL/pgvector、真实 Redis/RQ、DashScope `DASHSCOPE_API_KEY`、Linux、Playwright 浏览器 | 已执行 `make reset-demo` 和 `make migrate` | 执行 `make verify-e2e SCENARIO=v020-core-loop` | 新前端完成项目、资料、题目、来源结果闭环 | 未验证 | 待补充 | 阻塞 |
| 首次空项目 | Node.js、pnpm、Playwright 浏览器、Linux、真实 Web、390x844 和 1440x900 viewport | 已执行 `make reset-demo`，不存在项目和资料 | 执行 `make verify-e2e SCENARIO=v020-first-empty-project`；执行 `make verify-visual CHECK=first-empty-project` | 首屏展示简洁工作台空态，主行动为“添加第一份课程资料”，无大段说明文字 | E2E 已验证首次空工作台不使用默认项目名，展示“添加第一份课程资料”空态和空项目名称输入；视觉截图未验证 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、本地命令输出 | 阻塞 |
| 设计 token | Node.js、pnpm、本地前端源码、Linux | v0.2.0 前端实现完成 | 执行 `make verify-visual CHECK=design-tokens` | 固定 CSS custom properties、字号、圆角、阴影、图标尺寸和核心组件清单符合 spec，未引入主 UI 组件库 | 未验证 | 待补充 | 阻塞 |
| 旧文案清除 | Node.js、pnpm、本地前端源码、Linux | v0.2.0 前端实现完成 | 执行 `make verify-visual CHECK=legacy-copy-removed` | 源码和真实页面不再出现演示项目、默认项目、Demo 或 v0.1.0 可见文案 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：彻底重构前端可能引入功能回归。若新 UI 未通过核心闭环，不得回滚到旧设计并标记完成，必须修复新 UI 或调整 spec。

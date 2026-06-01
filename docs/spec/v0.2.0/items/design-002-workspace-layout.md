# 工作台信息架构与布局约束

- 类型：设计优化
- 状态：草案
- 背景：Suton 的主要使用动作是管理项目、管理资料、输入题目、查看来源。v0.1.0 将这些信息平铺在页面中，导致页面冗长、焦点分散。
- 当前问题：项目栏可以无限向下延伸，资料和结果也会把页面拉长；当前任务、当前项目和当前来源不够清楚。
- 目标行为：v0.2.0 固定采用工作台信息架构。桌面端为左侧项目导航、中间当前任务主工作区、右侧来源阅读区。移动端为底部三段导航：项目、检索、来源；来源阅读使用全屏详情层。项目列表、资料列表、题目历史和来源结果都必须在各自区域内部滚动，不得撑长整页。桌面端必须提供一键专注模式：入口固定在当前题目工具栏右侧，使用单个图标按钮触发；用户点击一次后，项目导航和资料管理区域收起，只保留当前题目、来源结果和 PDF 阅读；退出入口固定在专注模式顶部左侧，点击一次后恢复原工作台上下文。
- 非目标：不包含复杂多窗口、拖拽式自定义布局、用户自定义仪表盘。
- 发布必要性：必须发布
- 用户可见影响：用户在一个稳定工作台中完成复习操作，不再面对无限下拉页面。
- 涉及模块：前端布局、项目导航、资料列表、题目历史、来源结果、PDF 详情视图。
- 配置、接口或数据结构变化：无。
- 兼容性要求：布局变化不得破坏键盘输入、上传文件、打开来源和检索结果展示。
- 布局契约：
  - 桌面三列布局适用于 viewport 宽度 >= 1280px，高度 >= 720px；根容器高度固定为 `100dvh`，页面主体不得产生浏览器级纵向滚动。
  - 桌面端采用三列 CSS grid：左侧项目栏固定 248px，中间主工作区 `minmax(520px, 1fr)`，右侧来源阅读区固定 420px；列间分隔线使用 `#d8ddd2`。
  - 1200px 到 1279px 之间使用紧凑桌面布局：左侧项目栏 220px，右侧来源阅读区 360px，中间区域最小 480px。
  - 1024px 到 1199px 使用双栏布局：左侧项目栏 220px，中间主工作区占剩余宽度；来源阅读以覆盖式详情层打开。
  - 390px 到 1023px 使用移动布局：顶部只显示当前项目标题和当前状态，底部三段导航固定为 `项目`、`检索`、`来源`；来源阅读使用全屏详情层。
  - 390px 以下不是 v0.2.0 验证范围；实现不得主动阻断访问，但发布门禁只验证 390px 及以上。
  - 所有固定工具栏高度为 48px；底部移动导航高度为 56px；滚动区域高度必须通过 `min-height: 0` 和 `overflow: auto` 限定在各自 grid/flex 容器内。
- 区域契约：
  - 左侧项目栏包含项目列表、项目新建入口和当前项目统计；只有项目列表滚动，项目栏头部和新建入口固定。
  - 中间主工作区自上而下固定为当前项目标题栏、资料管理区、题目检索区、题目历史区；资料列表和题目历史分别在内部滚动。
  - 右侧来源阅读区固定包含来源结果列表、来源详情和 PDF 阅读壳；来源结果列表和 PDF 阅读内容分别在内部滚动。
  - 当前项目标题栏固定展示项目名称、`latest_status` 对应状态、`document_count` 和 `question_count`；状态文案固定为 `空项目`、`处理中`、`需处理`、`可检索`，分别对应 `empty`、`processing`、`failed`、`ready`。
  - 当前题目工具栏左侧固定展示当前题目文本；题目为空时展示 `输入题目开始检索`；右侧固定展示题目状态、检索范围入口和专注模式入口。
  - 题目状态文案固定为：无当前题目时展示 `未检索`；请求未完成时展示 `正在检索来源`；`questions.status = completed` 展示 `已找到来源`；`questions.status = no_reliable_source` 展示 `未找到可靠来源`；`questions.status = failed` 展示 `检索失败`。
  - 来源结果列表必须高亮当前来源；右侧来源阅读区顶部固定展示当前来源文件名、页码、置信层级和排序位置；未选择来源时展示固定空态标题 `选择来源查看 PDF`。
  - 当前题目工具栏高度固定 48px，右侧最后一个工具按钮为专注模式入口，`aria-label` 固定为 `进入专注模式`。
  - 专注模式桌面端隐藏左侧项目栏和中间资料管理区，布局固定为左侧题目与来源结果 420px、右侧 PDF 阅读 `minmax(640px, 1fr)`；退出按钮 `aria-label` 固定为 `退出专注模式`。
  - 退出专注模式后必须恢复进入前的当前项目、当前题目、来源选择、PDF 页码、检索范围和资料列表滚动位置。
  - 移动端底部导航切换不得重新发起题目检索或资料处理；只切换可见区域。
- 文本与溢出契约：
  - 项目名、文件名、题目文本和来源标题在列表中最多占两行，超过两行使用截断；详情视图中允许完整换行展示。
  - 任一 viewport 下不得出现横向滚动条；按钮文字不得溢出按钮边界。
  - 长列表验证数据固定为 20 个项目、20 份资料、20 道题目历史和 20 条来源结果。
- 验收标准：
  - 左侧项目区域固定高度并在内部滚动。
  - 资料列表、题目历史和来源结果均不得无限撑长页面。
  - 当前项目标题栏展示项目名称、状态、资料数量和题目数量。
  - 当前题目工具栏展示题目文本、固定题目状态文案、检索范围入口和专注模式入口。
  - 当前来源在来源结果列表中高亮，来源阅读区顶部展示文件名、页码、置信层级和排序位置。
  - 页面首屏不展示低价值大段说明文字。
  - 同一时刻只突出当前任务相关信息。
  - 桌面端提供一键专注模式，入口固定在当前题目工具栏右侧，使用单个图标按钮触发。
  - 专注模式进入后隐藏项目导航和资料管理区域，保留当前题目、来源结果和 PDF 阅读。
  - 专注模式退出入口固定在顶部左侧，点击一次后退出，退出后当前项目、题目、来源选择和 PDF 页码不丢失。
  - 移动宽度下使用底部三段导航和全屏来源详情层，不出现横向溢出。
  - 1440x900、1280x832、1200x800、1024x768 和 390x844 viewport 均符合本条目布局契约。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 长列表布局 | Node.js、pnpm、Playwright 浏览器、Linux、1440x900 和 390x844 viewport、真实 Web | 已通过 `make reset-demo` 准备空库，由测试场景创建 20 个项目、20 份资料记录、20 道题目历史 | 执行 `make verify-e2e SCENARIO=v020-long-lists`；执行 `make verify-visual CHECK=long-lists` | 页面整体高度不被列表无限拉长，项目列表、资料列表、题目历史和来源结果均在各自区域内部滚动 | 已使用真实 Web、真实 FastAPI 和真实 PostgreSQL seed 验证 20 个项目、20 份资料、20 道题目历史和 20 条来源结果均在各自区域内部滚动，桌面与移动无横向溢出，页面高度受控，并生成 1440x900 与 390x844 截图证据 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_long_lists.py`、`Makefile`、本地命令输出、`tmp/v0.2.0-visual-evidence/1440x900-long-lists.png`、`tmp/v0.2.0-visual-evidence/390x844-long-lists.png` | 通过 |
| 当前上下文字段 | Node.js、pnpm、Playwright 浏览器、Linux、真实 Web、真实后端、真实 PostgreSQL | 已选择项目，已处理 `tests/fixtures/text-layer-material.pdf`，已检索 `tests/fixtures/question.txt` 并打开来源详情 | 执行 `make verify-visual CHECK=current-context` | 项目标题栏展示项目名称、状态、资料数量和题目数量；题目工具栏展示题目文本、固定题目状态、检索范围入口和专注模式入口；来源列表高亮当前来源，阅读区顶部展示文件名、页码、置信层级和排序位置 | 已使用真实 Web、真实 FastAPI 和真实 PostgreSQL source reader seed 验证项目标题栏展示项目名称、`可检索` 状态、资料数量和题目数量；题目工具栏展示当前题目文本、`已找到来源`、检索范围入口和 `进入专注模式` 图标入口；点击来源后来源卡片高亮，阅读区顶部展示文件名、页码、排序位置和置信层级，并生成 1440x900 截图证据 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_source_reader.py`、`Makefile`、本地命令输出、`tmp/v0.2.0-visual-evidence/1440x900-current-context.png` | 通过 |
| 窄屏布局 | Node.js、pnpm、Playwright 浏览器、Linux、390x844 viewport、真实 Web | 已启动 Web 应用并准备固定 fixture 数据 | 执行 `make verify-visual CHECK=mobile-workspace` | 页面无横向溢出、遮挡、文本压缩失败或不可操作控件 | 已使用真实项目、资料、题目和来源 seed 在 390x844 viewport 生成移动工作台截图，验证项目区、检索区、来源区、资料库、来源卡片和关键按钮可见，页面无横向溢出且可见按钮文字不溢出 | `frontend/e2e/v010.spec.ts`、`scripts/seed_source_reader.py`、`tmp/v0.2.0-visual-evidence/390x844-mobile-workspace.png`、本地命令输出 | 通过 |
| 专注模式 | Node.js、pnpm、Playwright 浏览器、Linux、1440x900 viewport、真实 Web | 已选择项目，已处理 `tests/fixtures/text-layer-material.pdf`，已检索 `tests/fixtures/question.txt` 并打开来源详情 | 执行 `make verify-e2e SCENARIO=v020-focus-mode`；执行 `make verify-visual CHECK=focus-mode` | 当前题目工具栏右侧存在单个图标入口；点击一次进入专注模式后只保留当前题目、来源结果和 PDF 阅读；顶部左侧退出入口点击一次后恢复上下文 | 已使用真实 Web、真实 FastAPI 和真实 PostgreSQL source reader seed 验证 `进入专注模式` 单图标入口；进入后项目栏、项目上下文、资料管理、题目输入和题目历史隐藏，只保留当前题目工具栏、来源结果和 PDF 阅读；顶部左侧 `退出专注模式` 可见；退出后来源选择和 PDF 页码仍保留，并生成 1440x900 截图证据 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_source_reader.py`、`Makefile`、本地命令输出、`tmp/v0.2.0-visual-evidence/1440x900-focus-mode.png` | 通过 |
| 桌面断点 | Node.js、pnpm、Playwright 浏览器、Linux、1440x900、1280x832、1200x800、1024x768 viewport、真实 Web | 已准备固定 fixture 数据 | 执行 `make verify-visual CHECK=workspace-breakpoints` | 三列、紧凑桌面和双栏布局按固定断点生效，页面主体无浏览器级纵向滚动 | 已使用真实 Web、真实 FastAPI 和真实 PostgreSQL source reader seed 验证 1440x900 与 1280x832 使用 248px / `minmax(520px, 1fr)` / 420px 三列；1200x800 使用 220px / `minmax(480px, 1fr)` / 360px 紧凑三列；1024x768 使用 220px / 剩余宽度双栏且来源阅读区以 fixed 覆盖层打开，不占 grid 第三列；1024 下来源结果可点击并打开 PDF 阅读；四个 viewport 均无浏览器级横向或纵向滚动，并生成截图证据 | `frontend/app/globals.css`、`frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_source_reader.py`、`Makefile`、本地命令输出、`tmp/v0.2.0-visual-evidence/1440x900-workspace-breakpoints.png`、`tmp/v0.2.0-visual-evidence/1280x832-workspace-breakpoints.png`、`tmp/v0.2.0-visual-evidence/1200x800-workspace-breakpoints.png`、`tmp/v0.2.0-visual-evidence/1024x768-workspace-breakpoints.png` | 通过 |
| 专注模式恢复 | Node.js、pnpm、Playwright 浏览器、Linux、1440x900 viewport、真实 Web | 已选择项目、检索题目、打开来源详情并滚动资料列表 | 执行 `make verify-e2e SCENARIO=v020-focus-mode-restore` | 退出专注模式后项目、题目、来源、PDF 页码、检索范围和资料滚动位置保持不变 | 已使用真实 Web、真实 FastAPI 和真实 PostgreSQL long list seed 验证进入前设置指定资料范围、滚动资料列表并打开来源；退出专注模式后项目名称、当前题目、当前来源高亮、PDF 页码 meta、指定资料勾选和资料列表 `scrollTop` 均保持不变 | `frontend/app/page.tsx`、`frontend/e2e/v010.spec.ts`、`scripts/seed_long_lists.py`、`Makefile`、本地命令输出 | 通过 |

- 风险与回滚：工作台布局若过度复杂会降低实现速度。若出现风险，应减少视图数量，但不得回到长页面堆叠。

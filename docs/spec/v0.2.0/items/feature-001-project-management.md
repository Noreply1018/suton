# 项目管理完整化

- 类型：功能新增
- 状态：草案
- 背景：项目是 Suton 的课程或考试复习容器。v0.1.0 已支持项目创建，但缺少真实使用所需的命名、去重、重命名和删除能力。
- 当前问题：项目名称可能使用演示默认值，项目可以重名，项目不能改名，不能删除，项目列表会无限延伸。
- 目标行为：用户必须主动输入项目名称；同一工作区项目名称唯一；项目可以重命名和删除；项目列表在固定区域中展示并可滚动。项目删除采用硬删除：项目、资料、页面文本、chunk、embedding、题目、来源结果和上传文件一并删除；任一上传文件删除失败时项目删除失败并显示错误。
- 非目标：不包含项目归档、回收站、协作成员、权限、分享和云同步。
- 发布必要性：必须发布
- 用户可见影响：用户可以像管理真实课程一样管理项目，不再被演示默认值和重复项目干扰。
- 涉及模块：前端项目导航、项目创建/编辑/删除 UI、后端项目 API、数据库。
- 配置、接口或数据结构变化：项目接口必须支持重命名和删除；数据库必须约束同一工作区项目名称唯一。单用户版本将工作区固定为本地默认工作区。
- 兼容性要求：已有 v0.1.0 项目数据必须迁移到本地默认工作区；迁移按项目 ID 升序逐条处理项目名：`trim` 固定为 Python `str.strip()`；`base` 固定为对原名执行 `str.strip()` 后，若为空则替换为 `迁移项目 {id}`，再按 Python `str` Unicode code point 截断到前 80 个字符得到的字符串；若 `base` 已存在，则从 `n = 2` 开始生成后缀 `（迁移 {n}）`，候选名固定为 `base[:80 - len(suffix)] + suffix`，取第一个未被占用的候选名。`len` 固定为 Python `str` 的 Unicode code point 长度。
- 交互契约：
  - 首次进入空工作区时，不自动创建项目，不显示演示项目名；主行动固定为 `添加第一份课程资料`，点击后先要求用户输入项目名称。
  - 新建项目入口固定在左侧项目栏顶部，按钮文案为 `新建项目`；移动端项目页顶部使用同一文案。
  - 新建项目弹层只包含项目名称输入框、取消、创建三个控件；按 Enter 触发创建，按 Esc 关闭弹层且不创建项目。
  - 项目名称 trim 后最短 1 个字符，最长 80 个字符；超过 80 个字符时前端阻止提交并显示 `项目名称不能超过 80 个字符`，后端返回 HTTP 400，`detail` 固定为同一文案。
  - 项目重命名入口固定在当前项目标题右侧的更多菜单中，菜单项文案为 `重命名`；提交成功后项目列表选中项和主工作区标题必须同步更新。
  - 项目删除入口固定在当前项目标题右侧的更多菜单中，菜单项文案为 `删除项目`；点击后显示二次确认弹层，确认文案固定为 `删除项目及其全部资料`。
  - 删除确认弹层必须展示将删除的项目名称、资料数量和题目数量；确认按钮固定为危险样式，文案为 `确认删除`。
  - 当前项目删除成功后，若仍有其他项目，按 `updated_at DESC, id DESC` 选择第一个项目；若没有项目，回到首次空工作区状态。
  - 项目列表按 `updated_at DESC, id DESC` 排序；当前项目固定高亮；列表只在项目栏内部滚动。
- 接口与数据契约：
  - 项目接口字段、错误状态和 `detail` 文案以 `data-001-v020-model-api.md` 为准；本条目不得另行定义不同错误文案。
  - 项目删除必须使用 `data-001-v020-model-api.md` 定义的删除暂存区两阶段流程。
  - 项目名称唯一性以 `workspace_id = local-default` 和 trim 后名称为准；前端不得用大小写转换、拼音、编号或时间戳自动改名。
  - v0.1.0 迁移后的项目必须补齐 `workspace_id` 和 `updated_at`；迁移名称必须使用本条目兼容性要求中的逐条去重算法，最终名称长度不得超过 80 个字符。
- 验收标准：
  - 新建项目没有默认演示名称。
  - 项目名称不能为空。
  - 项目名称超过 80 个字符时前后端都拒绝创建和重命名。
  - 同一工作区内项目名称不能重复。
  - 项目可以重命名，重命名后列表和当前项目标题同步更新。
  - 项目可以删除，删除前必须二次确认。
  - 删除项目后项目、资料、页面文本、chunk、embedding、题目、来源结果和上传文件一并删除。
  - 任一上传文件删除失败时项目删除失败，数据库不得留下半删除状态。
  - 项目列表固定区域展示，不撑长页面。
  - 删除当前项目后选中项目或空工作区状态按本条目固定规则更新。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 新建项目 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已执行 `make reset-demo` 和 `make migrate` | 执行 `make verify-e2e SCENARIO=v020-project-create` | 项目创建成功，不出现演示默认名 | 未验证 | 待补充 | 阻塞 |
| 重名拦截 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已存在项目“高性能计算期末” | 执行 `make verify-e2e SCENARIO=v020-project-unique-name` | 页面提示名称重复，数据库不产生重名项目 | 未验证 | 待补充 | 阻塞 |
| 重命名与删除 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、本地文件系统、Linux、Playwright 浏览器 | 已存在包含资料和题目的项目 | 执行 `make verify-e2e SCENARIO=v020-project-rename-delete`；执行 `make verify-db CHECK=v020-project-hard-delete` | 名称更新成功；项目硬删除符合 spec；页面状态同步 | 未验证 | 待补充 | 阻塞 |
| 项目名称边界 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、Linux、Playwright 浏览器 | 已执行 `make reset-demo` 和 `make migrate` | 执行 `make verify-e2e SCENARIO=v020-project-name-limits`；执行 `make verify-api-contract CHECK=v020-project-name-limits` | 空名称、超长名称和重复名称均返回固定错误；合法 80 字符名称可创建 | 未验证 | 待补充 | 阻塞 |
| 删除后选择规则 | Node.js、pnpm、Python、uv、真实 Web、真实 FastAPI、真实 PostgreSQL、本地文件系统、Linux、Playwright 浏览器 | 已存在 3 个项目且当前项目不是排序第一项 | 执行 `make verify-e2e SCENARIO=v020-project-delete-selection` | 删除当前项目后按 `updated_at DESC, id DESC` 选中下一个项目；无项目时进入首次空工作区 | 未验证 | 待补充 | 阻塞 |
| 重名项目迁移 | Python、uv、真实 PostgreSQL、Linux、v0.1.0 样例数据 | 已准备同名项目、空名项目和超过 80 字符项目 | 执行 `make migrate`；执行 `make verify-db CHECK=v020-project-name-migration` | 项目按 ID 升序使用固定 trim、空名替换、80 字符截断和后缀去重算法生成唯一名称 | 未验证 | 待补充 | 阻塞 |

- 风险与回滚：删除项目涉及级联数据。实现前必须固定删除语义；若语义未固定，不得开始实现。

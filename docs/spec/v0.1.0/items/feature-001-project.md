# 项目创建与项目页

- 类型：功能新增
- 状态：已完成
- 背景：Suton 以课程或考试复习任务为组织单位。用户需要先创建项目，再在项目中上传资料、输入题目并查看资料依据。
- 当前问题：没有项目容器时，资料、题目和检索结果无法形成清晰边界。
- 目标行为：用户可以创建一个项目，并在项目页看到该项目的资料数量、题目数量、最近处理状态和核心入口。
- 非目标：不包含多项目协作、项目成员权限、项目分享、项目归档、项目删除恢复。
- 发布必要性：必须发布
- 用户可见影响：用户进入 Web App 后可以创建项目，并从项目页进入资料上传、题目输入和查依据流程。
- 涉及模块：前端项目页、后端项目 API、数据库。
- 配置、接口或数据结构变化：新增 `projects` 数据对象；新增项目创建和项目查询接口。
- 兼容性要求：无特殊要求。
- 验收标准：
  - 用户可以创建项目。
  - 项目名称不能为空。
  - 创建后项目出现在项目列表或当前项目区域。
  - 项目页展示资料数量、题目数量和最近处理状态。
  - 项目页提供进入资料上传、题目输入和结果查看的入口。
- 验证矩阵：

| 场景 | 环境 | 前置条件 | 操作命令 | 预期结果 | 实际结果 | 证据 | 结论 |
|---|---|---|---|---|---|---|---|
| 正常创建项目 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector；关键变量 `DATABASE_URL` 存在 | 已执行 `make reset-demo` 和 `make migrate`，数据库为空或已清理测试项目 | 执行 `make dev`；在浏览器打开本地 Web；点击“新建项目”；输入“高等数学（上）期末复习”；提交；执行 `make verify-db CHECK=project-created PROJECT_NAME="高等数学（上）期末复习"` | 页面显示新项目，数据库存在对应 `projects` 记录 | 已验证：浏览器创建项目成功，数据库存在项目记录 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make verify-e2e` 与 `SCENARIO=minimal-loop make verify-e2e` 通过 | 通过 |
| 空名称拦截 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector | 已执行 `make dev` 并打开新建项目入口 | 清空项目名称；点击提交；执行 `make verify-db CHECK=project-count-unchanged` | 页面提示名称不能为空，数据库不新增项目 | 已验证：页面提示项目名称不能为空，数据库不存在空名称项目 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`project-validation` 场景通过；`make verify-db CHECK=project-count-unchanged` 通过 | 通过 |
| 项目页统计 | v0.1.0 验证环境基线：记录 `make env-info` 输出；真实浏览器；真实后端；真实 PostgreSQL/pgvector | 已创建项目，且至少有一份资料记录或题目记录 | 执行 `make dev`；打开项目页；执行 `make verify-db CHECK=project-summary PROJECT_NAME="高等数学（上）期末复习"` | 页面展示资料数量、题目数量和处理状态，数值与数据库一致 | 已验证：最小闭环项目展示 1 份资料、1 道题和完成状态，数据库统计一致 | `docs/spec/v0.1.0/validation-2026-05-29.md`；`make verify-db CHECK=project-summary ... EXPECT_DOCUMENT_COUNT=1 EXPECT_QUESTION_COUNT=1` 通过 | 通过 |

- 风险与回滚：项目模型过早复杂化会拖慢 v0.1.0。若实现时范围膨胀，应保留单用户、基础项目模型，移除协作和权限相关字段。

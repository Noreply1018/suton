# Suton v0.2.0 视觉审计记录
## 审计元信息

- 审计人：Codex subagent 只读人工审美审计。
- 审计时间：2026-06-02T08:04:43+08:00。
- HEAD：94116a45eec99c4e9e5a6eae3bf4b9b0891ed3e7。
- 证据路径：`tmp/v0.2.0-visual-evidence/manifest.json`、`tmp/v0.2.0-visual-evidence/contact-sheet.png`、`tmp/v0.2.0-visual-evidence/*.png`。
- 已通过前置命令：`CHECK=screenshot-matrix make verify-visual`、`CHECK=visual-evidence-manifest make verify-visual`。

## 截图矩阵结论

manifest 与当前 HEAD 一致，截图矩阵覆盖 16 个固定状态：`first-empty-project`、`project-created`、`document-list`、`document-health`、`paper-ingest-uploading`、`processing-rail-running`、`processing-failure-actions`、`question-search`、`source-confidence-levels`、`no-reliable-source`、`focus-mode`、`source-detail`、`source-page-nav`、`pdf-reader`、`long-lists`、`mobile-workspace`。

截图矩阵整体覆盖 5 个固定 viewport：`1440x900`、`1280x832`、`1200x800`、`1024x768`、`390x844`。该覆盖方式符合 `gate-001` 当前契约：每个 state 至少一张截图，整体覆盖全部 viewport，不要求 16x5 全笛卡尔积。

整体视觉判断为通过。界面呈现浅色自然系、低饱和绿色、纸面网格、克制边框与清晰信息密度，整体接近“Nature 论文式高级浅色自然系”的方向。未发现厚重暗色背景、紫蓝主导渐变、彩虹进度条、大面积玻璃拟态、装饰性渐变球、营销 hero、无意义插画、默认 SaaS 卡片堆叠或可识别第三方产品布局复制。旧前端视觉语言未在截图矩阵中形成影响。

## 问题列表

无阻断问题。

非阻断观察点：

1. 部分 seed 生成的长项目名在桌面和移动截图中显得较重，例如来源详情、长列表、移动工作台状态。当前已有截断和换行处理，未造成阻断级溢出或遮挡；后续若真实用户长标题较多，可继续优化标题压缩策略。
2. 来源阅读和空状态右侧区域在部分截图中保留较大空白。这符合工作台阅读区和 PDF 容器的功能预期，不构成低价值空白阻断；后续可通过更细的空状态层级继续提升感知密度。
3. 移动截图中左下角圆形浮动控件在长列表、无可靠来源等状态较醒目，视觉上会与内容竞争注意力。当前未遮挡核心文本、按钮或状态，不构成阻断。
4. 整体色彩偏单一绿色系，但仍处于浅色自然、克制、长期使用友好的范围内，未落入禁区中的紫蓝渐变或装饰化视觉。

## 修复记录

本次人工审美审计不要求主线程修复。当前截图证据支持创建本审计记录。

## 最终结论
结论：通过

本结论仅覆盖本次人工审美审计，不代表 v0.2.0 全部发布门禁完成。

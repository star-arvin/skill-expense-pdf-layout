---
name: skill-expense-pdf-layout
description: Use when arranging expense PDFs for A4 printing.
license: MIT
metadata:
  title: 报销材料分类与 A4 拼版
  version: "1.0.0"
  author: star-arvin
  tags: pdf, expense, invoice, printing
  compatibility: Python 3.10+ with PyMuPDF 1.x on macOS, Windows, or Linux.
---

# 报销材料分类与 A4 拼版

## 一、技能定位

本技能面向需要整理报销打印材料的办公人员。它先识别文件用途，再优先按同类型、日期顺序把两个材料上下排到一张 A4 纸；与普通 PDF 合并工具相比，它会把铁路客票和字体风险页完整截图后等比放置，避免文字层替换造成票面差异。

## 二、技术栈约束

- Python 3.10、3.11 或 3.12。
- PyMuPDF 1.x、PyYAML 6.x。
- 输入仅限本地 PDF、PNG、JPEG；核心流程不依赖 Codex、Cursor 或其他单一宿主 SDK。
- 输出为纵向 A4 PDF 和 JSON 清单；源文件只读且必须保持哈希不变。

## 三、核心能力

- **检查与分类**：输入文件夹，输出铁路客票、住宿发票、交通发票、行程单、报销单、普通发票或待确认类型。
- **分组与排序**：同类型优先，按业务日期、开票日期、文件名稳定排序；有证据时才跨类型配对。
- **安全拼版**：每页最多两个材料，上下结构、8 mm 边距、全程等比缩放。
- **票面保真**：铁路客票和字体风险页按不低于 300 DPI 整页截图，不重建文字。
- **结果验证**：检查 A4 尺寸、页数、源文件哈希和输入到输出的映射。
- **打印边界**：只有用户明确要求打印时才提交打印任务；默认意图是一份、A4、单面、黑白。

## 四、使用指南

当用户提出“整理报销材料”“两张发票放一页”“铁路客票按截图排版”或“生成可打印 A4 PDF”时使用本技能。

1. 只读检查输入文件夹，先运行 `python scripts/layout_expense_documents.py ./sample-input --output ./expense-layout.pdf --dry-run`。
2. 如有 `unclassified`、加密文件或不支持格式，停止并请用户确认，不生成可能误导的最终文件。
3. 核对分组后去掉 `--dry-run` 生成 PDF 与清单。
4. 检查输出页数、A4 尺寸、清单映射和源文件哈希。
5. 创建 PDF 不等于打印；打印必须再次确认是用户的明确请求。

完整命令、预期输出和故障处理见[快速开始](./references/guides/getting-started.md)。

## 五、最佳实践

- 始终先 dry-run，再写入结果。
- 铁路客票使用 `auto` 或 `raster`，不要从 PDF 文本层重排票面。
- 不为填满页面而臆测关联；无法配对的材料只放上半页。
- 不覆盖源文件；结果放到新的文件名，并保留清单。
- 不在日志或清单中复制姓名、证件号、税号、地址或票面全文。
- 打印前检查系统实际选择的打印机、A4、单面和黑白能力。

更多说明见[最佳实践](./references/guides/best-practices.md)和[隐私规范](./references/standards/privacy.md)。

## 六、参考资料

- [参考资料索引](./references/README.md)：按任务选择需要加载的规则。
- [分类规范](./references/standards/classification.md)：类型、证据和待确认条件。
- [排版规范](./references/standards/layout.md)：A4 几何、配对和渲染要求。
- [配置模板](./references/templates/layout-config.yaml)：明确覆盖少量已确认类型。
- [使用指南](./docs/skill-guides/skill-expense-pdf-layout/index.md)：触发方式、输入输出和对话示例。
- [Agent Skills 规范](https://agentskills.io/specification)：跨宿主目录与元数据标准。
- [PyMuPDF 文档](https://pymupdf.readthedocs.io/)：PDF 检查和渲染 API。

## 变更日志

### v1.0.0 (2026-09-01)

- 初始发布：分类、同类优先配对、两联 A4 拼版、铁路客票截图保真、清单和隐私检查。


# Expense PDF Layout Agent Skill

一个跨宿主的 Agent Skill：识别本地报销材料，优先把同类型文件按日期排序，并将两个材料以上下结构等比排到一张纵向 A4 纸。铁路电子客票及字体风险页先按整页图像渲染，再进行排版，避免文字重建造成票面差异。

## 功能

- 支持 PDF、PNG、JPEG。
- 识别铁路客票、住宿发票、交通发票、行程单、报销单和普通发票。
- 同类型优先配对；有关联证据时支持行程单与交通发票、报销单与发票配对。
- 每张 A4 最多放两个材料，8 mm 边距，保持原始比例。
- 生成 PDF 和不含票面正文的 JSON 映射清单。
- 源文件只读；生成前后验证 SHA-256。

## 安装

克隆到开放 Agent Skills 通用目录：

```bash
git clone https://github.com/star-arvin/skill-expense-pdf-layout.git \
  .agents/skills/skill-expense-pdf-layout
cd .agents/skills/skill-expense-pdf-layout
python -m pip install -e .
```

- Cursor 可直接发现 `.agents/skills/`，也可使用 `.cursor/skills/` 或从 GitHub 导入。
- Work Buddy 可把同一目录投射到项目的 `.agents/skills/`。
- Codex 及其他兼容 Agent Skills 的工具使用同一份 `SKILL.md`；`agents/openai.yaml` 只是可选界面元数据。
- 不使用智能体时，也可直接运行下方脚本。

## 快速使用

先预览分类和分组，不写 PDF：

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf \
  --dry-run
```

确认后生成：

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf
```

输出包括 `expense-layout.pdf` 和 `expense-layout.manifest.json`。更完整的步骤见[快速开始](references/guides/getting-started.md)。

## 安全边界

工具不会修改源文件、上传材料、填写报销系统或自动发起打印。打印是独立动作，只有用户明确提出时才执行；默认打印意图为一份、A4、单面、黑白。

## 开发与验证

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python scripts/validate_skill.py .
```

支持 Python 3.10–3.12，以及 macOS、Windows 和 Linux。项目采用 [MIT License](LICENSE)。


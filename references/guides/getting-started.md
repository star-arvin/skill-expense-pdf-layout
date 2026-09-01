# 快速开始

最后更新：2026-09-01

## 1. 准备环境

需要 Python 3.10–3.12。进入技能目录后安装：

```bash
python -m pip install -e .
```

## 2. 准备输入

把 PDF、PNG 或 JPEG 放入 `./sample-input`。输入目录只放本次需要处理的材料，不要把结果 PDF 放进去。

示例目录包含：

```text
sample-input/
├── railway-ticket-01.pdf
├── railway-ticket-02.pdf
├── accommodation-01.pdf
├── accommodation-02.pdf
├── itinerary-01.pdf
└── transport-invoice-01.pdf
```

## 3. 预览分类与分组

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf \
  --dry-run
```

预期返回三页规划：两张铁路客票一页、两张住宿发票一页、行程单与对应交通发票一页。dry-run 不生成 PDF。

如果返回 `unclassified`，先核对该文件，再通过文件名或[配置模板](../templates/layout-config.yaml)明确覆盖。不要猜测。

## 4. 生成结果

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf
```

成功后生成：

- `expense-layout.pdf`：纵向 A4，每页一至两个材料。
- `expense-layout.manifest.json`：文件名、源哈希、类型、输出页、位置和渲染方式。

## 5. 验证

```bash
python -m pytest -q
python scripts/validate_skill.py .
```

运行结果应无失败。打开生成的 PDF，重点检查铁路客票是否为完整票面截图、文字和二维码是否没有被裁切。

## 常见问题

### 输出已存在

默认拒绝覆盖。确认旧文件可以替换后再添加 `--overwrite`，或使用新的输出文件名。

### 铁路客票文字与原件不同

使用 `--render-mode raster --dpi 300` 重新生成，并确认源文件本身可以正常显示。截图模式把完整页面当成一个图像对象，不读取文本重建票面。

### 文件无法识别

先运行 `python scripts/inspect_expense_documents.py ./sample-input`。如仍无法确认，让用户指定类型；不要仅凭开票方或单位名称判断。


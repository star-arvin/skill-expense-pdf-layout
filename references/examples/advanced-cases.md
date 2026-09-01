# 进阶案例

最后更新：2026-09-01

## 案例一：混合文件夹与人工覆盖

### 场景

输入目录同时包含铁路客票、住宿发票、交通发票、行程单和一张扫描件。扫描件没有可提取文字，但用户已经查看原件并确认它是报销单。

> 用户：扫描件我已经核对过，是报销单。其余材料请自动分类并排版。
>
> AI：我会把该文件名写入本地配置的精确类型覆盖，其余文件仍按内容证据分类。先 dry-run 展示所有分组，确认无待分类项后再生成。

配置示例：

```yaml
type_overrides:
  sample-form-scan.pdf: reimbursement-form
```

执行：

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf \
  --config ./layout-config.yaml \
  --dry-run
```

### 技术难点

覆盖只改变分类标签，不修改文件内容。配置必须按 basename 精确匹配，防止把覆盖错误应用到其他文件。

## 案例二：全部强制截图

### 场景

一批 PDF 来自不同系统，字体嵌入情况不一致，需要把外观一致性放在文件体积之前。

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf \
  --render-mode raster \
  --dpi 300
```

### 技术难点与优化

- 强制截图可以避开字体替换，但会增加内存和输出体积。
- 先按批次拆分大目录，避免一次处理过多高分辨率页面。
- 300 DPI 通常足够打印；只有细小票面内容确实不清晰时才提高 DPI。


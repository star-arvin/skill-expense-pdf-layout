# 快速入门案例：两张铁路客票

最后更新：2026-09-01

## 业务背景

用户有两张同一差旅行程的铁路电子客票，希望在一张 A4 上下排列，并确保票面文字、二维码和版式不因 PDF 字体层而变化。

> 用户：把 `./sample-input` 里的两张铁路电子客票整理成一张 A4，先不要打印。
>
> AI：我会先只读识别并预览分组；两张客票将分别按完整页面截图，以不低于 300 DPI 等比放入同一张 A4 的上、下区域。确认后只生成新 PDF 和映射清单，不修改源文件，也不提交打印任务。

## 完整执行

```bash
python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf \
  --dry-run

python scripts/layout_expense_documents.py ./sample-input \
  --output ./expense-layout.pdf
```

## 预期结果

- 一张纵向 A4。
- 两个铁路票面图像对象，上下排列并保持比例。
- 页面没有重建的客票文字层。
- 清单包含两个输入文件、源哈希和对应槽位。

## 注意事项

如 dry-run 出现未分类文件，先停止并核对。不要为了完成版面而强制归类。


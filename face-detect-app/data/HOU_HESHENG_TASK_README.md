# 侯贺升测试素材整理交付说明

本目录中的交付物用于对应侯贺升后续任务：现有测试素材整理、图片清洗去重、测试样例管理与验收记录支持。本轮不处理公开数据集下载、TICaM、SVIRO 或 AI 图片来源说明。

## 交付文件

- `dataset_manifest.csv`：测试数据清单，盘点 `samples/`、`uploads/`、`results/` 和整理后的 `curated/` 图片。
- `cleaning_report.csv`：图片清洗与去重报告，标记可读性、格式、尺寸、SHA256、感知哈希、重复关系和处理建议。
- `acceptance_test_records.csv`：验收测试记录模板，素材侧信息已填写，实际检测结果等待后端接口稳定后补充。
- `curated/`：整理后的测试样例副本，只复制图片，不移动或删除原始图片。
- `rename_map.csv`：图片重命名映射表，记录每张图的原路径、新路径、类别和重命名原因。

## 重新生成

在项目根目录执行：

```bash
python face-detect-app/tools/prepare_hou_dataset.py
```

脚本只扫描现有图片并生成报告，不删除任何文件。

如需重新执行图片统一命名，在项目根目录执行：

```bash
python face-detect-app/tools/rename_data_images.py
```

重命名脚本采用两阶段改名并做冲突检查，只处理 `face-detect-app/data/` 下的图片。

## 字段说明

`dataset_manifest.csv` 中无法确认的人数和座位统一填写为 `unknown`，避免硬编标准答案。`cleaning_report.csv` 的 `action` 字段仅使用 `keep`、`review`、`exclude`，其中 `exclude` 只是报告建议，不代表脚本已删除文件。

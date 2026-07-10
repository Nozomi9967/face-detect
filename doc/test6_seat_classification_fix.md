# test6.png 座位分类 — 更新说明

> **更新说明（当前代码状态）**：本说明撰写时检测后端为 Haar Cascade（YOLOv8-face 未部署）。当前 `backend/yolov8n-face-lindevs.pt` 已存在，detector 默认优先加载 YOLOv8-face，仅在模型缺失或 ultralytics 未安装时回退 Haar。文中"多维评分优先 + 2-means 聚类兜底"算法已在 `seat_classifier.py` 中实现并适用，端到端验证现可用 YOLOv8-face 完成；下方"Haar 环境"下的实测数据保留为历史记录。

## 原问题（已修复）

原 test6 场景：3 人（副驾女士、主驾男士、后排老人），相机在后排乘客后方近距离拍摄。旧算法使用纯 Y-center 聚类，无法区分前排和后排近景的大脸。

**原错误输出**：5 张检测（含误检），座位分类全部错误，前排被误判为后排。

## 当前状态

### 修复内容

1. **新增多维评分优先策略** (`_front_candidates_by_position`)：对 3+ 人脸场景，基于 X偏移×0.35 + 宽度×0.45 + 面积×0.20 + Y位置×0.12 打分。前排人脸通常在画面两侧且更大。
2. **三人后排横向排布保护**：正好 3 人且 Y 集中、两侧不比中间大 → 直接判定后排。
3. **保留 2-means 聚类作为兜底**：多维评分失败时，使用 weighted [height, 3×Y-center] 聚类，辅以 tallest-in-back 翻转、Y偏离修正、高度比修正、全后排检测。

### 实际输出（Haar Cascade）

```
Faces: 5 (含 2 个 Haar 误检)
  Face 1: seat=posterior_left,  nx=0.067, ny=0.395  ← 可能为误检
  Face 2: seat=co_driver,       nx=0.282, ny=0.421  ← 副驾女士 ✓
  Face 3: seat=posterior_right, nx=0.497, ny=0.427  ← 后排老人 ✓
  Face 4: seat=after_the_middle,nx=0.610, ny=0.727  ← 可能为误检
  Face 5: seat=master_driver,   nx=0.722, ny=0.368  ← 主驾男士 ✓
```

3 个真实座位（co_driver, posterior_right, master_driver）均被正确分类。

### 算法流程（3+ 人脸）

```
n >= 3:
  1. _front_candidates_by_position():
     - 3人保护检查（y_span < 0.08 且两侧不比中间大）
     - 评分打分，两侧各选 best，需满足 plausible_front
     - 两侧都通过 → 判定前排
     - 返回空集 → 进入 b)

  2. Y集中(y_span < 0.06) → 宽度分层

  3. 2-means 聚类 (n >= 3, Y有分层):
     - weighted [height, 3×Y-center]
     - tallest-in-back 翻转
     - Y偏离修正 (|Y - 簇中心| > 0.06 → 移出)
     - 高度比修正 (front max/min > 2.0 → 移除较矮者)
     - 全后排检测
```

## 文件状态

| 文件 | 状态 |
|------|------|
| `seat_classifier.py` | ✅ 多维评分 + 2-means 两级策略已实现 |
| `pipeline.py` | ✅ similarity_threshold 存为实例变量 |
| `data/HOU_HESHENG_TASK_README.md` | ✅ 数据集整理交付说明 |

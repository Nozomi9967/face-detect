# Seat Classifier 算法说明

> 本文档描述座位分类算法 (`_is_front_row`) 的设计原理和关键逻辑。

---

## 算法架构

座位分类采用**多维评分优先 + 2-means 聚类兜底**的两级策略：

```
3+ 人脸场景
    │
    ├── 第一步：_front_candidates_by_position() 多维评分
    │   └── 成功（两侧都有足够大的候选）→ 直接判定
    │
    └── 第二步：2-means on [height, 3×Y-center] 聚类
        ├── tallest-in-back 翻转修正
        ├── Y偏离修正（|Y - 簇中心| > 0.06 → 移出）
        └── 高度比修正（front 内 max/min > 2.0 → 移除较矮者）

2 人脸场景：Y跨度 > 0.12 → 按Y高低；否则平均宽度 > 0.08

1 人脸场景：综合判断（宽度 + 面积 + 位置）
```

## 多维评分详情 (`_front_candidates_by_position`)

### 特征计算

对每个人脸计算四项归一化特征：
- **nx**: 人脸中心 X / 图片宽度 → 衡量左右偏移
- **ny**: 人脸中心 Y / 图片高度 → 衡量纵向位置
- **w**: 人脸宽度 / 图片宽度 → 人脸大小
- **area**: (宽×高) / (图片面积) → 人脸面积

### 评分公式

```
score = |nx - 0.5| × 0.35      # 靠边加分
      + w / max_w × 0.45       # 宽度越大加分
      + area / max_area × 0.20 # 面积越大加分
      + (ny >= median_y ? 0.12 : 0.0)  # Y位置偏下加分（弱信号）
```

### 三人后排横向排布保护

当正好3人时，额外检查：
- 左右两侧人脸宽度/面积与中间人的比值
- 如果 Y 跨度 < 0.08 且两侧比中间大不了多少（宽度比<1.35，面积比<1.55），判定为后排横向排布，返回空集

### 判定条件

- 左右两侧各选出评分最高的人脸
- 该人脸需要满足：`|nx-0.5| >= 0.12` 且（宽度 >= 中位数90% 或 面积 >= 中位数90%）
- 两侧都满足 → 判定为前排

## 2-means 聚类详情 (`_kmeans2`)

### 特征向量

`[normalized_height, 3 × normalized_Y_center]`

Y-center 加权 3 倍，因为纵向位置对排区分更可靠。

### 迭代过程

1. 以最高人脸和最低人脸为初始质心
2. 逐轮迭代分配（曼哈顿距离），最多 20 轮
3. 均值高的簇为前排

### 修正步骤

1. **tallest-in-back 翻转**：如果前排只有1人且后排出 >= 2 人中有比前排更高的脸 → 翻转
2. **Y偏离修正**：前排簇内人脸，其 Y-center 偏离簇中心 > 0.06 → 移入后排
3. **高度比修正**：前排内 max_height / min_height > 2.0 → 移除较矮者（后排近景误入）

### 全后排检测

如果前排簇包含 >= 2 人且其 Y-center 范围完全落在后排簇的 Y-center 范围内 → 判定为全后排

## 单人场景

```python
x1, y1, x2, y2 = bbox
nx = ((x1+x2)/2) / img_w
ny = ((y1+y2)/2) / img_h
width = (x2-x1) / img_w
area = width * (y2-y1) / img_h
front_sized = width >= 0.08 or area >= 0.010
side_position = |nx - 0.5| >= 0.18
lower_half = ny >= 0.28
return front_sized and (side_position or lower_half)
```

## 测试覆盖

| 用例 | 场景 | 关键特征 |
|------|------|----------|
| test1 | 2人全后排（远） | Y集中，宽度小 |
| test2 | 3人全后排（远） | Y集中，宽度小 |
| test3 | 5人全车（正常） | Y分层清晰，前排宽 |
| test3_抬高 | 5人全车（抬高） | Y分层更宽，前排宽 |
| **test4** | **3人混排（全后排但高度差大）** | Y分散但都在后排范围，高度比3.2x |
| test5 | 单司机 | 左侧大脸 |
| test6 | 3人全后排近景 | minY > 0.50（Signal1a触发） |

## 文件清单

| 文件 | 说明 |
|------|------|
| `seat_classifier.py` | 核心算法实现 |
| `pipeline.py` | 编排检测流程，存 `similarity_threshold` 为实例变量 |
| `data/HOU_HESHENG_TASK_README.md` | 数据集整理说明 |
| `tools/prepare_hou_dataset.py` | 数据集生成脚本 |
| `tools/rename_data_images.py` | 图片重命名脚本 |

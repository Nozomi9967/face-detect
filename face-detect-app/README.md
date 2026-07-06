# 多人脸采集素材自动化清洗

YOLOv8-face（优先）+ OpenCV Haar Cascade（fallback）+ InsightFace/像素特征（特征匹配）+ 规则座位分类的多人脸检测与素材清洗系统。

## 技术架构

| 模块 | 实现 | 说明 |
|------|------|------|
| 人脸检测 | YOLOv8-face / Haar Cascade | 优先YOLOv8，模型不可用时自动降级到Haar |
| 特征匹配 | InsightFace ArcFace / 像素直方图 | 优先ArcFace 512维，不可用时用像素统计特征 |
| 座位分类 | 坐标规则引擎 | 基于人脸框中心点坐标的5区域划分 |
| 后端服务 | FastAPI + Uvicorn | RESTful API + 静态文件服务 |
| 前端界面 | HTML5 + CSS3 + Vanilla JS | 响应式移动端适配 |

## 项目结构

```
face-detect-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 服务入口
│   │   ├── detector.py      # YOLOv8-face / Haar Cascade 人脸检测
│   │   ├── recognizer.py    # InsightFace / 像素特征 人脸匹配
│   │   ├── seat_classifier.py # 座位区域规则分类 + 标注绘制
│   │   └── pipeline.py      # 检测流程编排
│   ├── requirements.txt
│   └── __init__.py
├── frontend/
│   └── index.html           # 移动端可视化页面
├── docs/
│   ├── 需求规格说明书.md
│   └── 概要设计文档.md
├── data/
│   ├── uploads/             # 上传图片
│   └── results/             # 检测结果
└── models/                  # 模型权重目录（可选）
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动服务

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 打开页面

浏览器访问 `http://localhost:8000`

### 4. 使用

- **单张检测**：上传一张图片，自动检测并标注人脸
- **批量清洗**：上传多张图片，跨图匹配同一人，生成统计报告

## 座位分类规则

| 座位ID | X范围 | Y范围 | 颜色 |
|--------|-------|-------|------|
| posterior_left | 0.00-0.33 | 0.00-0.50 | 红色 |
| posterior_right | 0.33-0.66 | 0.00-0.50 | 绿色 |
| after_the_middle | 0.66-1.00 | 0.00-0.50 | 蓝色 |
| co_driver | 0.00-0.50 | 0.50-1.00 | 橙色 |
| master_driver | 0.50-1.00 | 0.50-1.00 | 青色 |

## 测试结果

在5人合成测试图上：
- 检测准确率：5/5 (100%)
- 座位分类准确率：5/5 (100%)
- 处理耗时：~300ms (CPU)

## 技术栈

- **后端**: FastAPI + Uvicorn
- **人脸检测**: YOLOv8-face (ultralytics) / OpenCV Haar Cascade fallback
- **特征匹配**: InsightFace ArcFace (512维) / 像素统计特征 fallback
- **座位分类**: 坐标规则引擎
- **前端**: HTML5 + CSS3 + Vanilla JS (响应式移动端)

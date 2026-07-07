# 多人脸采集素材自动化清洗

YOLOv8-face（优先）+ OpenCV Haar Cascade（fallback）+ InsightFace/像素特征（特征匹配）+ 规则座位分类的多人脸检测与素材清洗系统。

## 技术架构

| 模块 | 实现 | 说明 |
|------|------|------|
| 人脸检测 | YOLOv8n-face (lindevs, 6MB) | 优先模型，检测精度高；置信度阈值默认 0.1 |
| 特征匹配 | InsightFace ArcFace (buffalo_l) | 512维特征，跨图匹配同一人（可选，CPU较慢） |
| 座位分类 | 坐标规则引擎 | 5区域划分，自适应前后排判断（Y坐标+宽度聚类） |
| 后端服务 | FastAPI + Uvicorn | RESTful API + 静态文件服务 |
| 前端界面 | HTML5 + CSS3 + Vanilla JS | 响应式移动端适配 |
| 中文标注 | PIL + simhei.ttf | OpenCV不支持中文，用PIL渲染 |
| Android客户端 | WebView + JsBridge | 原生Android封装 |

## 项目结构

```
face-detect-app/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 服务入口
│   │   ├── detector.py      # YOLOv8-face / Haar Cascade 人脸检测
│   │   ├── recognizer.py    # InsightFace / 像素特征 人脸匹配
│   │   ├── seat_classifier.py # 座位区域规则分类 + PIL标注绘制
│   │   └── pipeline.py      # 检测流程编排
│   ├── requirements.txt
│   └── __init__.py
├── frontend/
│   ├── index.html           # 移动端检测页面（单张+批量）
│   └── setup.html           # 配网页面（二维码+手动输入）
├── android/                 # Android 原生客户端
│   ├── README.md
│   ├── build-debug.bat      # Windows 一键构建脚本
│   ├── app/
│   │   ├── build.gradle.kts
│   │   ├── src/main/        # Java 源码 + 资源
│   │   └── proguard-rules.pro
│   └── build.gradle.kts
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

配网页面（手机扫码）：`http://localhost:8000/setup`

### 4. 使用

- **单张检测**：上传一张图片，自动检测并标注人脸
- **批量清洗**：上传多张图片，跨图匹配同一人，生成统计报告
- **Android**：手机扫码连接服务器，使用原生App

## API 接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 前端页面 |
| GET | `/setup` | 配网页面 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/seat-zones` | 座位区域配置 |
| GET | `/api/server-info` | 服务器局域网地址 |
| POST | `/api/detect` | 单张图片检测 |
| POST | `/api/detect-batch` | 批量图片检测 |

### POST /api/detect 响应格式

```json
{
  "image_id": 0,
  "filename": "car_01.jpg",
  "num_faces": 3,
  "faces": [
    {
      "bbox": [120, 80, 200, 170],
      "conf": 0.92,
      "seat": "master_driver",
      "seat_label": "主驾",
      "person_id": 1
    }
  ],
  "annotated_image_base64": "data:image/jpeg;base64,...",
  "processing_time_ms": 2340.5
}
```

## 座位分类规则

座位分类采用自适应算法：根据人脸框位置和大小自动判断前后排，再按 X 坐标映射座位。参考区域如下：

| 座位ID | X范围 | Y范围 | 颜色 | 含义 |
|--------|-------|-------|------|------|
| posterior_left | 0.25-0.45 | 0.25-0.45 | 红色 | 后排左侧 |
| posterior_right | 0.45-0.65 | 0.25-0.45 | 绿色 | 后排中间 |
| after_the_middle | 0.65-0.90 | 0.25-0.50 | 蓝色 | 后排右侧 |
| co_driver | 0.00-0.40 | 0.30-0.55 | 橙色 | 前排左手边 |
| master_driver | 0.60-1.00 | 0.30-0.55 | 青色 | 前排右手边 |

前后排通过 Y 坐标 + 人脸宽度自适应判断，X 坐标三分区分后排左右。

## 标注显示

- 标注标签格式：`座位名称 ID:N`（如 `主驾 ID:1`）
- 使用 PIL + 中文字体绘制
- 置信度显示在标注框下方

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
- **标注**: PIL + 中文字体

## Android 移动客户端

将 Web 前端封装为原生 Android App，使用 WebView 加载页面，通过 HTTP 与后端通信。详见 [android/README.md](android/README.md)。

**构建方式**：
```bat
cd android
build-debug.bat
adb install app/build/outputs/apk/debug/app-debug.apk
```

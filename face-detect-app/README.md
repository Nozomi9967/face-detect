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

---

## 生产环境部署

### 服务器环境要求

- OS: Linux (CentOS / Alibaba Cloud Linux / Ubuntu)
- Python: >= 3.10
- Nginx: >= 1.18
- 内存: >= 4GB (建议 7GB+，YOLO 模型加载约需 600MB)
- 磁盘: >= 5GB (含模型文件)

### 服务架构

```
公网用户 (80端口)
  ├── http://<ip>/        → Nozomi-House (前端 SPA)
  └── http://<ip>/face/   → Face Detect 服务
```

Face Detect 通过 Nginx 反向代理共享 80 端口，路径前缀 `/face/`。后端 FastAPI 服务监听 `127.0.0.1:8000`，不对外暴露。

### 服务器目录结构

```
/opt/face-detect/                    # 项目根目录（Nginx 可读）
├── frontend/                        # 静态文件
│   ├── index.html                   # 检测主页面
│   └── setup.html                   # 配网页面
├── backend/                         # Python 后端
│   ├── venv/                        # Python 虚拟环境
│   ├── app/
│   │   ├── main.py
│   │   ├── detector.py
│   │   ├── recognizer.py
│   │   ├── seat_classifier.py
│   │   └── pipeline.py
│   └── requirements.txt
├── data/
│   ├── uploads/                     # 上传图片
│   └── results/                     # 检测结果
└── yolov8n-face-lindevs.pt         # 模型权重

/usr/share/nginx/html/face-detect/   # Nginx 前端文件（软链接或复制）
/etc/nginx/conf.d/nozomi.conf        # Nginx 配置（追加 face-detect 路由）
/etc/systemd/system/face-detect.service  # systemd 服务单元
```

### 部署步骤

#### 1. 克隆代码

```bash
git clone <repo-url> /opt/face-detect
cd /opt/face-detect
```

#### 2. 创建 Python 虚拟环境

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 配置 systemd 服务

文件 `/etc/systemd/system/face-detect.service`：

```ini
[Unit]
Description=Face Detect API Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/face-detect/backend
ExecStart=/opt/face-detect/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment="PYTHONUNBUFFERED=1"
Environment="PUBLIC_IP=<公网IP地址>"
Environment="BASE_PATH=/face"

[Install]
WantedBy=multi-user.target
```

```bash
mkdir -p /opt/face-detect/data/uploads /opt/face-detect/data/results
systemctl daemon-reload
systemctl enable face-detect
systemctl start face-detect
```

#### 4. 部署前端文件

```bash
mkdir -p /usr/share/nginx/html/face-detect
cp /opt/face-detect/frontend/* /usr/share/nginx/html/face-detect/
chmod 755 /usr/share/nginx/html/face-detect
chmod 644 /usr/share/nginx/html/face-detect/*
```

#### 5. 配置 Nginx

在现有 Nginx `server` 块末尾（`}` 之前）追加：

```nginx
# ---- Face Detect (port 8000) ----
location = /face/index.html {
    alias /usr/share/nginx/html/face-detect/index.html;
}
location = /face/setup.html {
    alias /usr/share/nginx/html/face-detect/setup.html;
}
location /face/ {
    alias /usr/share/nginx/html/face-detect/;
    index index.html;
    try_files $uri $uri/ =404;
}
location /face/api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    client_max_body_size 50M;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

```bash
nginx -t && systemctl reload nginx
```

#### 6. 验证

```bash
# 后端服务
curl http://127.0.0.1:8000/api/health
# → {"status":"ok","message":"多人脸检测服务运行中"}

# Nginx 前端
curl http://127.0.0.1/face/ | head -3
# → 应返回 HTML 页面

# Nginx API 代理
curl http://127.0.0.1/face/api/seat-zones
# → 返回 JSON 座位配置

# 确认原有服务不受影响
curl http://127.0.0.1/ | head -3
# → 应返回原有 Nozomi-House 页面
```

### 常用运维命令

```bash
# 查看服务状态
systemctl status face-detect

# 查看日志
journalctl -u face-detect -f

# 重启服务
systemctl restart face-detect

# 更新前端文件后同步
cp frontend/index.html /usr/share/nginx/html/face-detect/
systemctl reload nginx

# 更新后端代码后重启
cp backend/app/main.py /opt/face-detect/backend/app/main.py
systemctl restart face-detect
```

### 在线访问

| 服务 | 地址 |
|------|------|
| Face Detect 主页面 | `http://<服务器IP>/face/` |
| Face Detect 配网页 | `http://<服务器IP>/face/setup.html` |
| Nozomi-House（原有） | `http://<服务器IP>/` |

### 注意事项

- Nginx worker 进程以 `nginx` 用户运行，前端文件需放在 Nginx 可读的目录（如 `/usr/share/nginx/html/`），`/root/` 等目录无法访问
- `/face/api/` 路径下的请求会被 Nginx 代理到 FastAPI，前端 JS 中使用相对路径 `./api/` 而非绝对路径 `/api/`
- `PUBLIC_IP` 环境变量用于让 `server-info` 接口返回正确的公网地址，供配网页面使用
- 模型文件 `yolov8n-face-lindevs.pt`（约 6MB）需与代码同步到服务器

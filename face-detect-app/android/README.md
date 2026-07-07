# FaceDetect Android

Android 移动端应用，将多人脸采集素材自动化清洗系统封装为原生 App。

## 架构概览

```
FaceDetect Android/
├── MainActivity          # WebView 主界面，加载前端页面
├── SplashActivity        # 启动闪屏页
├── SettingsActivity      # 服务器地址配置页面
├── JsBridge              # JavaScript ↔ Java 通信桥
└── res/                  # 资源文件（布局、样式、颜色）
```

## 技术栈

| 组件 | 技术 |
|------|------|
| UI 层 | WebView + 原生 TouchFlow 风格资源 |
| 设计系统 | [TouchFlow DESIGN.md](DESIGN.md) |
| 后端通信 | HTTP REST API (FastAPI) |
| 最低 Android 版本 | 8.0 Oreo (API 26) |
| 目标版本 | Android 14 (API 34) |

## 快速开始

### 前置条件

- **Android SDK**: Platform 34 + Build-tools 34.0.0
- **JDK**: Java 11+
- **后端服务**: 需先启动 FastAPI 后端 (`python -m uvicorn backend.app.main:app`)

### 构建（Windows）

```bat
cd android
build-debug.bat
```

构建完成后 APK 位于 `android/app/build/outputs/apk/debug/app-debug.apk`。

### 部署与运行

#### 方式一：USB 连接真机

```bat
adb install android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.facedetect/.MainActivity
```

#### 方式二：Android Studio 导入

1. 打开 Android Studio → Open → 选择 `android` 目录
2. 等待 Gradle Sync 完成
3. 连接真机或启动模拟器
4. 点击 Run

### 配置服务器地址

首次启动后，点击 Toolbar 菜单 → 设置，输入后端服务地址：

```
http://<你的电脑IP>:8000
```

> **注意**: 默认 `10.0.2.2` 仅用于 Android 模拟器访问宿主机。真机需使用电脑的实际局域网 IP。

## 功能

- 拖拽 / 选择上传车辆内摄像头照片
- 实时显示检测结果（人脸框 + 座位分类 + 置信度）
- 单图 / 批量处理模式切换
- 座位区域图例与颜色标识
- 批量统计报表（人员出勤汇总）
- 中文字体标注支持

## 与后端配合

App 通过 HTTP 调用以下 API：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 加载前端页面 |
| `/api/detect` | POST | 单张图片人脸检测 |
| `/api/detect-batch` | POST | 批量图片检测 |
| `/api/health` | GET | 健康检查 |
| `/api/seat-zones` | GET | 座位区域配置 |

后端启动命令：
```bash
cd face-detect-app
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## 设计系统

本项目采用 **TouchFlow** 设计系统（来自 [designmd.ai/chef/touchflow](https://designmd.ai/chef/touchflow)），详见 [docs/DESIGN.md](DESIGN.md)。

设计特点：
- 手势优先、拇指友好
- 最小 44px 触摸目标
- 16px 圆角卡片
- 蓝/珊瑚/薄荷三色体系
- 1px-8px 层级阴影系统

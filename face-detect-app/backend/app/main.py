"""
多人脸检测API服务
FastAPI + 前端静态文件服务
"""

import os
import sys
import base64
import cv2
import numpy as np
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import socket
from pydantic import BaseModel
import uvicorn

# 将backend目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.pipeline import Pipeline

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RESULT_DIR = BASE_DIR / "data" / "results"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

# ── 初始化引擎 ─────────────────────────────────────────────
pipeline = Pipeline(detector_conf=0.1, similarity_threshold=0.5)

# ── FastAPI应用 ─────────────────────────────────────────────
app = FastAPI(
    title="多人脸采集素材自动化清洗",
    description="YOLOv8-face + InsightFace + 规则座位分类",
    version="1.0.0",
)

# 挂载前端静态文件
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")


# ── 数据模型 ───────────────────────────────────────────────
class FaceResult(BaseModel):
    bbox: list[float]
    conf: float
    seat: str
    seat_label: str
    person_id: int


class DetectionResponse(BaseModel):
    image_id: int
    filename: str
    num_faces: int
    faces: list[FaceResult]
    annotated_image_base64: str
    processing_time_ms: float


class SeatZoneConfig(BaseModel):
    """座位区域配置（可前端动态调整）"""
    zones: dict


# ── API路由 ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """前端主页"""
    index_path = BASE_DIR / "frontend" / "index.html"
    return index_path.read_text(encoding="utf-8")


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "多人脸检测服务运行中"}


@app.post("/api/detect", response_model=DetectionResponse)
async def detect_faces(file: UploadFile = File(...)):
    import time, traceback
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="无法解析图片文件，请上传JPG/PNG格式")

        ext = Path(file.filename).suffix or ".jpg"
        t0 = time.time()
        save_name = f"{int(t0*1000)}{ext}"
        save_path = UPLOAD_DIR / save_name
        cv2.imwrite(str(save_path), image)

        result = pipeline.process_image(image, image_id=0)
        elapsed_ms = (time.time() - t0) * 1000

        result_name = f"result_{save_name}"
        result_path = RESULT_DIR / result_name
        cv2.imwrite(str(result_path), result["annotated_image"])

        _, buf = cv2.imencode(".jpg", result["annotated_image"], [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buf).decode("utf-8")

        return DetectionResponse(
            image_id=result["image_id"],
            filename=file.filename,
            num_faces=result["num_faces"],
            faces=[FaceResult(**f) for f in result["faces"]],
            annotated_image_base64=f"data:image/jpeg;base64,{img_b64}",
            processing_time_ms=round(elapsed_ms, 1),
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/api/detect-batch")
async def detect_batch(files: list[UploadFile] = File(...)):
    """
    批量上传多张图片（用于素材清洗场景）
    返回所有图片的检测结果，并跨图匹配同一人ID
    """
    import time

    images = []
    filenames = []
    for f in files:
        contents = await f.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            images.append(img)
            filenames.append(f.filename)

    if not images:
        raise HTTPException(status_code=400, detail="未找到有效图片")

    t0 = time.time()
    results, annotated_imgs = pipeline.process_batch(images)
    elapsed_ms = (time.time() - t0) * 1000

    # 编码结果
    batch_results = []
    for i, (res, ann_img) in enumerate(zip(results, annotated_imgs)):
        _, buf = cv2.imencode(".jpg", ann_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buf).decode("utf-8")

        # 保存结果
        result_name = f"batch_{int(time.time()*1000)}_{i}.jpg"
        cv2.imwrite(str(RESULT_DIR / result_name), ann_img)

        batch_results.append({
            "image_id": i,
            "filename": filenames[i],
            "num_faces": res["num_faces"],
            "faces": res["faces"],
            "annotated_image_base64": f"data:image/jpeg;base64,{img_b64}",
        })

    return {
        "total_images": len(batch_results),
        "total_faces": sum(r["num_faces"] for r in batch_results),
        "processing_time_ms": round(elapsed_ms, 1),
        "results": batch_results,
    }


@app.get("/api/seat-zones")
async def get_seat_zones():
    """获取当前座位区域配置"""
    from app.seat_classifier import SEAT_ZONES, COLOR_MAP_RGB
    return {
        "zones": SEAT_ZONES,
        "colors": {k: list(v) for k, v in COLOR_MAP_RGB.items()},
    }


@app.get("/api/server-info")
async def server_info():
    """返回服务器地址，供手机配网页面获取"""
    import os
    public_ip = os.environ.get("PUBLIC_IP", "")
    port = int(os.environ.get("PORT", "80"))
    base_path = os.environ.get("BASE_PATH", "")
    if public_ip:
        host = f"http://{public_ip}" if port in (80, 443) else f"http://{public_ip}:{port}"
    else:
        ip = _get_lan_ip()
        host = f"http://{ip}:{port}"
    # 拼上路径前缀（生产环境 Nginx 代理路径，如 /face）
    url = host + base_path if base_path else host
    return {"url": url}


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """配网页面 — 手机扫码获取服务器地址"""
    setup_path = BASE_DIR / "frontend" / "setup.html"
    return setup_path.read_text(encoding="utf-8")


def _get_lan_ip() -> str:
    """获取本机的公网/LAN IP 地址"""
    import subprocess
    try:
        # 获取所有非回环、非 docker 的 IPv4 地址
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                iface = parts[1]
                if iface == "lo":
                    continue
                if iface.startswith("docker") or iface.startswith("br-"):
                    continue
                addr = parts[3].split("/")[0]
                if not addr.startswith("127."):
                    return addr
    except Exception:
        pass
    # fallback
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "0.0.0.0"


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepfake_detector.image_detector import ImageDetector
from deepfake_detector.security import (
    InMemoryRateLimiter,
    UploadLimits,
    normalize_suffix,
    validate_upload_metadata,
    validate_video_file,
)
from deepfake_detector.video_detector import VideoDetector

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
FRONTEND_URL = os.getenv(
    "FRONTEND_URL", "https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/"
)
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://tanishqkolhatkar93.github.io",
    "https://tanishq93-deepfake-detection.hf.space",
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS)).split(",")
    if origin.strip()
]

app = FastAPI(
    title="Media Authenticity Detector API",
    description=(
        "HTTP service for binary Yes/No image and video checks using a local "
        "xRayon checkpoint-based model with hardened upload validation."
    ),
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-MS"],
)

image_detector = ImageDetector()
video_detector = VideoDetector(image_detector=image_detector)
upload_limits = UploadLimits()
rate_limiter = InMemoryRateLimiter()


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request.state.request_id = uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Process-Time-MS"] = f"{(time.perf_counter() - started) * 1000:.2f}"
    return response


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": "media-authenticity-detector",
        "version": APP_VERSION,
        "frontend_url": FRONTEND_URL,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": ["/health", "/metadata", "/detect/image", "/detect/video"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metadata")
def metadata() -> dict[str, object]:
    return {
        "service": "media-authenticity-detector",
        "version": APP_VERSION,
        "frontend_url": FRONTEND_URL,
        "model": {
            "name": image_detector.model_id,
            "threshold": image_detector.threshold,
            "positive_label": image_detector.fake_label,
            "device": image_detector.device,
        },
        "limits": {
            "max_image_bytes": upload_limits.max_image_bytes,
            "max_video_bytes": upload_limits.max_video_bytes,
            "max_video_duration_seconds": upload_limits.max_video_duration_seconds,
            "rate_limit_max_requests": rate_limiter.max_requests,
            "rate_limit_window_seconds": rate_limiter.window_seconds,
        },
    }


@app.post("/detect/image")
async def detect_image(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
    started = time.perf_counter()
    _check_rate_limit(request)
    payload = await file.read()
    try:
        validate_upload_metadata(
            filename=file.filename,
            content_type=file.content_type,
            payload=payload,
            media_type="image",
            limits=upload_limits,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        image = Image.open(BytesIO(payload)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image payload") from exc

    try:
        report = image_detector.detect_pil(image)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "request_id": request.state.request_id,
        "processed_at": datetime.now(UTC).isoformat(),
        "processing_ms": round((time.perf_counter() - started) * 1000, 2),
        "filename": file.filename or "upload",
        "media_type": "image",
        "model": image_detector.model_id,
        "report": report.to_dict(),
    }


@app.post("/detect/video")
async def detect_video(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
    started = time.perf_counter()
    _check_rate_limit(request)
    payload = await file.read()
    try:
        validate_upload_metadata(
            filename=file.filename,
            content_type=file.content_type,
            payload=payload,
            media_type="video",
            limits=upload_limits,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    temp_dir = ROOT / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    with NamedTemporaryFile(
        delete=False,
        suffix=normalize_suffix(file.filename) or ".mp4",
        dir=temp_dir,
    ) as tmp:
        tmp.write(payload)
        temp_path = Path(tmp.name)

    try:
        validate_video_file(temp_path, limits=upload_limits)
        report = video_detector.detect_file(temp_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "request_id": request.state.request_id,
        "processed_at": datetime.now(UTC).isoformat(),
        "processing_ms": round((time.perf_counter() - started) * 1000, 2),
        "filename": file.filename or "upload",
        "media_type": "video",
        "model": video_detector.image_detector.model_id,
        "report": report.to_dict(),
    }


def _check_rate_limit(request: Request) -> None:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    if not client_ip and request.client is not None:
        client_ip = request.client.host
    if not client_ip:
        client_ip = "unknown"
    try:
        rate_limiter.check(client_ip)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

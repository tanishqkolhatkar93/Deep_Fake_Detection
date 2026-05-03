from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
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

app = FastAPI(
    title="Media Authenticity Detector API",
    description=(
        "HTTP service for binary Yes/No image and video checks using a local "
        "xRayon checkpoint-based model."
    ),
    version="0.1.0",
)

image_detector = ImageDetector()
video_detector = VideoDetector(image_detector=image_detector)
upload_limits = UploadLimits()
rate_limiter = InMemoryRateLimiter()


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": "media-authenticity-detector",
        "docs": "/docs",
        "endpoints": ["/health", "/detect/image", "/detect/video"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/detect/image")
async def detect_image(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
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
        "filename": file.filename or "upload",
        "media_type": "image",
        "report": report.to_dict(),
    }


@app.post("/detect/video")
async def detect_video(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
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
        "filename": file.filename or "upload",
        "media_type": "video",
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

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepfake_detector.image_detector import ImageDetector
from deepfake_detector.video_detector import VideoDetector


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}

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
async def detect_image(file: UploadFile = File(...)) -> dict[str, object]:
    suffix = _normalized_suffix(file.filename)
    if suffix not in IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {suffix or 'unknown'}",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty upload")

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
async def detect_video(file: UploadFile = File(...)) -> dict[str, object]:
    suffix = _normalized_suffix(file.filename)
    if suffix not in VIDEO_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type: {suffix or 'unknown'}",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty upload")

    temp_dir = ROOT / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    with NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as tmp:
        tmp.write(payload)
        temp_path = Path(tmp.name)

    try:
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


def _normalized_suffix(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()

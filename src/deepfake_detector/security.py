from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import cv2


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
}

DEFAULT_MAX_IMAGE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_VIDEO_BYTES = 60 * 1024 * 1024
DEFAULT_MAX_VIDEO_DURATION_SECONDS = 30.0
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 600
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 12


@dataclass(frozen=True)
class UploadLimits:
    max_image_bytes: int = int(os.getenv("MAX_IMAGE_BYTES", str(DEFAULT_MAX_IMAGE_BYTES)))
    max_video_bytes: int = int(os.getenv("MAX_VIDEO_BYTES", str(DEFAULT_MAX_VIDEO_BYTES)))
    max_video_duration_seconds: float = float(
        os.getenv("MAX_VIDEO_DURATION_SECONDS", str(DEFAULT_MAX_VIDEO_DURATION_SECONDS))
    )


def normalize_suffix(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def validate_upload_metadata(
    *,
    filename: str | None,
    content_type: str | None,
    payload: bytes,
    media_type: str,
    limits: UploadLimits | None = None,
) -> None:
    limits = limits or UploadLimits()
    suffix = normalize_suffix(filename)
    content_type = (content_type or "").lower()

    if not payload:
        raise ValueError("Empty upload")

    if media_type == "image":
        if suffix not in IMAGE_SUFFIXES:
            raise ValueError(f"Unsupported image type: {suffix or 'unknown'}")
        if content_type and content_type not in IMAGE_MIME_TYPES:
            raise ValueError(f"Unsupported image MIME type: {content_type}")
        if len(payload) > limits.max_image_bytes:
            raise ValueError(
                f"Image is too large. Limit is {limits.max_image_bytes // (1024 * 1024)} MB."
            )
        return

    if media_type == "video":
        if suffix not in VIDEO_SUFFIXES:
            raise ValueError(f"Unsupported video type: {suffix or 'unknown'}")
        if content_type and content_type not in VIDEO_MIME_TYPES:
            raise ValueError(f"Unsupported video MIME type: {content_type}")
        if len(payload) > limits.max_video_bytes:
            raise ValueError(
                f"Video is too large. Limit is {limits.max_video_bytes // (1024 * 1024)} MB."
            )
        return

    raise ValueError(f"Unsupported media_type: {media_type}")


def validate_video_file(path: str | Path, limits: UploadLimits | None = None) -> float:
    limits = limits or UploadLimits()
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Unable to open uploaded video")

    frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    capture.release()

    if frame_count <= 0 or fps <= 0:
        raise ValueError("Unable to read video duration metadata")

    duration_seconds = frame_count / fps
    if duration_seconds > limits.max_video_duration_seconds:
        raise ValueError(
            f"Video is too long. Limit is {int(limits.max_video_duration_seconds)} seconds."
        )
    return duration_seconds


class InMemoryRateLimiter:
    def __init__(
        self,
        max_requests: int = int(
            os.getenv("RATE_LIMIT_MAX_REQUESTS", str(DEFAULT_RATE_LIMIT_MAX_REQUESTS))
        ),
        window_seconds: int = int(
            os.getenv("RATE_LIMIT_WINDOW_SECONDS", str(DEFAULT_RATE_LIMIT_WINDOW_SECONDS))
        ),
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.time()
        threshold = now - self.window_seconds
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] < threshold:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                raise ValueError(
                    f"Rate limit exceeded. Try again in {self.window_seconds // 60} minutes."
                )
            bucket.append(now)

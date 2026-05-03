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
DEFAULT_MAX_VIDEO_DURATION_SECONDS = 60.0
DEFAULT_FALLBACK_VIDEO_FPS = 24.0
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

    try:
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)

        if frame_count > 0 and fps > 0:
            duration_seconds = frame_count / fps
        else:
            duration_seconds = _probe_video_duration(capture, limits.max_video_duration_seconds)
    finally:
        capture.release()

    if duration_seconds <= 0:
        raise ValueError("Unable to read video duration metadata")
    if duration_seconds > limits.max_video_duration_seconds:
        raise ValueError(
            f"Video is too long. Limit is {int(limits.max_video_duration_seconds)} seconds."
        )
    return duration_seconds


def _probe_video_duration(capture: cv2.VideoCapture, max_duration_seconds: float) -> float:
    fallback_fps = float(os.getenv("FALLBACK_VIDEO_FPS", str(DEFAULT_FALLBACK_VIDEO_FPS)))
    frames_read = 0
    last_timestamp_seconds = 0.0
    # Probe a bounded number of frames. For short public-demo uploads this is acceptable and
    # handles mobile/browser encodes that omit usable frame-count or fps metadata.
    max_probe_frames = int(max(max_duration_seconds, 1.0) * max(fallback_fps, 1.0) * 2)

    while frames_read < max_probe_frames:
        ok, frame = capture.read()
        if not ok or frame is None:
            break

        frames_read += 1
        timestamp_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
        if timestamp_ms > 0:
            last_timestamp_seconds = max(last_timestamp_seconds, timestamp_ms / 1000.0)

        estimated_duration = max(last_timestamp_seconds, frames_read / max(fallback_fps, 1.0))
        if estimated_duration > max_duration_seconds:
            return estimated_duration

    if frames_read == 0:
        return 0.0

    return max(last_timestamp_seconds, frames_read / max(fallback_fps, 1.0))


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

from __future__ import annotations

import pytest

from deepfake_detector.security import UploadLimits, validate_upload_metadata, validate_video_file


def test_image_payload_rejected_when_too_large() -> None:
    limits = UploadLimits(max_image_bytes=8, max_video_bytes=64, max_video_duration_seconds=30.0)
    with pytest.raises(ValueError, match="too large"):
        validate_upload_metadata(
            filename="sample.png",
            content_type="image/png",
            payload=b"123456789",
            media_type="image",
            limits=limits,
        )


def test_video_payload_rejects_wrong_mime() -> None:
    with pytest.raises(ValueError, match="Unsupported video MIME type"):
        validate_upload_metadata(
            filename="sample.mp4",
            content_type="application/octet-stream",
            payload=b"1234",
            media_type="video",
        )


class _FakeCapture:
    def __init__(self, *, frame_count: float, fps: float, readable_frames: int, timestamp_step_ms: float):
        self._frame_count = frame_count
        self._fps = fps
        self._readable_frames = readable_frames
        self._timestamp_step_ms = timestamp_step_ms
        self._frames_read = 0

    def isOpened(self) -> bool:
        return True

    def get(self, prop: int) -> float:
        if prop == 7:  # cv2.CAP_PROP_FRAME_COUNT
            return self._frame_count
        if prop == 5:  # cv2.CAP_PROP_FPS
            return self._fps
        if prop == 0:  # cv2.CAP_PROP_POS_MSEC
            return self._frames_read * self._timestamp_step_ms
        return 0.0

    def read(self):
        if self._frames_read >= self._readable_frames:
            return False, None
        self._frames_read += 1
        return True, object()

    def release(self) -> None:
        return None


def test_video_duration_falls_back_to_frame_probe(monkeypatch) -> None:
    import deepfake_detector.security as security

    monkeypatch.setattr(
        security.cv2,
        "VideoCapture",
        lambda _path: _FakeCapture(
            frame_count=0.0,
            fps=0.0,
            readable_frames=40,
            timestamp_step_ms=250.0,
        ),
    )

    duration = validate_video_file("sample.mp4")
    assert duration > 0
    assert duration <= 30.0


def test_video_duration_probe_still_rejects_long_video(monkeypatch) -> None:
    import deepfake_detector.security as security

    monkeypatch.setattr(
        security.cv2,
        "VideoCapture",
        lambda _path: _FakeCapture(
            frame_count=0.0,
            fps=0.0,
            readable_frames=300,
            timestamp_step_ms=500.0,
        ),
    )

    with pytest.raises(ValueError, match="Video is too long"):
        validate_video_file("sample.mp4")

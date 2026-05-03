from __future__ import annotations

import pytest

from deepfake_detector.security import UploadLimits, validate_upload_metadata


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

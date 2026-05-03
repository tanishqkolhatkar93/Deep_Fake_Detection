from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

import api
from deepfake_detector.types import ImageDetectionReport, VideoDetectionReport


client = TestClient(api.app)


def _png_bytes() -> bytes:
    image = Image.new("RGB", (16, 16), color=(240, 120, 90))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metadata() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "media-authenticity-detector"
    assert "model" in payload
    assert "limits" in payload


def test_version() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()


def test_detect_image(monkeypatch) -> None:
    def fake_detect(_image):
        return ImageDetectionReport(
            verdict="No",
            fake_probability=0.12,
            synthetic_likelihood=0.12,
            deepfake_likelihood=0.12,
            face_count=0,
            evidence={"real": 0.88, "fake": 0.12},
            summary="Synthetic signal not detected.",
            model_name="mock-model",
        )

    monkeypatch.setattr(api.image_detector, "detect_pil", fake_detect)

    response = client.post(
        "/detect/image",
        files={"file": ("sample.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["media_type"] == "image"
    assert payload["report"]["verdict"] == "No"
    assert "request_id" in payload


def test_detect_video(monkeypatch) -> None:
    def fake_validate_video(_path, limits=None):
        return 4.0

    def fake_detect_file(_path):
        return VideoDetectionReport(
            verdict="Yes",
            fake_probability=0.77,
            synthetic_likelihood=0.77,
            deepfake_likelihood=0.77,
            frames_sampled=6,
            evidence={"mean_frame_fake_probability": 0.77},
            summary="Likely manipulated.",
            model_name="mock-model",
        )

    monkeypatch.setattr(api, "validate_video_file", fake_validate_video)
    monkeypatch.setattr(api.video_detector, "detect_file", fake_detect_file)

    response = client.post(
        "/detect/video",
        files={"file": ("sample.mp4", b"not-a-real-video", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["media_type"] == "video"
    assert payload["report"]["frames_sampled"] == 6

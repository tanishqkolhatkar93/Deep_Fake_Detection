from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import api
from deepfake_detector.auth_store import AuthStore
from deepfake_detector.google_auth import GoogleIdentity
from deepfake_detector.types import ImageDetectionReport, VideoDetectionReport


client = TestClient(api.app)


def _png_bytes() -> bytes:
    image = Image.new("RGB", (16, 16), color=(240, 120, 90))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def auth_headers(monkeypatch: pytest.MonkeyPatch, tmp_path) -> dict[str, str]:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("FREE_TIER_IMAGE_LIMIT", "2")
    monkeypatch.setenv("FREE_TIER_VIDEO_LIMIT", "1")

    store = AuthStore(db_path=str(tmp_path / "verilens-test.db"))
    monkeypatch.setattr(api, "auth_store", store)

    def fake_verify_google_id_token(_token: str) -> GoogleIdentity:
        return GoogleIdentity(
            email="tester@example.com",
            subject="google-sub-123",
            name="Verifier",
            picture_url="https://example.com/avatar.png",
        )

    monkeypatch.setattr(api, "verify_google_id_token", fake_verify_google_id_token)

    response = client.post("/auth/google", json={"id_token": "fake-google-id-token"})
    assert response.status_code == 200
    payload = response.json()
    return {"Authorization": f"Bearer {payload['session_token']}"}


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


def test_auth_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    response = client.get("/auth/config")
    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "google_client_id": "test-client-id.apps.googleusercontent.com",
        "free_image_limit": api.auth_store.free_image_limit,
        "free_video_limit": api.auth_store.free_video_limit,
    }


def test_auth_login_and_me(auth_headers: dict[str, str]) -> None:
    response = client.get("/me", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "tester@example.com"
    assert payload["usage"]["image_limit"] == 2
    assert payload["usage"]["video_limit"] == 1


def test_detect_image(monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
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
        headers=auth_headers,
        files={"file": ("sample.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["media_type"] == "image"
    assert payload["report"]["verdict"] == "No"
    assert payload["usage"]["images_used"] == 1
    assert payload["usage"]["image_remaining"] == 1


def test_detect_video(monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
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
        headers=auth_headers,
        files={"file": ("sample.mp4", b"not-a-real-video", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["media_type"] == "video"
    assert payload["report"]["frames_sampled"] == 6
    assert payload["usage"]["videos_used"] == 1
    assert payload["usage"]["video_remaining"] == 0


def test_quota_limit_returns_payment_required(
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
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

    first = client.post(
        "/detect/image",
        headers=auth_headers,
        files={"file": ("sample-1.png", _png_bytes(), "image/png")},
    )
    second = client.post(
        "/detect/image",
        headers=auth_headers,
        files={"file": ("sample-2.png", _png_bytes(), "image/png")},
    )
    third = client.post(
        "/detect/image",
        headers=auth_headers,
        files={"file": ("sample-3.png", _png_bytes(), "image/png")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 402
    assert third.json()["detail"] == "Free image limit reached. Upgrade your plan to continue."


def test_logout_invalidates_session(auth_headers: dict[str, str]) -> None:
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 200

    after_logout = client.get("/me", headers=auth_headers)
    assert after_logout.status_code == 401

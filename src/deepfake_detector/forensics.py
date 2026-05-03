from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def normalize_score(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return clamp01((value - low) / (high - low))


def suspicious_mid_deviation(value: float, center: float, tolerance: float) -> float:
    if tolerance <= 0:
        return 0.0
    return clamp01(abs(value - center) / tolerance)


def to_gray(image_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def load_haar_face_detector() -> cv2.CascadeClassifier:
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    return cv2.CascadeClassifier(str(cascade_path))


def high_frequency_ratio(gray: np.ndarray) -> float:
    gray_f = gray.astype(np.float32) / 255.0
    spectrum = np.fft.fftshift(np.fft.fft2(gray_f))
    power = np.abs(spectrum) ** 2
    h, w = gray.shape
    yy, xx = np.indices((h, w))
    cy, cx = h // 2, w // 2
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    threshold = 0.25 * radius.max()
    high = power[radius >= threshold].sum()
    total = power.sum() + 1e-8
    return float(high / total)


def radial_power_slope(gray: np.ndarray) -> float:
    gray_f = gray.astype(np.float32) / 255.0
    spectrum = np.fft.fftshift(np.fft.fft2(gray_f))
    power = np.abs(spectrum) ** 2
    h, w = gray.shape
    yy, xx = np.indices((h, w))
    cy, cx = h // 2, w // 2
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.int32)
    radial_sum = np.bincount(radius.ravel(), weights=power.ravel())
    radial_count = np.bincount(radius.ravel())
    radial_profile = radial_sum / np.maximum(radial_count, 1)
    valid = np.arange(1, len(radial_profile))
    values = radial_profile[1:]
    mask = values > 0
    valid = valid[mask]
    values = values[mask]
    if len(valid) < 8:
        return -2.0
    x = np.log(valid.astype(np.float32))
    y = np.log(values.astype(np.float32))
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)


def jpeg_blockiness(gray: np.ndarray) -> float:
    gray_i = gray.astype(np.float32)
    if gray.shape[1] > 8:
        left = gray_i[:, 7::8]
        right = gray_i[:, 8::8]
        cols = min(left.shape[1], right.shape[1])
        vertical = np.abs(left[:, :cols] - right[:, :cols]).mean() if cols else 0.0
    else:
        vertical = 0.0

    if gray.shape[0] > 8:
        top = gray_i[7::8, :]
        bottom = gray_i[8::8, :]
        rows = min(top.shape[0], bottom.shape[0])
        horizontal = np.abs(top[:rows, :] - bottom[:rows, :]).mean() if rows else 0.0
    else:
        horizontal = 0.0
    return float((vertical + horizontal) / 2.0)


def local_noise_dispersion(gray: np.ndarray) -> float:
    gray_f = gray.astype(np.float32) / 255.0
    smooth = cv2.GaussianBlur(gray_f, (5, 5), 0)
    residual = np.abs(gray_f - smooth)
    local_mean = cv2.blur(residual, (15, 15))
    return float(local_mean.std() / (local_mean.mean() + 1e-6))


def edge_halo_score(gray: np.ndarray) -> float:
    gray_f = gray.astype(np.float32) / 255.0
    lap = cv2.Laplacian(gray_f, cv2.CV_32F, ksize=3)
    sobel_x = cv2.Sobel(gray_f, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_f, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    edge_mask = grad > np.percentile(grad, 80)
    if not np.any(edge_mask):
        return 0.0
    score = np.mean(np.abs(lap[edge_mask])) / (np.mean(grad[edge_mask]) + 1e-6)
    return float(score)


def clipping_fraction(image_bgr: np.ndarray) -> float:
    image = image_bgr.astype(np.float32)
    clipped_dark = np.mean(image <= 2)
    clipped_bright = np.mean(image >= 253)
    return float(clipped_dark + clipped_bright)


def channel_correlation_gap(image_bgr: np.ndarray) -> float:
    channels = [image_bgr[:, :, idx].astype(np.float32).ravel() for idx in range(3)]
    corrs = []
    for i in range(3):
        for j in range(i + 1, 3):
            corr = np.corrcoef(channels[i], channels[j])[0, 1]
            if np.isnan(corr):
                corr = 1.0
            corrs.append(corr)
    mean_corr = float(np.mean(corrs))
    return clamp01(1.0 - mean_corr)


def detect_faces(image_bgr: np.ndarray, face_detector: cv2.CascadeClassifier) -> list[tuple[int, int, int, int]]:
    gray = to_gray(image_bgr)
    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(48, 48),
    )
    return [tuple(map(int, face)) for face in faces]


def _safe_crop(image: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    h, w = image.shape[:2]
    x0 = max(0, min(w, x0))
    x1 = max(0, min(w, x1))
    y0 = max(0, min(h, y0))
    y1 = max(0, min(h, y1))
    if x1 <= x0 or y1 <= y0:
        return image[0:0, 0:0]
    return image[y0:y1, x0:x1]


def face_artifact_scores(
    image_bgr: np.ndarray, faces: list[tuple[int, int, int, int]]
) -> dict[str, float]:
    if not faces:
        return {
            "face_boundary_score": 0.0,
            "face_texture_gap_score": 0.0,
            "face_color_gap_score": 0.0,
        }

    gray = to_gray(image_bgr)
    boundary_scores = []
    texture_scores = []
    color_scores = []

    for x, y, w, h in faces:
        pad = max(int(0.12 * max(w, h)), 4)
        inner = _safe_crop(gray, x, y, x + w, y + h)
        outer = _safe_crop(gray, x - pad, y - pad, x + w + pad, y + h + pad)
        outer_color = _safe_crop(image_bgr, x - pad, y - pad, x + w + pad, y + h + pad)
        face_color = _safe_crop(image_bgr, x, y, x + w, y + h)
        if inner.size == 0 or outer.size == 0 or face_color.size == 0 or outer_color.size == 0:
            continue

        grad_outer = cv2.Laplacian(outer.astype(np.float32) / 255.0, cv2.CV_32F)
        band = np.zeros_like(outer, dtype=np.uint8)
        band[:pad, :] = 1
        band[-pad:, :] = 1
        band[:, :pad] = 1
        band[:, -pad:] = 1
        band_score = np.mean(np.abs(grad_outer[band == 1])) / (np.mean(np.abs(grad_outer)) + 1e-6)
        boundary_scores.append(float(band_score))

        inner_var = cv2.Laplacian(inner.astype(np.float32), cv2.CV_32F).var()
        outer_var = cv2.Laplacian(outer.astype(np.float32), cv2.CV_32F).var()
        texture_scores.append(float(abs(inner_var - outer_var) / (outer_var + 1e-6)))

        face_mean = face_color.reshape(-1, 3).mean(axis=0)
        outer_mean = outer_color.reshape(-1, 3).mean(axis=0)
        color_gap = np.abs(face_mean - outer_mean).mean() / 255.0
        color_scores.append(float(color_gap))

    if not boundary_scores:
        return {
            "face_boundary_score": 0.0,
            "face_texture_gap_score": 0.0,
            "face_color_gap_score": 0.0,
        }

    return {
        "face_boundary_score": float(np.mean(boundary_scores)),
        "face_texture_gap_score": float(np.mean(texture_scores)),
        "face_color_gap_score": float(np.mean(color_scores)),
    }


def frame_flicker_score(frames_bgr: list[np.ndarray]) -> float:
    if len(frames_bgr) < 3:
        return 0.0
    frame_means = []
    for frame in frames_bgr:
        gray = to_gray(frame).astype(np.float32) / 255.0
        lap = cv2.Laplacian(gray, cv2.CV_32F)
        frame_means.append(float(np.mean(np.abs(lap))))
    diffs = np.abs(np.diff(frame_means))
    return float(np.std(diffs) + np.mean(diffs))

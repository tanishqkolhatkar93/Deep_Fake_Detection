from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .image_detector import ImageDetector
from .types import ImageDetectionReport, VideoDetectionReport


class VideoDetector:
    def __init__(self, image_detector: ImageDetector | None = None, max_frames: int = 8) -> None:
        self.image_detector = image_detector or ImageDetector()
        self.max_frames = max_frames

    def detect_file(self, path: str | Path) -> VideoDetectionReport:
        frames, frame_indices = self._sample_frames(Path(path))
        if not frames:
            raise ValueError(f"Unable to sample frames from video: {path}")

        frame_reports: list[ImageDetectionReport] = []
        for frame, frame_index in zip(frames, frame_indices):
            report = self.image_detector.detect_array(frame)
            report.frame_index = frame_index
            frame_reports.append(report)

        fake_scores = [item.fake_probability for item in frame_reports]
        mean_fake = float(np.mean(fake_scores))
        max_fake = float(np.max(fake_scores))
        positive_frame_ratio = float(
            np.mean([1.0 if item.verdict == "Yes" else 0.0 for item in frame_reports])
        )
        frame_variation = float(np.std(fake_scores))
        verdict = "Yes" if mean_fake >= self.image_detector.threshold else "No"

        return VideoDetectionReport(
            verdict=verdict,
            fake_probability=mean_fake,
            synthetic_likelihood=mean_fake,
            deepfake_likelihood=mean_fake,
            frames_sampled=len(frame_reports),
            evidence={
                "mean_frame_fake_probability": mean_fake,
                "max_frame_fake_probability": max_fake,
                "positive_frame_ratio": positive_frame_ratio,
                "frame_probability_std": frame_variation,
            },
            frame_reports=frame_reports,
            summary=self._build_summary(verdict, mean_fake, len(frame_reports)),
            model_name=self.image_detector.model_id,
        )

    def _sample_frames(self, path: Path) -> tuple[list[np.ndarray], list[int]]:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            return [], []

        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = self.max_frames
        sample_count = min(self.max_frames, max(total_frames, 1))
        indices = np.linspace(0, max(total_frames - 1, 0), num=sample_count, dtype=int)

        frames: list[np.ndarray] = []
        frame_indices: list[int] = []
        for frame_index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            frames.append(frame)
            frame_indices.append(int(frame_index))

        capture.release()
        return frames, frame_indices

    @staticmethod
    def _build_summary(verdict: str, fake_probability: float, frames_sampled: int) -> str:
        if verdict == "Yes":
            return (
                f"{frames_sampled} sampled frames averaged fake probability {fake_probability:.2f}. "
                "The local model flagged the video as likely AI-generated or manipulated."
            )
        return (
            f"{frames_sampled} sampled frames averaged fake probability {fake_probability:.2f}. "
            "The local model did not flag the video as AI-generated or manipulated."
        )

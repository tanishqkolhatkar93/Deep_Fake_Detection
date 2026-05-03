from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ImageDetectionReport:
    verdict: str
    fake_probability: float
    synthetic_likelihood: float
    deepfake_likelihood: float
    face_count: int
    evidence: dict[str, float] = field(default_factory=dict)
    summary: str = ""
    frame_index: int | None = None
    model_name: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VideoDetectionReport:
    verdict: str
    fake_probability: float
    synthetic_likelihood: float
    deepfake_likelihood: float
    frames_sampled: int
    evidence: dict[str, float] = field(default_factory=dict)
    frame_reports: list[ImageDetectionReport] = field(default_factory=list)
    summary: str = ""
    model_name: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["frame_reports"] = [frame.to_dict() for frame in self.frame_reports]
        return data

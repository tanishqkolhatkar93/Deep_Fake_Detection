from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepfake_detector.image_detector import ImageDetector
from deepfake_detector.video_detector import VideoDetector


st.set_page_config(
    page_title="Media Authenticity Detector",
    page_icon="AI",
    layout="wide",
)

st.title("Media Authenticity Detector")
st.caption("Local xRayon detector for binary Yes/No checks on images and videos.")

detector = ImageDetector()
video_detector = VideoDetector(image_detector=detector)


def _evidence_table(evidence: dict[str, float]) -> pd.DataFrame:
    rows = [{"signal": key, "score": round(value, 3)} for key, value in evidence.items()]
    return pd.DataFrame(rows).sort_values("score", ascending=False)


tab1, tab2 = st.tabs(["Image", "Video"])

with tab1:
    image_file = st.file_uploader(
        "Upload an image", type=["png", "jpg", "jpeg", "webp"], key="image"
    )
    if image_file is not None:
        image = Image.open(image_file).convert("RGB")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(image, use_container_width=True)

        try:
            report = detector.detect_pil(image)
        except Exception as exc:
            st.error(str(exc))
        else:
            with col2:
                st.metric("AI Generated / Deepfake", report.verdict)
                st.metric("Fake Probability", f"{report.fake_probability:.2f}")
                st.write(f"Model: `{report.model_name}`")
                st.write(report.summary)

            st.subheader("Model scores")
            st.dataframe(_evidence_table(report.evidence), use_container_width=True)

with tab2:
    video_file = st.file_uploader(
        "Upload a video", type=["mp4", "mov", "avi", "mkv"], key="video"
    )
    if video_file is not None:
        suffix = Path(video_file.name).suffix or ".mp4"
        temp_dir = ROOT / ".tmp"
        temp_dir.mkdir(exist_ok=True)
        st.video(video_file.getvalue())

        try:
            with NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as tmp:
                tmp.write(video_file.getbuffer())
                temp_path = Path(tmp.name)
            report = video_detector.detect_file(temp_path)
        except Exception as exc:
            st.error(str(exc))
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("AI Generated / Deepfake", report.verdict)
            col2.metric("Average Fake Probability", f"{report.fake_probability:.2f}")
            col3.metric("Frames Sampled", str(report.frames_sampled))

            st.write(f"Model: `{report.model_name}`")
            st.write(report.summary)
            st.subheader("Model scores")
            st.dataframe(_evidence_table(report.evidence), use_container_width=True)

            if report.frame_reports:
                frame_rows = [
                    {
                        "frame_index": frame.frame_index,
                        "verdict": frame.verdict,
                        "fake_probability": round(frame.fake_probability, 3),
                    }
                    for frame in report.frame_reports
                ]
                st.subheader("Per-frame scores")
                st.dataframe(pd.DataFrame(frame_rows), use_container_width=True)
        finally:
            if "temp_path" in locals():
                temp_path.unlink(missing_ok=True)

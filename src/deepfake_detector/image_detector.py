from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from transformers import (
    AutoConfig,
    ConvNextForImageClassification,
    ConvNextImageProcessor,
    ConvNextV2ForImageClassification,
    ViTForImageClassification,
)

try:
    from transformers import ViTImageProcessorPil as ViTImageProcessor
except ImportError:
    from transformers import ViTImageProcessor

from .types import ImageDetectionReport


class ImageDetector:
    def __init__(
        self,
        model_id: str | None = None,
        threshold: float | None = None,
        fake_label: str | None = None,
        device: str | None = None,
    ) -> None:
        self.model_id = model_id or os.getenv(
            "HF_MODEL_ID", "xRayon/convnext-ai-images-detector"
        )
        self.threshold = threshold or float(os.getenv("HF_FAKE_THRESHOLD", "0.35"))
        self.fake_label = (fake_label or os.getenv("HF_FAKE_LABEL", "fake")).strip()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.project_root = Path(__file__).resolve().parents[2]
        self.xrayon_checkpoint_path = Path(
            os.getenv(
                "XRAYON_CHECKPOINT_PATH",
                str(self.project_root / "checkpoints" / "checkpoint_phase2.pth"),
            )
        )
        self._processor: Any | None = None
        self._model: Any | None = None

    def detect_file(self, path: str | Path) -> ImageDetectionReport:
        image = Image.open(path).convert("RGB")
        return self.detect_pil(image)

    def detect_pil(self, image: Image.Image) -> ImageDetectionReport:
        processor, model = self._load_model()
        evidence = self._predict(image.convert("RGB"), processor, model)
        fake_probability = self._extract_fake_probability(evidence)
        verdict = "Yes" if fake_probability >= self.threshold else "No"

        return ImageDetectionReport(
            verdict=verdict,
            fake_probability=fake_probability,
            synthetic_likelihood=fake_probability,
            deepfake_likelihood=fake_probability,
            face_count=0,
            evidence=evidence,
            summary=self._build_summary(verdict, fake_probability),
            model_name=self.model_id,
        )

    def detect_array(self, image_bgr: np.ndarray) -> ImageDetectionReport:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        return self.detect_pil(Image.fromarray(rgb))

    def _load_model(self) -> tuple[Any, Any]:
        if self._processor is not None and self._model is not None:
            return self._processor, self._model

        if self.model_id == "xRayon/convnext-ai-images-detector":
            processor, model = self._load_xrayon_model()
            self._processor = processor
            self._model = model
            return processor, model

        try:
            config = AutoConfig.from_pretrained(self.model_id)
            processor, model = self._load_by_model_type(config.model_type)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load local model '{self.model_id}'. "
                "The first run needs internet access to download the weights into the local Hugging Face cache."
            ) from exc

        model.to(self.device)
        model.eval()
        self._processor = processor
        self._model = model
        return processor, model

    def _load_xrayon_model(self) -> tuple[Any, Any]:
        try:
            import timm
            from torchvision import transforms as T
        except Exception as exc:
            raise RuntimeError(
                "xRayon requires the 'timm' and 'torchvision' packages. "
                "Run: python -m pip install timm torchvision"
            ) from exc

        checkpoint_path = self._resolve_xrayon_checkpoint()

        model = timm.create_model(
            "convnextv2_base.fcmae_ft_in1k",
            pretrained=False,
            num_classes=2,
        )
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        state_dict = checkpoint.get("model", checkpoint)
        state_dict = {
            key.removeprefix("module."): value
            for key, value in state_dict.items()
        }
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        if missing and len(missing) > 8:
            raise RuntimeError(
                "xRayon checkpoint loaded with too many missing keys. "
                "Make sure 'checkpoint_phase2.pth' matches the ConvNeXtV2 base architecture."
            )

        transform = T.Compose(
            [
                T.Resize((256, 256), antialias=True),
                T.ToTensor(),
                T.Normalize(
                    mean=(0.485, 0.456, 0.406),
                    std=(0.229, 0.224, 0.225),
                ),
            ]
        )
        model.to(self.device)
        model.eval()
        if unexpected:
            # Non-empty unexpected keys are tolerated because some training checkpoints
            # include optimizer or EMA-related extras outside the model state.
            pass
        return transform, model

    def _resolve_xrayon_checkpoint(self) -> Path:
        if self.xrayon_checkpoint_path.exists():
            return self.xrayon_checkpoint_path

        try:
            downloaded_path = hf_hub_download(
                repo_id="xRayon/convnext-ai-images-detector",
                filename="AI Images Detector/checkpoints/checkpoint_phase2.pth",
            )
        except Exception as exc:
            raise RuntimeError(
                "xRayon checkpoint not found locally and automatic download failed. "
                "Ensure internet access is available or set XRAYON_CHECKPOINT_PATH to a valid "
                "checkpoint_phase2.pth file."
            ) from exc

        return Path(downloaded_path)

    def _load_by_model_type(self, model_type: str) -> tuple[Any, Any]:
        if model_type == "vit":
            processor = ViTImageProcessor.from_pretrained(self.model_id)
            model = ViTForImageClassification.from_pretrained(self.model_id)
            return processor, model

        if model_type == "convnextv2":
            processor = ConvNextImageProcessor.from_pretrained(self.model_id)
            model = ConvNextV2ForImageClassification.from_pretrained(self.model_id)
            return processor, model

        if model_type == "convnext":
            processor = ConvNextImageProcessor.from_pretrained(self.model_id)
            model = ConvNextForImageClassification.from_pretrained(self.model_id)
            return processor, model

        raise RuntimeError(
            f"Unsupported model_type '{model_type}' for model '{self.model_id}'. "
            "Use a ViT, ConvNeXt, or ConvNeXtV2 image-classification model."
        )

    def _predict(self, image: Image.Image, processor: Any, model: Any) -> dict[str, float]:
        if self.model_id == "xRayon/convnext-ai-images-detector":
            tensor = processor(image).unsqueeze(0).to(self.device)
            with torch.inference_mode():
                logits = model(tensor)
                probabilities = torch.softmax(logits, dim=-1)[0].detach().cpu()
            return {
                "real": float(probabilities[0].item()),
                "fake": float(probabilities[1].item()),
            }

        inputs = processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.inference_mode():
            outputs = model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=-1)[0].detach().cpu()

        id2label = getattr(model.config, "id2label", {}) or {}
        return {
            str(id2label.get(index, f"class_{index}")): float(probabilities[index].item())
            for index in range(len(probabilities))
        }

    def _extract_fake_probability(self, evidence: dict[str, float]) -> float:
        normalized = {label.strip().lower(): score for label, score in evidence.items()}

        preferred_fake = self.fake_label.strip().lower()
        if preferred_fake in normalized:
            return normalized[preferred_fake]

        positive_markers = (
            "ai-generated",
            "ai generated",
            "fake",
            "deepfake",
            "synthetic",
            "generated",
            "manipulated",
        )
        negative_markers = (
            "real",
            "human",
            "authentic",
            "natural",
        )

        for label, score in normalized.items():
            if any(marker in label for marker in positive_markers):
                return float(score)

        for label, score in normalized.items():
            if any(marker in label for marker in negative_markers):
                return max(0.0, min(1.0, 1.0 - float(score)))

        labels = ", ".join(evidence.keys())
        raise RuntimeError(
            "The local model did not return recognizable fake/real labels. "
            f"Received labels: {labels}. Set HF_FAKE_LABEL to the positive class label if needed."
        )

    @staticmethod
    def _build_summary(verdict: str, fake_probability: float) -> str:
        if verdict == "Yes":
            return (
                f"The local model flagged this image as likely AI-generated or manipulated "
                f"with probability {fake_probability:.2f}."
            )
        return (
            f"The local model did not flag this image as AI-generated or manipulated. "
            f"Fake probability: {fake_probability:.2f}."
        )

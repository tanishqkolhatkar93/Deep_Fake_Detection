from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepfake_detector.image_detector import ImageDetector
from deepfake_detector.video_detector import VideoDetector


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python detect.py <image-or-video-path>")
        return 1

    target = Path(sys.argv[1]).expanduser().resolve()
    if not target.exists():
        print(f"File not found: {target}")
        return 1

    image_detector = ImageDetector()
    video_detector = VideoDetector(image_detector=image_detector)

    if target.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        report = image_detector.detect_file(target)
    else:
        report = video_detector.detect_file(target)

    print(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

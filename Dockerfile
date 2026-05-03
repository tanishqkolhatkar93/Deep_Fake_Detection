FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/app/.cache/huggingface
ENV PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY . .

RUN python - <<'PY'
from pathlib import Path
import shutil
from huggingface_hub import hf_hub_download

downloaded = hf_hub_download(
    repo_id="xRayon/convnext-ai-images-detector",
    filename="AI Images Detector/checkpoints/checkpoint_phase2.pth",
)
target = Path("/app/checkpoints/checkpoint_phase2.pth")
target.parent.mkdir(parents=True, exist_ok=True)
if not target.exists():
    shutil.copyfile(downloaded, target)
print(target)
PY

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]

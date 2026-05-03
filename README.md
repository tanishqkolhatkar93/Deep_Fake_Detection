---
title: Deepfake and AI-Generated Media Detector
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: Detect AI-generated and deepfake images/videos with xRayon.
tags:
  - computer-vision
  - deepfake-detection
  - streamlit
  - fastapi
models:
  - xRayon/convnext-ai-images-detector
---

# Deepfake and AI-Generated Media Detector

[![CI](https://github.com/tanishqkolhatkar93/Deep_Fake_Detection/actions/workflows/ci.yml/badge.svg)](https://github.com/tanishqkolhatkar93/Deep_Fake_Detection/actions/workflows/ci.yml)

This project is a demo app for detecting:

- AI-generated images
- Deepfake-style or synthetic-looking video frames

It uses a local stronger checkpoint-based model:

- `xRayon/convnext-ai-images-detector`

This Space is configured as a Docker app for Hugging Face Spaces. The xRayon checkpoint is downloaded automatically from Hugging Face during build or first run.

## What it does

- Returns a simple `Yes` or `No` verdict
- Uses the model's fake probability to drive the verdict
- Samples frames from uploaded videos and aggregates frame-level predictions
- Provides a Streamlit UI, CLI, and FastAPI service

## Limits

This is a showcase detector, not a production-grade classifier.

- It requires `timm` and `torchvision`.
- The checkpoint is much larger than the earlier CapCheck model.
- Video detection is frame-based, so it can miss short manipulations.
- Accuracy depends on the chosen model and threshold.
- Upload validation is enforced:
  - images up to 10 MB
  - videos up to 60 MB
  - videos up to 30 seconds
- The FastAPI endpoints also apply a basic in-memory rate limit by client IP.

## Environment

Optional settings:

```powershell
$env:HF_MODEL_ID="xRayon/convnext-ai-images-detector"
$env:HF_FAKE_THRESHOLD="0.35"
$env:HF_FAKE_LABEL="fake"
```

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The checkpoint will be downloaded automatically if it is not already present locally.

Source model:

- https://huggingface.co/xRayon/convnext-ai-images-detector

CLI:

```powershell
python detect.py path\to\image_or_video.mp4
```

API:

```powershell
uvicorn api:app --reload
```

Then open:

- `http://localhost:8501`
- `http://127.0.0.1:8000/docs`

## Project structure

```text
app.py
api.py
checkpoints/
detect.py
src/deepfake_detector/
```

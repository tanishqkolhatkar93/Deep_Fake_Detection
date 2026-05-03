# Deepfake and AI-Generated Media Detector

[![CI](https://github.com/tanishqkolhatkar93/Deep_Fake_Detection/actions/workflows/ci.yml/badge.svg)](https://github.com/tanishqkolhatkar93/Deep_Fake_Detection/actions/workflows/ci.yml)

This project is a demo app for detecting:

- AI-generated images
- Deepfake-style or synthetic-looking video frames

It uses a local stronger checkpoint-based model:

- `xRayon/convnext-ai-images-detector`

This model is not a plain `transformers.from_pretrained()` package. You need to download its checkpoint file once and keep it in this project.

## What it does

- Returns a simple `Yes` or `No` verdict
- Uses the model's fake probability to drive the verdict
- Samples frames from uploaded videos and aggregates frame-level predictions
- Provides a Streamlit UI, CLI, and FastAPI service

## Limits

This is a showcase detector, not a production-grade classifier.

- You must download `checkpoint_phase2.pth` manually from the xRayon model page.
- It also requires `timm` and `torchvision`.
- The checkpoint is much larger than the earlier CapCheck model.
- Video detection is frame-based, so it can miss short manipulations.
- Accuracy depends on the chosen model and threshold.

## Environment

Optional settings:

```powershell
$env:HF_MODEL_ID="xRayon/convnext-ai-images-detector"
$env:HF_FAKE_THRESHOLD="0.35"
$env:HF_FAKE_LABEL="fake"
$env:XRAYON_CHECKPOINT_PATH="C:\Users\tanuu\Downloads\Deep_Fake_Detection\checkpoints\checkpoint_phase2.pth"
```

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Before running, place the xRayon checkpoint here:

```text
checkpoints/checkpoint_phase2.pth
```

Source:

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

---
title: VeriLens Detection API
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Public API for AI-image and short deepfake-video checks.
tags:
  - fastapi
  - computer-vision
  - deepfake-detection
  - synthetic-media
models:
  - xRayon/convnext-ai-images-detector
---

# VeriLens

[![CI](https://github.com/tanishqkolhatkar93/Deep_Fake_Detection/actions/workflows/ci.yml/badge.svg)](https://github.com/tanishqkolhatkar93/Deep_Fake_Detection/actions/workflows/ci.yml)

VeriLens is a public-facing synthetic-media detector with two deployment surfaces:

- `Website`: GitHub Pages static site for product UX, SEO, and browser uploads
- `API`: Hugging Face Spaces Docker runtime serving FastAPI inference endpoints

Live URLs:

- Website: `https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/`
- API: `https://tanishq93-deepfake-detection.hf.space`
- API docs: `https://tanishq93-deepfake-detection.hf.space/docs`
- GitHub: `https://github.com/tanishqkolhatkar93/Deep_Fake_Detection`

## Product scope

VeriLens currently supports:

- image detection with a local xRayon checkpoint
- short video detection by frame sampling and aggregation
- binary `Yes/No` verdicts with fake probability
- browser uploads through the public website
- public API access through FastAPI

This is a strong public demo baseline, not a claim of forensic certainty.

## Architecture

- `site/`: static marketing and scanner website, deployed via GitHub Pages
- `api.py`: FastAPI application for public inference
- `app.py`: Streamlit local/admin demo surface
- `src/deepfake_detector/`: model loading, video sampling, security validation, report types
- `checkpoints/`: local model artifact location

Deployment shape:

1. GitHub Pages serves the public website and SEO surface
2. Hugging Face Spaces serves the FastAPI inference API
3. The website posts uploads cross-origin to the API
4. CORS, upload caps, duration caps, and rate limiting protect the demo runtime

## Security guardrails

The public API enforces:

- image uploads up to `10 MB`
- video uploads up to `60 MB`
- video duration up to `30 seconds`
- MIME and extension validation
- request IDs and processing time headers
- basic in-memory rate limiting by client IP

These controls are appropriate for a free public demo. A heavier production deployment should move to:

- Redis-backed rate limiting
- async video jobs
- durable audit logging
- object storage
- a managed GPU/CPU runtime you control

## Local development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the public API locally:

```powershell
python -m uvicorn api:app --reload
```

Run the Streamlit demo locally:

```powershell
python -m streamlit run app.py
```

Run tests:

```powershell
pytest
```

## Environment variables

Optional runtime settings:

```powershell
$env:HF_MODEL_ID="xRayon/convnext-ai-images-detector"
$env:HF_FAKE_THRESHOLD="0.35"
$env:HF_FAKE_LABEL="fake"
$env:FRONTEND_URL="https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/"
$env:ALLOWED_ORIGINS="https://tanishqkolhatkar93.github.io,https://tanishq93-deepfake-detection.hf.space"
```

## Free hosting rationale

This repo intentionally uses a split deployment:

- GitHub Pages is a good free host for a static, SEO-friendly website
- Hugging Face Spaces is a reasonable free host for model-backed API inference

That combination is more responsible than pretending Vercel/Netlify/Cloudflare can run this exact model-serving workload cleanly for free without architecture changes.

## Operational docs

- [System design](SYSTEM_DESIGN.md)
- [Launch checklist](LAUNCH_CHECKLIST.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Model

- model source: `xRayon/convnext-ai-images-detector`
- checkpoint: `checkpoint_phase2.pth`
- architecture: `ConvNeXtV2`

Source:

- `https://huggingface.co/xRayon/convnext-ai-images-detector`

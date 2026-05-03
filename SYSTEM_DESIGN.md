# VeriLens System Design

## Current public architecture

VeriLens is split into two public layers:

1. `GitHub Pages website`
   - static SEO-friendly product site
   - browser upload UI
   - no server compute on the website tier

2. `Hugging Face Spaces API`
   - FastAPI application in Docker
   - local xRayon checkpoint inference
   - short-video frame sampling and aggregation

That separation keeps the public surface fast while isolating model compute to the inference runtime.

## Request flow

### Image

1. User uploads an image from the website
2. Browser sends multipart request to `/detect/image`
3. API validates MIME, extension, and file size
4. `ImageDetector` loads or reuses the local xRayon model
5. API returns:
   - verdict
   - fake probability
   - model name
   - request ID
   - processing time

### Video

1. User uploads a short video from the website
2. Browser sends multipart request to `/detect/video`
3. API validates MIME, extension, file size, and duration
4. `VideoDetector` samples frames across the clip
5. Each sampled frame is scored by `ImageDetector`
6. Scores are aggregated into a final verdict
7. API returns the video-level report and evidence

## Security controls

The current public demo includes:

- explicit MIME allowlists
- extension allowlists
- image size cap
- video size cap
- video duration cap
- basic IP-based rate limiting
- CORS allowlist
- request tracing via request IDs

## Why this is not pretending to be full enterprise production

Free hosting does not give you:

- durable queue workers
- stable horizontal scaling
- reliable GPU scheduling
- enterprise observability
- WAF-backed abuse controls

So the repo is positioned honestly as a strong public product baseline, not a regulated forensic system.

## Next production upgrades

If this moves beyond public demo use, the next steps are:

1. Move video detection to async jobs
2. Add Redis-backed rate limiting and queueing
3. Add object storage for uploads
4. Add persistent audit logging
5. Add stronger monitoring and error tracking
6. Benchmark and version models formally

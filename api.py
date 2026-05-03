from __future__ import annotations

import logging
import os
import sys
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepfake_detector.auth_store import AuthStore, UserProfile
from deepfake_detector.billing import LemonSqueezyBilling
from deepfake_detector.google_auth import google_auth_enabled, verify_google_id_token
from deepfake_detector.image_detector import ImageDetector
from deepfake_detector.security import (
    InMemoryRateLimiter,
    UploadLimits,
    normalize_suffix,
    validate_upload_metadata,
    validate_video_file,
)
from deepfake_detector.video_detector import VideoDetector

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("verilens.api")

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
FRONTEND_URL = os.getenv(
    "FRONTEND_URL", "https://tanishqkolhatkar93.github.io/Deep_Fake_Detection/"
)
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://tanishqkolhatkar93.github.io",
    "https://tanishq93-deepfake-detection.hf.space",
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS)).split(",")
    if origin.strip()
]


class ServiceInfoResponse(BaseModel):
    service: str
    version: str
    frontend_url: str
    docs: str
    openapi: str
    endpoints: list[str]


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    version: str


class ModelMetadata(BaseModel):
    name: str
    threshold: float
    positive_label: str
    device: str


class LimitsMetadata(BaseModel):
    max_image_bytes: int
    max_video_bytes: int
    max_video_duration_seconds: float
    rate_limit_max_requests: int
    rate_limit_window_seconds: int


class MetadataResponse(BaseModel):
    service: str
    version: str
    frontend_url: str
    model: ModelMetadata
    limits: LimitsMetadata


class DetectionEnvelope(BaseModel):
    request_id: str
    processed_at: str
    processing_ms: float = Field(..., ge=0)
    filename: str
    media_type: str
    model: str
    report: dict[str, object]
    usage: dict[str, int | str] | None = None


class AuthConfigResponse(BaseModel):
    enabled: bool
    google_client_id: str | None
    free_image_limit: int
    free_video_limit: int


class GoogleAuthRequest(BaseModel):
    id_token: str


class UserResponse(BaseModel):
    email: str
    name: str
    picture_url: str
    plan_name: str
    subscription_status: str | None


class AuthSessionResponse(BaseModel):
    session_token: str
    user: UserResponse
    usage: dict[str, int | str]


class MeResponse(BaseModel):
    user: UserResponse
    usage: dict[str, int | str]


class BillingPlanResponse(BaseModel):
    slug: str
    name: str
    price_label: str
    description: str
    image_limit: int
    video_limit: int
    featured: bool
    checkout_available: bool


class BillingConfigResponse(BaseModel):
    enabled: bool
    provider: str
    plans: list[BillingPlanResponse]


class BillingCheckoutRequest(BaseModel):
    plan_slug: str


class BillingRedirectResponse(BaseModel):
    url: str


class BillingPortalResponse(BaseModel):
    url: str


class BillingWebhookResponse(BaseModel):
    status: str


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    return token.strip()


def _serialize_user(user: UserProfile) -> UserResponse:
    return {
        "email": user.email,
        "name": user.name,
        "picture_url": user.picture_url,
        "plan_name": user.plan_name,
        "subscription_status": user.subscription_status,
    }


def _require_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> UserProfile:
    token = _extract_bearer_token(authorization)
    try:
        return auth_store.get_session_user(token)
    except KeyError as exc:
        raise HTTPException(status_code=401, detail="Session expired or invalid.") from exc


app = FastAPI(
    title="Media Authenticity Detector API",
    description=(
        "HTTP service for binary Yes/No image and video checks using a local "
        "xRayon checkpoint-based model with hardened upload validation."
    ),
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-MS"],
)

image_detector = ImageDetector()
video_detector = VideoDetector(image_detector=image_detector)
upload_limits = UploadLimits()
rate_limiter = InMemoryRateLimiter()
auth_store = AuthStore()
billing = LemonSqueezyBilling()


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request.state.request_id = uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Process-Time-MS"] = f"{duration_ms:.2f}"
    logger.info(
        "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request.state.request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/", response_model=ServiceInfoResponse)
def root() -> ServiceInfoResponse:
    return {
        "service": "media-authenticity-detector",
        "version": APP_VERSION,
        "frontend_url": FRONTEND_URL,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": [
            "/health",
            "/version",
            "/metadata",
            "/auth/config",
            "/auth/google",
            "/me",
            "/billing/config",
            "/billing/checkout",
            "/billing/portal",
            "/detect/image",
            "/detect/video",
        ],
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return {"status": "ok"}


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return {"version": APP_VERSION}


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    return {
        "service": "media-authenticity-detector",
        "version": APP_VERSION,
        "frontend_url": FRONTEND_URL,
        "model": {
            "name": image_detector.model_id,
            "threshold": image_detector.threshold,
            "positive_label": image_detector.fake_label,
            "device": image_detector.device,
        },
        "limits": {
            "max_image_bytes": upload_limits.max_image_bytes,
            "max_video_bytes": upload_limits.max_video_bytes,
            "max_video_duration_seconds": upload_limits.max_video_duration_seconds,
            "rate_limit_max_requests": rate_limiter.max_requests,
            "rate_limit_window_seconds": rate_limiter.window_seconds,
        },
    }


@app.get("/auth/config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    return {
        "enabled": google_auth_enabled(),
        "google_client_id": client_id or None,
        "free_image_limit": auth_store.free_image_limit,
        "free_video_limit": auth_store.free_video_limit,
    }


@app.get("/billing/config", response_model=BillingConfigResponse)
def billing_config() -> BillingConfigResponse:
    return billing.public_config()


@app.post("/auth/google", response_model=AuthSessionResponse)
def auth_google(payload: GoogleAuthRequest) -> AuthSessionResponse:
    try:
        identity = verify_google_id_token(payload.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = auth_store.upsert_google_user(
        email=identity.email,
        google_sub=identity.subject,
        name=identity.name,
        picture_url=identity.picture_url,
    )
    session_token = auth_store.create_session(user.email)
    usage = auth_store.get_usage(user.email)
    return {
        "session_token": session_token,
        "user": _serialize_user(user),
        "usage": usage.to_dict(),
    }


@app.post("/auth/logout")
def auth_logout(
    _: Annotated[UserProfile, Depends(_require_user)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, str]:
    token = _extract_bearer_token(authorization)
    auth_store.delete_session(token)
    return {"status": "ok"}


@app.get("/me", response_model=MeResponse)
def me(current_user: Annotated[UserProfile, Depends(_require_user)]) -> MeResponse:
    usage = auth_store.get_usage(current_user.email)
    return {
        "user": _serialize_user(current_user),
        "usage": usage.to_dict(),
    }


@app.post("/billing/checkout", response_model=BillingRedirectResponse)
async def create_billing_checkout(
    payload: BillingCheckoutRequest,
    current_user: Annotated[UserProfile, Depends(_require_user)],
) -> BillingRedirectResponse:
    if current_user.lemon_subscription_id:
        raise HTTPException(
            status_code=409,
            detail="You already have an active subscription. Use the billing portal to manage it.",
        )
    if payload.plan_slug == "free":
        raise HTTPException(status_code=400, detail="The free plan does not require checkout.")

    try:
        plan = billing.get_plan(payload.plan_slug)
        checkout_url = await billing.create_checkout_url(
            plan=plan,
            email=current_user.email,
            name=current_user.name,
            redirect_url=FRONTEND_URL,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "billing_checkout_failed email=%s plan=%s",
            current_user.email,
            payload.plan_slug,
        )
        raise HTTPException(status_code=502, detail="Unable to start checkout right now.") from exc

    return {"url": checkout_url}


@app.get("/billing/portal", response_model=BillingPortalResponse)
async def billing_portal(
    current_user: Annotated[UserProfile, Depends(_require_user)],
) -> BillingPortalResponse:
    if not current_user.lemon_subscription_id:
        raise HTTPException(
            status_code=404,
            detail="No paid subscription is linked to this account yet.",
        )

    try:
        urls = await billing.fetch_subscription_urls(current_user.lemon_subscription_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "billing_portal_failed email=%s subscription_id=%s",
            current_user.email,
            current_user.lemon_subscription_id,
        )
        raise HTTPException(status_code=502, detail="Unable to open the billing portal right now.") from exc

    portal_url = (
        urls.get("customer_portal_update_subscription")
        or urls.get("customer_portal")
        or urls.get("update_payment_method")
    )
    if not portal_url:
        raise HTTPException(status_code=404, detail="No billing portal URL was available.")
    return {"url": portal_url}


@app.post("/webhooks/lemonsqueezy", response_model=BillingWebhookResponse)
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> BillingWebhookResponse:
    payload = await request.body()
    if not billing.verify_signature(payload, x_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    event = await request.json()
    resource = event.get("data") or event
    attributes = resource.get("attributes") or {}
    meta = event.get("meta") or {}
    event_name = str(meta.get("event_name") or "").strip()
    custom_data = meta.get("custom_data") or {}
    user_email = (
        str(custom_data.get("user_email") or "")
        or str(attributes.get("user_email") or "")
        or str(attributes.get("customer_email") or "")
    ).strip().lower()
    if not user_email:
        logger.warning("billing_webhook_missing_email event=%s", event_name)
        return {"status": "ignored"}

    try:
        current_user = auth_store.get_user(user_email)
    except KeyError:
        logger.warning("billing_webhook_unknown_user email=%s event=%s", user_email, event_name)
        return {"status": "ignored"}

    variant_id_raw = attributes.get("variant_id")
    variant_id = int(variant_id_raw) if variant_id_raw is not None else None
    plan = billing.plan_from_variant(variant_id)
    subscription_status = str(attributes.get("status") or "").strip().lower() or None
    resource_id = resource.get("id")
    subscription_id = str(resource_id).strip() if resource_id is not None else None
    customer_id = str(attributes.get("customer_id") or "").strip() or None

    keep_paid_access = event_name not in {
        "subscription_expired",
        "subscription_refunded",
    } and subscription_status not in {"expired"}

    if plan and keep_paid_access:
        auth_store.apply_plan(
            email=current_user.email,
            plan_name=plan.slug,
            image_limit=plan.image_limit,
            video_limit=plan.video_limit,
            lemon_customer_id=customer_id,
            lemon_subscription_id=subscription_id,
            lemon_variant_id=variant_id,
            subscription_status=subscription_status,
        )
    elif event_name in {
        "subscription_expired",
        "subscription_refunded",
    } or subscription_status in {"expired"}:
        auth_store.reset_to_free_plan(current_user.email)
    else:
        logger.info(
            "billing_webhook_ignored email=%s event=%s variant_id=%s",
            current_user.email,
            event_name,
            variant_id,
        )

    return {"status": "ok"}


@app.post("/detect/image", response_model=DetectionEnvelope)
async def detect_image(
    request: Request,
    current_user: Annotated[UserProfile, Depends(_require_user)],
    file: UploadFile = File(...),
) -> DetectionEnvelope:
    started = time.perf_counter()
    _check_rate_limit(request)
    try:
        auth_store.ensure_usage_available(current_user.email, "image")
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    payload = await file.read()
    try:
        validate_upload_metadata(
            filename=file.filename,
            content_type=file.content_type,
            payload=payload,
            media_type="image",
            limits=upload_limits,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        image = Image.open(BytesIO(payload)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image payload") from exc

    try:
        report = image_detector.detect_pil(image)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    usage = auth_store.consume_usage(current_user.email, "image")

    return DetectionEnvelope(
        request_id=request.state.request_id,
        processed_at=datetime.now(UTC).isoformat(),
        processing_ms=round((time.perf_counter() - started) * 1000, 2),
        filename=file.filename or "upload",
        media_type="image",
        model=image_detector.model_id,
        report=report.to_dict(),
        usage=usage.to_dict(),
    )


@app.post("/detect/video", response_model=DetectionEnvelope)
async def detect_video(
    request: Request,
    current_user: Annotated[UserProfile, Depends(_require_user)],
    file: UploadFile = File(...),
) -> DetectionEnvelope:
    started = time.perf_counter()
    _check_rate_limit(request)
    try:
        auth_store.ensure_usage_available(current_user.email, "video")
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    payload = await file.read()
    try:
        validate_upload_metadata(
            filename=file.filename,
            content_type=file.content_type,
            payload=payload,
            media_type="video",
            limits=upload_limits,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    temp_dir = ROOT / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    with NamedTemporaryFile(
        delete=False,
        suffix=normalize_suffix(file.filename) or ".mp4",
        dir=temp_dir,
    ) as tmp:
        tmp.write(payload)
        temp_path = Path(tmp.name)

    try:
        validate_video_file(temp_path, limits=upload_limits)
        report = video_detector.detect_file(temp_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)
    usage = auth_store.consume_usage(current_user.email, "video")

    return DetectionEnvelope(
        request_id=request.state.request_id,
        processed_at=datetime.now(UTC).isoformat(),
        processing_ms=round((time.perf_counter() - started) * 1000, 2),
        filename=file.filename or "upload",
        media_type="video",
        model=video_detector.image_detector.model_id,
        report=report.to_dict(),
        usage=usage.to_dict(),
    )


def _check_rate_limit(request: Request) -> None:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    if not client_ip and request.client is not None:
        client_ip = request.client.host
    if not client_ip:
        client_ip = "unknown"
    try:
        rate_limiter.check(client_ip)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

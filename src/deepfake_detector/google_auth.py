from __future__ import annotations

import os
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


@dataclass(frozen=True)
class GoogleIdentity:
    email: str
    subject: str
    name: str
    picture_url: str


def google_auth_enabled() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID", "").strip())


def verify_google_id_token(token: str) -> GoogleIdentity:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise ValueError("Google login is not configured on the server.")

    payload = id_token.verify_oauth2_token(
        token,
        google_requests.Request(),
        audience=client_id,
    )
    email = str(payload.get("email") or "").strip().lower()
    subject = str(payload.get("sub") or "").strip()
    name = str(payload.get("name") or email).strip()
    picture_url = str(payload.get("picture") or "").strip()

    if not email or not subject:
        raise ValueError("Google token did not contain a valid user identity.")

    return GoogleIdentity(
        email=email,
        subject=subject,
        name=name,
        picture_url=picture_url,
    )

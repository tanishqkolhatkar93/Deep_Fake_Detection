from __future__ import annotations

import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


DEFAULT_FREE_IMAGE_LIMIT = 10
DEFAULT_FREE_VIDEO_LIMIT = 3
DEFAULT_SESSION_TTL_DAYS = 30


@dataclass(frozen=True)
class UserProfile:
    email: str
    google_sub: str
    name: str
    picture_url: str
    plan_name: str
    image_limit: int
    video_limit: int


@dataclass(frozen=True)
class UsageSnapshot:
    period: str
    images_used: int
    videos_used: int
    image_limit: int
    video_limit: int
    image_remaining: int
    video_remaining: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "period": self.period,
            "images_used": self.images_used,
            "videos_used": self.videos_used,
            "image_limit": self.image_limit,
            "video_limit": self.video_limit,
            "image_remaining": self.image_remaining,
            "video_remaining": self.video_remaining,
        }


class AuthStore:
    def __init__(self, db_path: str | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        default_path = project_root / "data" / "verilens.db"
        self.db_path = Path(db_path or os.getenv("VERILENS_DB_PATH", str(default_path)))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_ttl_days = int(
            os.getenv("SESSION_TTL_DAYS", str(DEFAULT_SESSION_TTL_DAYS))
        )
        self.free_image_limit = int(
            os.getenv("FREE_TIER_IMAGE_LIMIT", str(DEFAULT_FREE_IMAGE_LIMIT))
        )
        self.free_video_limit = int(
            os.getenv("FREE_TIER_VIDEO_LIMIT", str(DEFAULT_FREE_VIDEO_LIMIT))
        )
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    google_sub TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    picture_url TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    image_limit INTEGER NOT NULL,
                    video_limit INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(email) REFERENCES users(email)
                );

                CREATE TABLE IF NOT EXISTS usage_monthly (
                    email TEXT NOT NULL,
                    period TEXT NOT NULL,
                    images_used INTEGER NOT NULL DEFAULT 0,
                    videos_used INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (email, period),
                    FOREIGN KEY(email) REFERENCES users(email)
                );
                """
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _period(now: datetime | None = None) -> str:
        current = now or datetime.now(UTC)
        return current.strftime("%Y-%m")

    def upsert_google_user(
        self,
        *,
        email: str,
        google_sub: str,
        name: str,
        picture_url: str,
    ) -> UserProfile:
        now = self._now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (email, google_sub, name, picture_url, plan_name, image_limit, video_limit, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    google_sub = excluded.google_sub,
                    name = excluded.name,
                    picture_url = excluded.picture_url,
                    updated_at = excluded.updated_at
                """,
                (
                    email.lower(),
                    google_sub,
                    name,
                    picture_url,
                    "free",
                    self.free_image_limit,
                    self.free_video_limit,
                    now,
                    now,
                ),
            )
        return self.get_user(email)

    def get_user(self, email: str) -> UserProfile:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT email, google_sub, name, picture_url, plan_name, image_limit, video_limit
                FROM users
                WHERE email = ?
                """,
                (email.lower(),),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown user: {email}")
        return UserProfile(
            email=row["email"],
            google_sub=row["google_sub"],
            name=row["name"],
            picture_url=row["picture_url"],
            plan_name=row["plan_name"],
            image_limit=int(row["image_limit"]),
            video_limit=int(row["video_limit"]),
        )

    def create_session(self, email: str) -> str:
        token = secrets.token_urlsafe(32)
        now = self._now()
        expires_at = now + timedelta(days=self.session_ttl_days)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (token, email, created_at, last_seen_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    token,
                    email.lower(),
                    now.isoformat(),
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
        return token

    def delete_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def get_session_user(self, token: str) -> UserProfile:
        now = self._now()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT s.email
                FROM sessions s
                WHERE s.token = ? AND s.expires_at > ?
                """,
                (token, now.isoformat()),
            ).fetchone()
            if row is None:
                raise KeyError("Session expired or invalid")
            connection.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
                (now.isoformat(), token),
            )
        return self.get_user(str(row["email"]))

    def get_usage(self, email: str) -> UsageSnapshot:
        user = self.get_user(email)
        period = self._period()
        now = self._now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO usage_monthly (email, period, images_used, videos_used, updated_at)
                VALUES (?, ?, 0, 0, ?)
                ON CONFLICT(email, period) DO NOTHING
                """,
                (email.lower(), period, now),
            )
            row = connection.execute(
                """
                SELECT images_used, videos_used
                FROM usage_monthly
                WHERE email = ? AND period = ?
                """,
                (email.lower(), period),
            ).fetchone()

        images_used = int(row["images_used"]) if row is not None else 0
        videos_used = int(row["videos_used"]) if row is not None else 0
        return UsageSnapshot(
            period=period,
            images_used=images_used,
            videos_used=videos_used,
            image_limit=user.image_limit,
            video_limit=user.video_limit,
            image_remaining=max(0, user.image_limit - images_used),
            video_remaining=max(0, user.video_limit - videos_used),
        )

    def ensure_usage_available(self, email: str, media_type: str) -> UsageSnapshot:
        usage = self.get_usage(email)
        if media_type == "image" and usage.image_remaining <= 0:
            raise ValueError("Free image limit reached. Upgrade your plan to continue.")
        if media_type == "video" and usage.video_remaining <= 0:
            raise ValueError("Free video limit reached. Upgrade your plan to continue.")
        return usage

    def consume_usage(self, email: str, media_type: str) -> UsageSnapshot:
        usage = self.ensure_usage_available(email, media_type)
        period = usage.period
        now = self._now().isoformat()
        with self._connect() as connection:
            if media_type == "image":
                connection.execute(
                    """
                    UPDATE usage_monthly
                    SET images_used = images_used + 1, updated_at = ?
                    WHERE email = ? AND period = ?
                    """,
                    (now, email.lower(), period),
                )
            elif media_type == "video":
                connection.execute(
                    """
                    UPDATE usage_monthly
                    SET videos_used = videos_used + 1, updated_at = ?
                    WHERE email = ? AND period = ?
                    """,
                    (now, email.lower(), period),
                )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")
        return self.get_usage(email)

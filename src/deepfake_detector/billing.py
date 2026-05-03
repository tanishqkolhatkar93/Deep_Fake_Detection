from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class PlanDefinition:
    slug: str
    name: str
    price_label: str
    description: str
    image_limit: int
    video_limit: int
    variant_id: int | None
    featured: bool = False

    def to_public_dict(self) -> dict[str, object]:
        return {
            "slug": self.slug,
            "name": self.name,
            "price_label": self.price_label,
            "description": self.description,
            "image_limit": self.image_limit,
            "video_limit": self.video_limit,
            "featured": self.featured,
            "checkout_available": self.variant_id is not None,
        }


class LemonSqueezyBilling:
    def __init__(self) -> None:
        self.api_key = os.getenv("LEMON_SQUEEZY_API_KEY", "").strip()
        self.store_id = os.getenv("LEMON_SQUEEZY_STORE_ID", "").strip()
        self.webhook_secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()
        self.redirect_url = os.getenv("LEMON_SQUEEZY_REDIRECT_URL", "").strip()
        self.test_mode = os.getenv("LEMON_SQUEEZY_TEST_MODE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.plans = self._load_plans()

    def _load_plans(self) -> dict[str, PlanDefinition]:
        def _variant(key: str) -> int | None:
            raw = os.getenv(key, "").strip()
            if not raw:
                return None
            return int(raw)

        return {
            "starter": PlanDefinition(
                slug="starter",
                name="Starter",
                price_label=os.getenv("STARTER_PRICE_LABEL", "$9/mo"),
                description="Best for solo creators and light verification workloads.",
                image_limit=int(os.getenv("STARTER_IMAGE_LIMIT", "120")),
                video_limit=int(os.getenv("STARTER_VIDEO_LIMIT", "15")),
                variant_id=_variant("LEMON_STARTER_VARIANT_ID"),
            ),
            "pro": PlanDefinition(
                slug="pro",
                name="Pro",
                price_label=os.getenv("PRO_PRICE_LABEL", "$19/mo"),
                description="Higher monthly quotas and API access for heavier usage.",
                image_limit=int(os.getenv("PRO_IMAGE_LIMIT", "400")),
                video_limit=int(os.getenv("PRO_VIDEO_LIMIT", "50")),
                variant_id=_variant("LEMON_PRO_VARIANT_ID"),
                featured=True,
            ),
            "business": PlanDefinition(
                slug="business",
                name="Business",
                price_label=os.getenv("BUSINESS_PRICE_LABEL", "$49/mo"),
                description="Team-facing limits and a stronger plan for recurring client work.",
                image_limit=int(os.getenv("BUSINESS_IMAGE_LIMIT", "1500")),
                video_limit=int(os.getenv("BUSINESS_VIDEO_LIMIT", "180")),
                variant_id=_variant("LEMON_BUSINESS_VARIANT_ID"),
            ),
        }

    def public_config(self) -> dict[str, object]:
        return {
            "enabled": self.is_enabled(),
            "provider": "lemonsqueezy",
            "plans": [plan.to_public_dict() for plan in self.plans.values()],
        }

    def is_enabled(self) -> bool:
        return bool(
            self.api_key
            and self.store_id
            and any(plan.variant_id is not None for plan in self.plans.values())
        )

    def get_plan(self, slug: str) -> PlanDefinition:
        try:
            return self.plans[slug]
        except KeyError as exc:
            raise ValueError(f"Unknown plan: {slug}") from exc

    def plan_from_variant(self, variant_id: int | None) -> PlanDefinition | None:
        for plan in self.plans.values():
            if plan.variant_id == variant_id:
                return plan
        return None

    def verify_signature(self, payload: bytes, signature: str | None) -> bool:
        if not self.webhook_secret or not signature:
            return False
        digest = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    async def create_checkout_url(
        self,
        *,
        plan: PlanDefinition,
        email: str,
        name: str,
        redirect_url: str,
    ) -> str:
        if not self.is_enabled():
            raise RuntimeError("Billing is not configured on the server.")
        if plan.variant_id is None:
            raise ValueError(f"Plan '{plan.slug}' is not purchasable.")

        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "product_options": {
                        "enabled_variants": [plan.variant_id],
                        "redirect_url": redirect_url or self.redirect_url,
                    },
                    "checkout_data": {
                        "email": email,
                        "name": name,
                        "custom": {
                            "user_email": email,
                            "plan_slug": plan.slug,
                        },
                    },
                    "test_mode": self.test_mode,
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": self.store_id,
                        }
                    },
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": str(plan.variant_id),
                        }
                    },
                },
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.lemonsqueezy.com/v1/checkouts",
                headers={
                    "Accept": "application/vnd.api+json",
                    "Content-Type": "application/vnd.api+json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=payload,
            )
        response.raise_for_status()
        data = response.json()["data"]["attributes"]
        return str(data["url"])

    async def fetch_subscription_urls(self, subscription_id: str) -> dict[str, str | None]:
        if not self.is_enabled():
            raise RuntimeError("Billing is not configured on the server.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://api.lemonsqueezy.com/v1/subscriptions/{subscription_id}",
                headers={
                    "Accept": "application/vnd.api+json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
        response.raise_for_status()
        attributes = response.json()["data"]["attributes"]
        urls = attributes.get("urls") or {}
        return {
            "customer_portal": urls.get("customer_portal"),
            "customer_portal_update_subscription": urls.get(
                "customer_portal_update_subscription"
            ),
            "update_payment_method": urls.get("update_payment_method"),
        }

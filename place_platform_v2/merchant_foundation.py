"""Sponsor/VIP-ready merchant foundation for PrachinLife V2.

This module intentionally does not mutate canonical place facts and does not
control public ranking.  It models optional merchant-owned content and
contract-bound VIP entitlements so future Merchant/Sponsor features can be
added without changing the canonical/evidence architecture.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class MerchantMode(str, Enum):
    NORMAL = "normal"
    VIP = "vip"


@dataclass(frozen=True)
class MerchantContentDraft:
    place_id: str
    logo_media_id: str | None = None
    cover_media_id: str | None = None
    gallery_media_ids: tuple[str, ...] = ()
    uploaded_media_id: str | None = None
    line_url: str | None = None
    facebook_url: str | None = None
    menu_url: str | None = None
    booking_url: str | None = None
    highlight_text: str | None = None

    @classmethod
    def create(cls, *, place_id: str, gallery_media_ids: Iterable[str] = (), **kwargs):
        clean_id = str(place_id or "").strip()
        if not clean_id:
            raise ValueError("place_id is required")
        gallery = tuple(dict.fromkeys(str(v).strip() for v in gallery_media_ids if str(v).strip()))
        if len(gallery) > 20:
            raise ValueError("gallery supports at most 20 media assets")
        for field in ("line_url", "facebook_url", "menu_url", "booking_url"):
            value = kwargs.get(field)
            if value and not str(value).strip().lower().startswith(("http://", "https://")):
                raise ValueError(f"{field} must be an http(s) URL")
        return cls(place_id=clean_id, gallery_media_ids=gallery, **kwargs)


@dataclass(frozen=True)
class SponsorEntitlement:
    place_id: str
    mode: MerchantMode = MerchantMode.NORMAL
    plan: str | None = None
    contract_start_at: datetime | None = None
    contract_end_at: datetime | None = None
    auto_expire: bool = True
    contract_reference: str | None = None

    def __post_init__(self):
        if not str(self.place_id or "").strip():
            raise ValueError("place_id is required")
        for value, label in (
            (self.contract_start_at, "contract_start_at"),
            (self.contract_end_at, "contract_end_at"),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{label} must be timezone-aware")
        if self.contract_start_at and self.contract_end_at and self.contract_end_at <= self.contract_start_at:
            raise ValueError("contract_end_at must be after contract_start_at")
        if self.mode is MerchantMode.VIP and (self.contract_start_at is None or self.contract_end_at is None):
            raise ValueError("VIP mode requires contract_start_at and contract_end_at")

    def effective_mode(self, at: datetime | None = None) -> MerchantMode:
        """Return the runtime mode without mutating stored contract history."""
        at = at or datetime.now(timezone.utc)
        if at.tzinfo is None:
            raise ValueError("at must be timezone-aware")
        if self.mode is not MerchantMode.VIP:
            return MerchantMode.NORMAL
        if self.contract_start_at and at < self.contract_start_at:
            return MerchantMode.NORMAL
        if self.contract_end_at and at >= self.contract_end_at and self.auto_expire:
            return MerchantMode.NORMAL
        return MerchantMode.VIP

    def is_active(self, at: datetime | None = None) -> bool:
        return self.effective_mode(at) is MerchantMode.VIP

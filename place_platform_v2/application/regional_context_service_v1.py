from __future__ import annotations

from typing import Callable

RegionalContextLoaderV1 = Callable[[str], dict[str, object]]


def regional_context_response_payload(
    region_slug: str,
    *,
    load_context: RegionalContextLoaderV1,
) -> dict[str, object]:
    """Resolve a regional context payload through an injected runtime loader."""

    return load_context(region_slug)

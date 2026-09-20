from __future__ import annotations

from threading import Lock
from typing import Any, Callable, Mapping

CBI_API_SHADOW_HOOK_VERSION = "1.0"
CBI_API_SHADOW_MODE = "SHADOW"

ShadowObserverV1 = Callable[[Mapping[str, Any]], Any]

_LOCK = Lock()
_OBSERVER: ShadowObserverV1 | None = None


def configure_cbi_api_shadow_observer_v1(
    observer: ShadowObserverV1 | None,
) -> None:
    if observer is not None and not callable(observer):
        raise TypeError("cbi_shadow_observer_must_be_callable")

    global _OBSERVER

    with _LOCK:
        _OBSERVER = observer


def cbi_api_shadow_enabled_v1() -> bool:
    with _LOCK:
        return _OBSERVER is not None


def observe_decision_request_shadow_v1(
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, Mapping):
        return

    with _LOCK:
        observer = _OBSERVER

    if observer is None:
        return

    try:
        observer(payload)
    except Exception:
        return

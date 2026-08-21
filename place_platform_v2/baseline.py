"""Frozen V1 baseline metadata used by V2 safety checks."""

from dataclasses import dataclass

from . import FROZEN_V1_COMMIT, FROZEN_V1_TAG


@dataclass(frozen=True)
class FrozenBaseline:
    tag: str
    commit: str
    mutable: bool = False


V1_BASELINE = FrozenBaseline(
    tag=FROZEN_V1_TAG,
    commit=FROZEN_V1_COMMIT,
)

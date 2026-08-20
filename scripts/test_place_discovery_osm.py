import sys
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from scripts.place_discovery_osm import (
    OSMDiscoveryResult,
)


def check(value, label):
    if not value:
        raise AssertionError(label)

    print("[PASS]", label)


def main():

    complete = OSMDiscoveryResult(
        elements=[
            {
                "type": "node",
                "id": 1,
            }
        ],
        completed_requests=4,
        failed_requests=0,
        coverage_complete=True,
    )

    check(
        complete.coverage_complete,
        "complete coverage accepted",
    )

    check(
        complete.completed_requests
        == 4,
        "completed request count preserved",
    )

    incomplete = OSMDiscoveryResult(
        elements=[],
        completed_requests=1,
        failed_requests=3,
        coverage_complete=False,
    )

    check(
        not incomplete.coverage_complete,
        "incomplete coverage preserved",
    )

    check(
        incomplete.failed_requests
        == 3,
        "failed request count preserved",
    )

    check(
        incomplete.elements == [],
        "zero results preserved separately from coverage",
    )

    print()
    print("=" * 60)
    print("PLACE DISCOVERY OSM CORE")
    print("FINAL RESULT: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()

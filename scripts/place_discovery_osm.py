from __future__ import annotations

import time

import requests


DEFAULT_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


class OSMDiscoveryResult:
    def __init__(
        self,
        elements=None,
        completed_requests=0,
        failed_requests=0,
        coverage_complete=False,
    ):
        self.elements = elements or []
        self.completed_requests = completed_requests
        self.failed_requests = failed_requests
        self.coverage_complete = coverage_complete


def fetch_overpass_query(
    query,
    label,
    *,
    endpoints=None,
    timeout=45,
    max_retries=2,
    rate_limit_backoff_seconds=8,
    error_backoff_seconds=2,
    user_agent="PrachinLife-PlaceDiscovery/1.0",
):
    endpoints = (
        endpoints
        or DEFAULT_ENDPOINTS
    )

    for endpoint in endpoints:

        for attempt in range(
            1,
            max_retries + 1,
        ):
            try:
                print(
                    f"[FETCH] {label}"
                    f" | {endpoint}"
                    f" | attempt={attempt}"
                )

                response = requests.post(
                    endpoint,
                    data={
                        "data": query,
                    },
                    timeout=timeout,
                    headers={
                        "User-Agent":
                            user_agent,
                    },
                )

                if (
                    response.status_code
                    == 429
                ):
                    print(
                        "RATE LIMITED = 429"
                    )

                    time.sleep(
                        rate_limit_backoff_seconds
                    )

                    continue

                response.raise_for_status()

                payload = response.json()

                elements = payload.get(
                    "elements",
                    [],
                )

                print(
                    "RECEIVED =",
                    len(elements),
                )

                return (
                    elements,
                    True,
                )

            except requests.HTTPError as error:

                status = (
                    error.response.status_code
                    if error.response
                    is not None
                    else None
                )

                print(
                    "FAILED = HTTPError",
                    status,
                    str(error),
                )

                if status == 429:
                    time.sleep(
                        rate_limit_backoff_seconds
                    )

                else:
                    time.sleep(
                        error_backoff_seconds
                    )

            except (
                requests.RequestException,
                ValueError,
            ) as error:

                print(
                    "FAILED =",
                    type(error).__name__,
                    str(error),
                )

                time.sleep(
                    error_backoff_seconds
                )

    return [], False


def fetch_bbox_grid(
    grid_boxes,
    query_builder,
    *,
    sleep_between_requests=1.5,
    endpoints=None,
    timeout=45,
    max_retries=2,
    rate_limit_backoff_seconds=8,
    user_agent="PrachinLife-PlaceDiscovery/1.0",
):
    all_elements = []

    completed = 0
    failed = 0

    total = len(
        grid_boxes
    )

    for index, bbox in enumerate(
        grid_boxes,
        start=1,
    ):
        query = query_builder(
            bbox
        )

        elements, success = (
            fetch_overpass_query(
                query,
                f"bbox-grid-{index}",
                endpoints=endpoints,
                timeout=timeout,
                max_retries=max_retries,
                rate_limit_backoff_seconds=(
                    rate_limit_backoff_seconds
                ),
                user_agent=user_agent,
            )
        )

        if success:
            completed += 1
        else:
            failed += 1

        if elements:
            all_elements.extend(
                elements
            )

        if index < total:
            time.sleep(
                sleep_between_requests
            )

    unique = {}

    for element in all_elements:

        key = (
            element.get("type"),
            element.get("id"),
        )

        unique[key] = element

    merged = list(
        unique.values()
    )

    coverage_complete = (
        failed == 0
        and
        completed == total
    )

    return OSMDiscoveryResult(
        elements=merged,
        completed_requests=completed,
        failed_requests=failed,
        coverage_complete=coverage_complete,
    )

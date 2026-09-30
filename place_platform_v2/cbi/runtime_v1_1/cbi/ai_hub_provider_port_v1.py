from __future__ import annotations

import json
import os
import socket
from urllib import error as urlerror
from urllib import request as urlrequest

from .provider_port import ProviderPort


AI_HUB_PROVIDER_PORT_VERSION = "1.0"
DEFAULT_PROFILE = "cbi-semantic"


_SYSTEM_PROMPT = """You are the external language-understanding helper for MEasyMate CBI.

CBI understands conversation. The downstream Project Brain makes business decisions.

Your authority is strictly limited:
- interpret the user's current meaning
- propose an intent
- propose semantic slots
- identify ambiguity or missing information
- provide confidence

You MUST NOT:
- recommend or choose a business/place
- rank or score candidates
- create candidate IDs or place IDs
- make publication/canonical/projection decisions
- make business decisions
- invent facts

Return exactly one JSON object with these fields only:
status
intent
slots
confidence
missing_information
ambiguity

status must be UNDERSTOOD or NEEDS_CLARIFICATION.
intent must be a string or null.
slots must be an object.
confidence must be a number from 0 to 1.
missing_information must be an array of short strings.
ambiguity must be an array of short strings.

The result is an UNTRUSTED semantic proposal. CBI will validate it.
"""


class AIHubProviderPortV1(ProviderPort):
    def __init__(
        self,
        *,
        base_url=None,
        bearer_token=None,
        profile=DEFAULT_PROFILE,
        timeout_seconds=8.0,
        transport=None,
    ):
        super().__init__("AI_HUB")

        self.base_url = str(base_url or "").strip().rstrip("/")
        self.bearer_token = str(
            bearer_token or ""
        ).strip()

        self.profile = str(
            profile or DEFAULT_PROFILE
        ).strip()

        self.timeout_seconds = min(
            max(float(timeout_seconds), 1.0),
            30.0,
        )

        self._transport = (
            transport
            if transport is not None
            else self._http_transport
        )

    @classmethod
    def from_environment(cls):
        try:
            timeout = float(
                os.environ.get(
                    "MEASYMATE_AI_HUB_TIMEOUT_SECONDS",
                    "8",
                )
            )
        except ValueError:
            timeout = 8.0

        return cls(
            base_url=os.environ.get(
                "MEASYMATE_AI_HUB_URL",
                "",
            ),
            bearer_token=os.environ.get(
                "MEASYMATE_AI_HUB_TOKEN",
                "",
            ),
            profile=os.environ.get(
                "MEASYMATE_AI_HUB_CBI_PROFILE",
                DEFAULT_PROFILE,
            ),
            timeout_seconds=timeout,
        )

    @property
    def available(self):
        return bool(
            self.base_url
            and self.bearer_token
            and self.profile
        )

    @staticmethod
    def _http_transport(
        url,
        headers,
        body,
        timeout_seconds,
    ):
        req = urlrequest.Request(
            url,
            data=json.dumps(
                body,
                ensure_ascii=False,
            ).encode("utf-8"),
            method="POST",
            headers=headers,
        )

        try:
            with urlrequest.urlopen(
                req,
                timeout=timeout_seconds,
            ) as response:
                status = int(
                    getattr(response, "status", 200)
                )

                data = json.loads(
                    response.read().decode("utf-8")
                )

                return status, data

        except urlerror.HTTPError as exc:
            return int(exc.code), {}

        except (
            urlerror.URLError,
            socket.timeout,
            TimeoutError,
            json.JSONDecodeError,
        ):
            return 503, {}

    @staticmethod
    def _extract_json(text):
        raw = str(text or "").strip()

        if raw.startswith("```"):
            lines = raw.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            raw = "\n".join(lines).strip()

        start = raw.find("{")
        end = raw.rfind("}")

        if start < 0 or end < start:
            return None

        try:
            result = json.loads(
                raw[start:end + 1]
            )
        except json.JSONDecodeError:
            return None

        return (
            result
            if isinstance(result, dict)
            else None
        )

    def escalate(self, payload):
        if not self.available:
            return {
                "status": "PROVIDER_UNAVAILABLE",
                "provider_mode": "AI_HUB",
                "trusted": False,
            }

        endpoint = (
            self.base_url
            + "/v1/ai/generate"
        )

        body = {
            "profile": self.profile,
            "messages": [
                {
                    "role": "system",
                    "content": _SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                },
            ],
            "options": {
                "max_output_tokens": 700,
            },
        }

        headers = {
            "Authorization":
                f"Bearer {self.bearer_token}",
            "Content-Type":
                "application/json",
            "Accept":
                "application/json",
        }

        try:
            status, response = self._transport(
                endpoint,
                headers,
                body,
                self.timeout_seconds,
            )
        except Exception:
            return {
                "status": "PROVIDER_UNAVAILABLE",
                "provider_mode": "AI_HUB",
                "trusted": False,
            }

        if (
            status != 200
            or not isinstance(response, dict)
            or response.get("status") != "ok"
        ):
            return {
                "status": "PROVIDER_UNAVAILABLE",
                "provider_mode": "AI_HUB",
                "trusted": False,
            }

        output = response.get("output")

        if not isinstance(output, dict):
            return {
                "status": "INVALID_PROPOSAL",
                "provider_mode": "AI_HUB",
                "trusted": False,
            }

        proposal = self._extract_json(
            output.get("text")
        )

        if proposal is None:
            return {
                "status": "INVALID_PROPOSAL",
                "provider_mode": "AI_HUB",
                "trusted": False,
            }

        return {
            "status": "PROPOSAL",
            "provider_mode": "AI_HUB",
            "trusted": False,
            "proposal": proposal,
        }

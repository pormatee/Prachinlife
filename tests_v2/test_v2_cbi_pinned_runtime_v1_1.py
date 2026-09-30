from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import unittest

from place_platform_v2.cbi.pinned_runtime_v1_1 import (
    build_pinned_cbi_v1_1,
)
from place_platform_v2.cbi.runtime_v1_1 import (
    DOMAIN_ID,
    DOMAIN_PACK_VERSION,
    RUNTIME_VERSION,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
)


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = (
    ROOT
    / "place_platform_v2"
    / "cbi"
    / "runtime_v1_1"
)


class LocalLifeCBIPinnedRuntimeV11Tests(
    unittest.TestCase
):
    def test_source_pin(self):
        self.assertEqual(
            SOURCE_REPOSITORY,
            "pormatee/MEasyMate_CBI",
        )
        self.assertEqual(
            SOURCE_COMMIT,
            "4957dc6db12bdf5bccd0d95bbe8b22dbef8f1d17",
        )
        self.assertEqual(
            RUNTIME_VERSION,
            "1.1.0",
        )
        self.assertEqual(
            DOMAIN_ID,
            "local_life",
        )
        self.assertEqual(
            DOMAIN_PACK_VERSION,
            "1.1.0",
        )

    def test_projection_manifest_hashes_match(self):
        manifest = json.loads(
            (
                RUNTIME_ROOT
                / "SOURCE_MANIFEST.json"
            ).read_text(encoding="utf-8")
        )

        self.assertTrue(
            manifest["projection_only"]
        )

        self.assertEqual(
            manifest["source_commit"],
            SOURCE_COMMIT,
        )

        for rel, expected in manifest[
            "files"
        ].items():
            path = RUNTIME_ROOT / rel

            self.assertTrue(
                path.is_file(),
                rel,
            )

            actual = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

            self.assertEqual(
                actual,
                expected,
                rel,
            )

    def test_default_runtime_has_no_provider(self):
        runtime = build_pinned_cbi_v1_1()

        self.assertFalse(
            runtime.core.provider_port.available
        )

        self.assertEqual(
            runtime.runtime_version,
            "1.1.0",
        )

    def test_deterministic_cbi_still_understands(self):
        runtime = build_pinned_cbi_v1_1()

        out = runtime.core.process(
            {
                "project_id": "locallife",
                "user_id": "u1",
                "session_id": "s1",
                "request_id": "r1",
                "turn": 1,
                "state_version": 0,
                "message": "หาร้านเจ",
            },
            runtime.domain_pack,
        )

        semantic = out["semantic_result"]

        self.assertEqual(
            semantic["status"],
            "UNDERSTOOD",
        )

        self.assertEqual(
            semantic["slots"]["category"],
            "vegetarian",
        )

    def test_projected_ai_port_has_no_direct_provider(self):
        source = (
            RUNTIME_ROOT
            / "cbi"
            / "ai_hub_provider_port_v1.py"
        ).read_text(encoding="utf-8").lower()

        for forbidden in (
            "api.openai.com",
            "api.deepseek.com",
            "openai_api_key",
            "deepseek_api_key",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )

    def test_projection_is_not_wired_to_production_yet(self):
        from place_platform_v2.api import (
            locallife_v1 as api,
        )
        from place_platform_v2 import (
            web_ai_runtime_v1 as runtime,
        )

        api_source = inspect.getsource(api)
        runtime_source = inspect.getsource(
            runtime
        )

        self.assertNotIn(
            "build_pinned_cbi_v1_1",
            api_source,
        )

        self.assertNotIn(
            "build_pinned_cbi_v1_1",
            runtime_source,
        )


if __name__ == "__main__":
    unittest.main()

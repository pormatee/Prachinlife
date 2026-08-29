from __future__ import annotations
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "place_platform_v2/web_ai_runtime_v1.py"
PUBLICATION = ROOT / "place_platform_v2/controlled_production_publication.py"
CONSUMER = ROOT / "place_platform_v2/production_published_place_consumer_v1.py"

class SinglePersistedProjectionRuntimeV1Tests(unittest.TestCase):

    def test_runtime_does_not_rebuild_ephemeral_projection(self):
        src = RUNTIME.read_text(encoding="utf-8")
        self.assertNotIn("TemporaryDirectory", src)
        self.assertNotIn("build_projection_database", src)
        self.assertNotIn("BUNDLE_FILES", src)
        self.assertNotIn("ephemeral-read-model", src)

    def test_runtime_uses_authoritative_persisted_projection(self):
        src = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("data/v2/decision_published_places_v1.sqlite3", src)
        self.assertIn("ProductionPublishedPlaceRepositoryAdapterV1", src)
        self.assertIn("authoritative-persisted-read-model", src)

    def test_runtime_fails_closed_if_projection_missing(self):
        src = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("if not projection.exists()", src)
        self.assertIn("FileNotFoundError", src)

    def test_controlled_publication_updates_same_projection(self):
        publication = PUBLICATION.read_text(encoding="utf-8")
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("sync_dedicated_projection_after_commit", publication)
        self.assertIn("data/v2/decision_published_places_v1.sqlite3", consumer)

    def test_web_runtime_has_no_write_authority(self):
        tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(x.name for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        joined = "\n".join(imports)
        self.assertNotIn("sqlite_store", joined)
        self.assertNotIn("controlled_production_publication", joined)
        self.assertNotIn("persisted_published_projection_v1", joined)

if __name__ == "__main__":
    unittest.main()

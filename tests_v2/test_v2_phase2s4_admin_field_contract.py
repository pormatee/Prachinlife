from __future__ import annotations

import unittest
from uuid import uuid4

from place_platform_v2.admin_fields import (
    ADMIN_DETAIL_PRIORITY_FIELDS,
    ADMIN_FIELD_SPECS,
    AdminEvidenceInput,
    build_admin_evidence,
)
from place_platform_v2.contracts import EvidenceStatus, GeoPoint, SourceType


class TestPhase2S4AdminFieldContract(unittest.TestCase):
    def entry(self, field_name="description", value="รายละเอียดร้าน"):
        return AdminEvidenceInput(
            place_id=str(uuid4()), field_name=field_name, value=value,
            source_name="Official page", source_url="https://example.com/place",
        )

    def test_s401_contract_covers_completeness_priority_fields(self):
        expected = {"district", "subdistrict", "area", "opening_hours", "phone", "website", "real_image", "description"}
        self.assertTrue(expected.issubset(ADMIN_DETAIL_PRIORITY_FIELDS))
        self.assertTrue(expected.issubset(ADMIN_FIELD_SPECS))

    def test_s402_admin_input_becomes_candidate_manual_evidence(self):
        evidence = build_admin_evidence(self.entry())
        self.assertEqual(evidence.status, EvidenceStatus.CANDIDATE)
        self.assertEqual(evidence.source.source_type, SourceType.MANUAL)
        self.assertEqual(evidence.metadata["intake"], "admin")

    def test_s403_source_name_and_url_are_mandatory(self):
        with self.assertRaises(ValueError):
            build_admin_evidence(AdminEvidenceInput(str(uuid4()), "phone", "037123456", "", "https://example.com"))
        with self.assertRaises(ValueError):
            build_admin_evidence(AdminEvidenceInput(str(uuid4()), "phone", "037123456", "Official", ""))

    def test_s404_unapproved_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            build_admin_evidence(self.entry("published", True))

    def test_s405_urls_must_be_traceable_http_urls(self):
        with self.assertRaises(ValueError):
            build_admin_evidence(self.entry("real_image", "javascript:alert(1)"))
        with self.assertRaises(ValueError):
            build_admin_evidence(AdminEvidenceInput(str(uuid4()), "description", "x", "Official", "not-a-url"))

    def test_s406_location_is_validated_as_geopoint(self):
        evidence = build_admin_evidence(self.entry("location", {"latitude": 14.05, "longitude": 101.37}))
        self.assertEqual(evidence.value, GeoPoint(14.05, 101.37))
        with self.assertRaises(ValueError):
            build_admin_evidence(self.entry("location", {"latitude": 999, "longitude": 101.37}))

    def test_s407_categories_are_normalized_without_blanks(self):
        evidence = build_admin_evidence(self.entry("categories", ["cafe", "restaurant", "cafe"]))
        self.assertEqual(evidence.value, ("cafe", "restaurant"))

    def test_s408_contract_has_no_direct_publish_or_canonical_write(self):
        import pathlib
        text = pathlib.Path("place_platform_v2/admin_fields.py").read_text(encoding="utf-8")
        self.assertNotIn("public_production", text)
        self.assertNotIn("save_place(", text)
        self.assertNotIn("apply_adoption(", text)


if __name__ == "__main__":
    unittest.main()

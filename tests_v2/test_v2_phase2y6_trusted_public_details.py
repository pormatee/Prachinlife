import sqlite3
import unittest

from place_platform_v2.web_export import _detail_evidence_for_place


class TestPhase2Y6TrustedPublicDetails(unittest.TestCase):
    def _connection(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute(
            "CREATE TABLE place_evidence ("
            "place_id TEXT, field_name TEXT, value_json TEXT, status TEXT, "
            "observed_at TEXT, evidence_id TEXT)"
        )
        return con

    def test_y601_only_supported_or_verified_detail_is_public(self):
        con = self._connection()
        con.executemany(
            "INSERT INTO place_evidence VALUES (?,?,?,?,?,?)",
            [
                ("p", "description", '"candidate"', "candidate", "2026-08-22T12:00:00", "1"),
                ("p", "description", '"rejected"', "rejected", "2026-08-22T11:00:00", "2"),
                ("p", "description", '"stale"', "stale", "2026-08-22T10:00:00", "3"),
                ("p", "description", '"supported"', "supported", "2026-08-22T09:00:00", "4"),
            ],
        )
        self.assertEqual(_detail_evidence_for_place(con, "p")["description"], "supported")

    def test_y602_verified_detail_can_be_public(self):
        con = self._connection()
        con.execute(
            "INSERT INTO place_evidence VALUES (?,?,?,?,?,?)",
            ("p", "opening_hours", '"08:00-17:00"', "verified", "2026-08-22", "1"),
        )
        self.assertEqual(_detail_evidence_for_place(con, "p")["opening_hours"], "08:00-17:00")

    def test_y603_untrusted_only_detail_is_omitted(self):
        con = self._connection()
        con.executemany(
            "INSERT INTO place_evidence VALUES (?,?,?,?,?,?)",
            [
                ("p", "real_image", '"https://bad.example/x.jpg"', "candidate", "2026-08-22", "1"),
                ("p", "prachinlife_page_url", '"/places/p"', "rejected", "2026-08-22", "2"),
            ],
        )
        self.assertEqual(_detail_evidence_for_place(con, "p"), {})

    def test_y604_newer_untrusted_evidence_does_not_shadow_trusted_value(self):
        con = self._connection()
        con.executemany(
            "INSERT INTO place_evidence VALUES (?,?,?,?,?,?)",
            [
                ("p", "area", '"new candidate"', "candidate", "2026-08-22T12:00:00", "1"),
                ("p", "area", '"trusted area"', "verified", "2026-08-21T12:00:00", "2"),
            ],
        )
        self.assertEqual(_detail_evidence_for_place(con, "p")["area"], "trusted area")


if __name__ == "__main__":
    unittest.main()

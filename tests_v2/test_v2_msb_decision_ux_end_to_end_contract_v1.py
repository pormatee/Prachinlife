from __future__ import annotations
import unittest
from pathlib import Path

class MSBDecisionUXEndToEndContractV1(unittest.TestCase):
    def test_identity_is_not_tie_breaker(self):
        text=Path("place_platform_v2/decision_quality_engine_v1.py").read_text(encoding="utf-8")
        bad=[]
        for line in text.splitlines():
            low=line.lower()
            if ("sort(" in low or "min(" in low or "max(" in low) and ("candidate_id" in low or "place_id" in low):
                bad.append(line)
        self.assertEqual(bad,[])

    def test_sponsor_not_in_organic_ordering(self):
        text=Path("place_platform_v2/decision_quality_engine_v1.py").read_text(encoding="utf-8")
        bad=[]
        for line in text.splitlines():
            low=line.lower()
            if ("organic_score" in low or "sort(" in low) and "sponsor" in low:
                bad.append(line)
        self.assertEqual(bad,[])

    def test_persisted_projection_contract_present(self):
        refs=[]
        for p in Path("place_platform_v2").glob("*.py"):
            txt=p.read_text(encoding="utf-8",errors="ignore")
            if "decision_published_places_v1" in txt:
                refs.append(str(p))
        self.assertTrue(refs)

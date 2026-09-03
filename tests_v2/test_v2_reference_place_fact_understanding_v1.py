import unittest
from dataclasses import dataclass
from pathlib import Path

from place_platform_v2.semantic_conversation_understanding_v1 import (
    SemanticConversationStateV1,
    build_reference_fact_answer_v1,
    resolve_semantic_turn_v1,
    state_from_payload,
)

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "js/core/locallife-decision-card-v1.js").read_text(encoding="utf-8")
RUNTIME = (ROOT / "place_platform_v2/web_ai_runtime_v1.py").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


@dataclass(frozen=True)
class FakePlace:
    place_id: str
    name: str
    address_text: str | None = None
    phone: str | None = None
    website: str | None = None


class FakeRepo:
    def __init__(self, places):
        self.places = {p.place_id: p for p in places}

    def get_published(self, place_id):
        return self.places.get(place_id)


class T(unittest.TestCase):
    def state(self, **changes):
        base = dict(
            turn_index=3,
            active_request_text="หาร้านเจ",
            category="vegetarian",
            decision_object="restaurant",
            province="ปทุมธานี",
            candidate_ids=("A", "B", "C"),
        )
        base.update(changes)
        return SemanticConversationStateV1(**base)

    def test_01_first_candidate_hours(self):
        r = resolve_semantic_turn_v1("ร้านแรกเปิดกี่โมง", {"conversation_state": self.state().to_payload()})
        self.assertEqual("reference_fact", r.mode)
        self.assertEqual("A", r.state.referenced_candidate_id)
        self.assertEqual("hours", r.state.reference_fact)

    def test_02_second_candidate_phone(self):
        r = resolve_semantic_turn_v1("ร้านที่สองมีเบอร์ไหม", {"conversation_state": self.state().to_payload()})
        self.assertEqual("B", r.state.referenced_candidate_id)
        self.assertEqual("phone", r.state.reference_fact)

    def test_03_followup_keeps_reference(self):
        s = self.state(referenced_candidate_id="B")
        r = resolve_semantic_turn_v1("มีเว็บไซต์ไหม", {"conversation_state": s.to_payload()})
        self.assertEqual("B", r.state.referenced_candidate_id)
        self.assertEqual("website", r.state.reference_fact)

    def test_04_demonstrative_reference(self):
        r = resolve_semantic_turn_v1("ร้านนั้นอยู่ไหน", {"conversation_state": self.state().to_payload()})
        self.assertEqual("A", r.state.referenced_candidate_id)
        self.assertEqual("address", r.state.reference_fact)

    def test_05_missing_reference_fails_closed(self):
        s = self.state(candidate_ids=())
        r = resolve_semantic_turn_v1("ร้านแรกเปิดกี่โมง", {"conversation_state": s.to_payload()})
        self.assertEqual("reference_unresolved", r.mode)
        self.assertIsNone(r.state.referenced_candidate_id)

    def test_06_phone_from_projection(self):
        s = self.state(referenced_candidate_id="A", reference_fact="phone")
        a = build_reference_fact_answer_v1(s, FakeRepo([FakePlace("A", "ร้านเอ", phone="0812345678")]))
        self.assertEqual("known", a["status"])
        self.assertIn("0812345678", a["answer"])
        self.assertEqual("published_projection", a["source"])

    def test_07_missing_hours_not_invented(self):
        s = self.state(referenced_candidate_id="A", reference_fact="hours")
        a = build_reference_fact_answer_v1(s, FakeRepo([FakePlace("A", "ร้านเอ")]))
        self.assertEqual("unknown", a["status"])
        self.assertIn("ยังไม่มี", a["answer"])

    def test_08_address_from_projection(self):
        s = self.state(referenced_candidate_id="A", reference_fact="address")
        a = build_reference_fact_answer_v1(s, FakeRepo([FakePlace("A", "ร้านเอ", address_text="รังสิต ปทุมธานี")]))
        self.assertIn("รังสิต ปทุมธานี", a["answer"])

    def test_09_no_ranking_sponsor_authority(self):
        s = self.state(referenced_candidate_id="A", reference_fact="phone")
        a = build_reference_fact_answer_v1(s, FakeRepo([FakePlace("A", "ร้านเอ", phone="02-000-0000")]))
        for forbidden in ("ranking", "rank", "score", "sponsor", "provider"):
            self.assertNotIn(forbidden, a)

    def test_10_runtime_fact_path_precedes_decision_flow(self):
        fact_pos = RUNTIME.index('if semantic_turn.mode == "reference_fact":')
        decision_pos = RUNTIME.index("result = run_end_to_end_real_decision_flow_v1(", fact_pos)
        self.assertLess(fact_pos, decision_pos)
        block = RUNTIME[fact_pos:decision_pos]
        self.assertIn("build_reference_fact_answer_v1", block)

    def test_11_frontend_fact_answer_precedes_best_id(self):
        pos = JS.index("const referenceAnswer = String(")
        best = JS.index("const bestId = String(", pos)
        block = JS[pos:best]
        self.assertIn('addRobotMessage("assistant", referenceAnswer);', block)
        self.assertIn("return;", block)

    def test_12_state_persists_fact_without_gps(self):
        payload = self.state(reference_fact="phone").to_payload()
        restored = state_from_payload(payload)
        self.assertEqual("phone", restored.reference_fact)
        for forbidden in ("latitude", "longitude", "current_location"):
            self.assertNotIn(forbidden, payload)

    def test_13_cache_bust(self):
        self.assertIn("reference-place-fact-v1", INDEX)


if __name__ == "__main__":
    unittest.main()

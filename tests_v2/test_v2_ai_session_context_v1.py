import unittest
from dataclasses import fields

from place_platform_v2.ai_session_context_v1 import (
    AiSessionContextV1,
    AiTurnUpdateV1,
    MAX_HIGH_VALUE_QUESTIONS,
    SESSION_CONTEXT_SCHEMA_VERSION,
    apply_turn_update,
    decision_context_payload,
)


class TestAiSessionContextV1(unittest.TestCase):
    def test_01_empty_context_does_not_fabricate_facts(self):
        c = AiSessionContextV1()
        self.assertIsNone(c.goal)
        self.assertIsNone(c.category)
        self.assertIsNone(c.province)
        self.assertIsNone(c.location_text)
        self.assertEqual((), c.hard_constraints)
        self.assertEqual((), c.preferences)
        self.assertEqual((), c.candidate_ids)

    def test_02_latest_explicit_location_overrides_previous(self):
        c = AiSessionContextV1(province="ปราจีนบุรี", location_text="เมืองปราจีนบุรี")
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="เปลี่ยนเป็นกบินทร์บุรี",
            location_text="กบินทร์บุรี",
        ))
        self.assertEqual("กบินทร์บุรี", c2.location_text)
        self.assertEqual("ปราจีนบุรี", c2.province)

    def test_03_preferences_accumulate_without_duplicates(self):
        c = AiSessionContextV1(preferences=("quiet",))
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="มีเด็กด้วย",
            add_preferences=("family_friendly", "quiet"),
        ))
        self.assertEqual(("quiet", "family_friendly"), c2.preferences)

    def test_04_hard_constraint_can_be_added_and_removed(self):
        c = AiSessionContextV1(hard_constraints=("exclude_temple",))
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="วัดก็ได้",
            remove_hard_constraints=("exclude_temple",),
        ))
        self.assertEqual((), c2.hard_constraints)

    def test_05_candidate_identity_order_is_preserved(self):
        c = AiSessionContextV1()
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="เอาสามตัวนี้",
            candidate_ids=("A", "B", "C", "B"),
        ))
        self.assertEqual(("A", "B", "C"), c2.candidate_ids)

    def test_06_comparison_context_is_explicit(self):
        c = AiSessionContextV1(candidate_ids=("A", "B", "C"))
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="เทียบ A กับ B",
            comparison_candidate_ids=("A", "B"),
        ))
        self.assertEqual(("A", "B"), c2.comparison_candidate_ids)

    def test_07_last_message_is_not_naively_concatenated(self):
        c = AiSessionContextV1(last_user_message="หาร้านเจ")
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="เอาใกล้กว่านี้",
            add_preferences=("closer",),
        ))
        self.assertEqual("เอาใกล้กว่านี้", c2.last_user_message)
        self.assertNotIn("หาร้านเจ", c2.last_user_message)

    def test_08_one_high_value_question_only(self):
        self.assertEqual(1, MAX_HIGH_VALUE_QUESTIONS)
        c = apply_turn_update(
            AiSessionContextV1(),
            AiTurnUpdateV1(
                user_message="ช่วยหาให้หน่อย",
                high_value_questions=("อยู่แถวไหน", "งบเท่าไร"),
            ),
        )
        self.assertEqual("อยู่แถวไหน", c.pending_high_value_question)

    def test_09_decision_payload_has_no_provider_sponsor_or_ranking_fields(self):
        payload = decision_context_payload(AiSessionContextV1())
        forbidden = {"provider", "sponsor", "sponsor_score", "ranking", "rank", "score"}
        self.assertTrue(forbidden.isdisjoint(payload.keys()))

    def test_10_context_dataclass_has_no_provider_sponsor_or_ranking_fields(self):
        names = {f.name for f in fields(AiSessionContextV1)}
        forbidden = {"provider", "sponsor", "sponsor_score", "ranking", "rank", "score"}
        self.assertTrue(forbidden.isdisjoint(names))

    def test_11_budget_can_remain_preference_not_invented_hard_constraint(self):
        c = apply_turn_update(
            AiSessionContextV1(),
            AiTurnUpdateV1(
                user_message="งบประมาณ 500",
                add_preferences=("budget_500",),
            ),
        )
        self.assertEqual(("budget_500",), c.preferences)
        self.assertEqual((), c.hard_constraints)

    def test_12_unknown_open_weather_distance_are_not_created(self):
        payload = decision_context_payload(AiSessionContextV1())
        for key in ("open_now", "weather", "distance_km", "travel_time"):
            self.assertNotIn(key, payload)

    def test_13_new_explicit_category_replaces_old_category(self):
        c = AiSessionContextV1(category="vegetarian")
        c2 = apply_turn_update(c, AiTurnUpdateV1(
            user_message="เปลี่ยนเป็นเที่ยว",
            category="go",
        ))
        self.assertEqual("go", c2.category)

    def test_14_missing_turn_fields_preserve_existing_context(self):
        c = AiSessionContextV1(
            goal="find_place",
            category="go",
            province="ปราจีนบุรี",
            preferences=("quiet",),
            candidate_ids=("A", "B", "C"),
        )
        c2 = apply_turn_update(c, AiTurnUpdateV1(user_message="มีเด็ก"))
        self.assertEqual(c.goal, c2.goal)
        self.assertEqual(c.category, c2.category)
        self.assertEqual(c.province, c2.province)
        self.assertEqual(c.preferences, c2.preferences)
        self.assertEqual(c.candidate_ids, c2.candidate_ids)

    def test_15_turn_index_is_deterministic(self):
        c = AiSessionContextV1()
        c = apply_turn_update(c, AiTurnUpdateV1(user_message="หนึ่ง"))
        c = apply_turn_update(c, AiTurnUpdateV1(user_message="สอง"))
        self.assertEqual(2, c.turn_index)

    def test_16_schema_version_is_explicit(self):
        self.assertEqual("AI-SESSION-CONTEXT-V1", SESSION_CONTEXT_SCHEMA_VERSION)
        self.assertEqual(SESSION_CONTEXT_SCHEMA_VERSION, AiSessionContextV1().schema_version)


if __name__ == "__main__":
    unittest.main()

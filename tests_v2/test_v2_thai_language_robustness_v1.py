import unittest

from place_platform_v2.intent_context_understanding_v1 import understand_user_request
from place_platform_v2.thai_query_normalization_v1 import (
    THAI_QUERY_NORMALIZATION_VERSION,
    normalize_thai_query_v1,
)


class TestThaiLanguageRobustnessV1(unittest.TestCase):
    def test_01_short_j_stays_supported(self):
        r = understand_user_request("ร้านเจ")
        self.assertEqual("vegetarian", r.category)
        self.assertEqual("restaurant", r.decision_object)

    def test_02_typo_j_matches_short_j_semantics(self):
        clean = understand_user_request("ร้านเจ")
        typo = understand_user_request("รานเจ")
        self.assertEqual(clean.category, typo.category)
        self.assertEqual(clean.decision_object, typo.decision_object)
        self.assertEqual(clean.goal, typo.goal)

    def test_03_typo_travel_is_go_destination(self):
        r = understand_user_request("ไปเทียวไหนดี")
        self.assertEqual("go", r.category)
        self.assertEqual("destination", r.decision_object)
        self.assertEqual("find_place_to_go", r.goal)

    def test_04_typo_near_me_sets_near_me(self):
        r = understand_user_request("ไกล้ฉัน")
        self.assertTrue(r.near_me)
        self.assertTrue(r.inferred_context.get("near_me"))
        self.assertIn("current_location", r.unresolved_context)

    def test_05_typo_child_sets_family_context(self):
        r = understand_user_request("มีเดก")
        self.assertTrue(r.inferred_context.get("family_context"))
        self.assertTrue(r.inferred_context.get("with_children"))

    def test_06_typo_j_and_province_recovers_object_and_province(self):
        r = understand_user_request("รานเจ ปาจีน")
        self.assertEqual("vegetarian", r.category)
        self.assertEqual("restaurant", r.decision_object)
        self.assertEqual("ปราจีนบุรี", r.province)

    def test_07_original_user_text_is_preserved(self):
        raw = "  ไปเทียวไหนดี  "
        r = understand_user_request(raw)
        self.assertEqual(raw, r.user_text)

    def test_08_clean_and_typo_travel_have_same_core_semantics(self):
        a = understand_user_request("ไปเที่ยวไหนดี")
        b = understand_user_request("ไปเทียวไหนดี")
        self.assertEqual((a.category, a.decision_object, a.goal),
                         (b.category, b.decision_object, b.goal))

    def test_09_clean_and_typo_near_have_same_near_semantics(self):
        a = understand_user_request("ใกล้ฉัน")
        b = understand_user_request("ไกล้ฉัน")
        self.assertEqual(a.near_me, b.near_me)
        self.assertEqual(a.inferred_context.get("near_me"),
                         b.inferred_context.get("near_me"))

    def test_10_clean_and_typo_child_have_same_family_semantics(self):
        a = understand_user_request("มีเด็ก")
        b = understand_user_request("มีเดก")
        self.assertEqual(a.inferred_context.get("family_context"),
                         b.inferred_context.get("family_context"))
        self.assertEqual(a.inferred_context.get("with_children"),
                         b.inferred_context.get("with_children"))

    def test_11_no_generic_fuzzy_place_name_rewrite(self):
        self.assertEqual("ร้านเทียวไทย", normalize_thai_query_v1("ร้านเทียวไทย"))
        self.assertEqual("เดกคาเฟ่", normalize_thai_query_v1("เดกคาเฟ่"))

    def test_12_normalizer_is_deterministic(self):
        q = "รานเจ ปาจีน"
        self.assertEqual(normalize_thai_query_v1(q),
                         normalize_thai_query_v1(normalize_thai_query_v1(q)))

    def test_13_known_phrase_normalizations(self):
        self.assertEqual("ร้านเจ", normalize_thai_query_v1("รานเจ"))
        self.assertEqual("ไปเที่ยวไหนดี", normalize_thai_query_v1("ไปเทียวไหนดี"))
        self.assertEqual("ใกล้ฉัน", normalize_thai_query_v1("ไกล้ฉัน"))
        self.assertEqual("มีเด็ก", normalize_thai_query_v1("มีเดก"))

    def test_14_version_is_explicit(self):
        self.assertEqual("THAI-QUERY-NORMALIZATION-V1", THAI_QUERY_NORMALIZATION_VERSION)


if __name__ == "__main__":
    unittest.main()

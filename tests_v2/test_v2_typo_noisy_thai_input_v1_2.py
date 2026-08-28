import unittest

from place_platform_v2.intent_context_understanding_v1 import (
    normalize_noisy_input,
    understand_user_request,
)

class TypoNoisyThaiInputV12Tests(unittest.TestCase):
    def parse(self, text):
        return understand_user_request(text)

    def test_pump_typo_preserves_fuel_station_decision_object(self):
        r=self.parse("หาปั้มไหนดีที่มีอาหารเยอะๆ")
        self.assertEqual(r.decision_object, "fuel_station")
        self.assertEqual(r.goal, "find_fuel_station")
        self.assertTrue(any(p.key=="food_variety" for p in r.preferences))

    def test_food_typo_is_preference_not_goal(self):
        r=self.parse("หาปั๊มไหนดีที่มีอาหานเยอะๆ")
        self.assertEqual(r.decision_object, "fuel_station")
        self.assertTrue(any(p.key=="food_variety" for p in r.preferences))

    def test_pathum_typo_normalizes_province(self):
        r=self.parse("หาร้านเจปทุมทานี")
        self.assertEqual(r.category, "vegetarian")
        self.assertEqual(r.province, "ปทุมธานี")

    def test_tomorrow_typo_resolves_temporal_context_label(self):
        r=self.parse("พุ่งนี้ไปปทุมธานี กินเจที่ไหนดี")
        self.assertEqual(r.category, "vegetarian")
        self.assertEqual(r.temporal_context, "tomorrow")
        self.assertIn("tomorrow", r.temporal_signals)

    def test_pump_reference_typo_not_promoted_to_object(self):
        r=self.parse("หาร้านอาหานแถวปั้ม ปตท. หน่อย")
        self.assertEqual(r.decision_object, "restaurant")
        self.assertEqual(r.category, "eat")
        self.assertTrue(r.references)

    def test_whitespace_noise(self):
        a=self.parse("หาร้านเจ ปทุมธานี")
        b=self.parse("   หาร้านเจ    ปทุมธานี   ")
        self.assertEqual(a.decision_object, b.decision_object)
        self.assertEqual(a.category, b.category)
        self.assertEqual(a.province, b.province)

    def test_known_negation_not_reversed_by_normalizer(self):
        text="ไม่กินเจ"
        self.assertEqual(normalize_noisy_input(text), text)

    def test_unknown_word_not_auto_corrected(self):
        text="หาร้าน xyzq ปทุมธานี"
        self.assertIn("xyzq", normalize_noisy_input(text))

    def test_no_fuzzy_guessing_of_arbitrary_words(self):
        text="หากล้องไหนดี"
        self.assertEqual(normalize_noisy_input(text), text)

    def test_normalization_is_idempotent(self):
        once=normalize_noisy_input("พุ่งนี้ หาปั้ม")
        twice=normalize_noisy_input(once)
        self.assertEqual(once, twice)

if __name__=="__main__":
    unittest.main()

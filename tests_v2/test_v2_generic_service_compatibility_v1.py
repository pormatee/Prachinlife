import unittest
from types import SimpleNamespace

from place_platform_v2.end_to_end_real_decision_flow_v1 import _candidate_compatible


class GenericServiceCompatibilityV1Tests(unittest.TestCase):

    def compatible(self, categories, decision_object, category="service"):
        place = SimpleNamespace(categories=tuple(categories))
        understanding = SimpleNamespace(
            decision_object=decision_object,
            category=category,
        )
        return _candidate_compatible(place, understanding)

    def test_generic_service_accepts_fuel_station(self):
        self.assertTrue(
            self.compatible(("ปั๊มน้ำมัน",), "service_place")
        )

    def test_generic_service_accepts_laundry(self):
        self.assertTrue(
            self.compatible(("ซักรีด",), "service_place")
        )

    def test_generic_service_accepts_clinic(self):
        self.assertTrue(
            self.compatible(("คลินิก",), "service_place")
        )

    def test_specific_fuel_object_does_not_accept_clinic(self):
        self.assertFalse(
            self.compatible(("คลินิก",), "fuel_station")
        )


if __name__ == "__main__":
    unittest.main()

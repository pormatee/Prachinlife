import unittest

from place_platform_v2.staged_milestone import (
    observation_status_for_item,
)


class TestOSMWayVerification(unittest.TestCase):

    def test_way_does_not_use_node_distance_rule(self):
        obs = {
            "visible": True,
            "tags": {"amenity": "fuel"},
            "lat": 99.0,
            "lon": 99.0,
        }
        item = {
            "osm_type": "way",
            "latitude": 13.9,
            "longitude": 101.5,
        }

        status, _ = observation_status_for_item(obs, item)
        self.assertEqual(status, "current_listing")

    def test_way_negative_marker_blocks(self):
        obs = {
            "visible": True,
            "tags": {"disused": "yes"},
            "lat": None,
            "lon": None,
        }
        item = {
            "osm_type": "way",
            "latitude": 13.9,
            "longitude": 101.5,
        }

        status, _ = observation_status_for_item(obs, item)
        self.assertEqual(status, "negative")


if __name__ == "__main__":
    unittest.main()

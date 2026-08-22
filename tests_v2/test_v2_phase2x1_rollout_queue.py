import unittest
from pathlib import Path

from place_platform_v2.staged_milestone import (
    eligible_place_ids,
    select_observation_queue,
)


DB = Path("data/v2/place_platform_v2.sqlite3")
PROVINCE = "ปราจีนบุรี"


class TestPhase2X1RolloutQueue(unittest.TestCase):

    def test_queue_is_deterministic(self):
        first = select_observation_queue(
            DB,
            province=PROVINCE,
            limit=25,
        )

        second = select_observation_queue(
            DB,
            province=PROVINCE,
            limit=25,
        )

        self.assertEqual(first, second)

    def test_queue_never_contains_already_eligible_places(self):
        queue = select_observation_queue(
            DB,
            province=PROVINCE,
            limit=1000,
        )

        eligible, _ = eligible_place_ids(
            DB,
            province=PROVINCE,
        )

        queue_ids = {
            item["place_id"]
            for item in queue
        }

        self.assertTrue(
            queue_ids.isdisjoint(set(eligible))
        )

    def test_initial_rollout_queue_uses_osm_nodes_only(self):
        queue = select_observation_queue(
            DB,
            province=PROVINCE,
            limit=1000,
        )

        for item in queue:
            self.assertEqual(
                item["osm_type"],
                "node",
            )

    def test_queue_has_unique_place_ids(self):
        queue = select_observation_queue(
            DB,
            province=PROVINCE,
            limit=1000,
        )

        ids = [
            item["place_id"]
            for item in queue
        ]

        self.assertEqual(
            len(ids),
            len(set(ids)),
        )

    def test_zero_limit_is_empty(self):
        self.assertEqual(
            select_observation_queue(
                DB,
                province=PROVINCE,
                limit=0,
            ),
            [],
        )

    def test_negative_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            select_observation_queue(
                DB,
                province=PROVINCE,
                limit=-1,
            )


if __name__ == "__main__":
    unittest.main()

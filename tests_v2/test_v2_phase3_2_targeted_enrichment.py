import json
import tempfile
import unittest
from pathlib import Path

from place_platform_v2.targeted_enrichment import build_targeted_enrichment_plan

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/v2/place_platform_v2.sqlite3'
QUALITY=ROOT/'data/v2/discovery_reports/production_place_quality_v2.json'


class TestPhase32TargetedEnrichment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=build_targeted_enrichment_plan(database_path=DB,repo_root=ROOT,quality_report_path=QUALITY,limit=50)

    def test_all_visible_production_places_map_to_v2(self):
        self.assertEqual(self.report['visible_place_count'],336)
        self.assertEqual(self.report['mapped_visible_place_count'],336)

    def test_top_50_queue_is_complete_and_deterministic(self):
        self.assertEqual(self.report['quality_priority_count'],50)
        self.assertEqual(self.report['queue_count'],50)
        self.assertEqual(self.report['unmapped_priority_count'],0)
        again=build_targeted_enrichment_plan(database_path=DB,repo_root=ROOT,quality_report_path=QUALITY,limit=50)
        self.assertEqual(self.report['queue'],again['queue'])
        self.assertEqual(self.report['next_step_counts'],again['next_step_counts'])

    def test_missing_enrichment_is_not_invented(self):
        for row in self.report['queue']:
            for action,info in row['actions'].items():
                if not info['ready'] and info['active_evidence_count']==0:
                    self.assertEqual(info['next_step'],f'acquire_new_{action}_evidence')

    def test_no_automatic_adoption_or_production_write(self):
        safety=self.report['safety']
        self.assertFalse(safety['canonical_writes'])
        self.assertFalse(safety['evidence_writes'])
        self.assertFalse(safety['production_json_writes'])
        self.assertFalse(safety['trust_policy_lowered'])
        self.assertTrue(safety['database_unchanged'])
        self.assertEqual(safety['database_sha256_before'],safety['database_sha256_after'])

    def test_queue_has_traceable_v2_place_ids(self):
        self.assertTrue(all(r['place_id'] and r['dataset'] and r['record_id'] for r in self.report['queue']))

    def test_report_is_json_serializable(self):
        text=json.dumps(self.report,ensure_ascii=False,sort_keys=True)
        self.assertIn('READ_ONLY_TARGETED_ENRICHMENT_ACQUISITION_PLAN',text)


if __name__=='__main__': unittest.main()

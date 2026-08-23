from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class Phase9PreviewAcceptanceContractTest(unittest.TestCase):
    def test_acceptance_runner_is_fail_closed(self):
        s=(ROOT/'scripts/run_phase9_preview_acceptance.py').read_text(encoding='utf-8')
        self.assertIn("passed=all(x['ok'] for x in checks)",s)
        self.assertIn("raise SystemExit(0 if passed else 2)",s)
    def test_preview_runner_does_not_write_production(self):
        s=(ROOT/'scripts/run_phase9_preview_acceptance.py').read_text(encoding='utf-8')
        self.assertIn("'production_switch':'DISABLED'",s)
        self.assertIn("'production_data_writes':False",s)
    def test_acceptance_checks_user_visible_contracts(self):
        s=(ROOT/'scripts/run_phase9_preview_acceptance.py').read_text(encoding='utf-8')
        for marker in ('recommended_content_type_aware','recommended_uses_place_image','near_me_contracts','search_contract','service_fuel_semantics'):
            self.assertIn(marker,s)
if __name__=='__main__': unittest.main()

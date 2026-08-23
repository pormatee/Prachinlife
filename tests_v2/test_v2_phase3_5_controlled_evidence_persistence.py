import json, sqlite3, tempfile, unittest, uuid
from datetime import datetime, timezone
from pathlib import Path
from place_platform_v2.sqlite_store import SQLitePlaceRepository
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.controlled_evidence_persistence import verify_and_persist_web_evidence

NOW=datetime(2026,8,23,tzinfo=timezone.utc)

def claim(pid, field, value, source, record):
    return {"evidence_id":str(uuid.uuid4()),"place_id":pid,"field_name":field,"value":value,
            "source_name":source,"source_record_id":record,"source_url":"https://example.com/"+record,
            "status":"candidate","target_rank":1}

class TestPhase35(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); root=Path(self.t.name)
        self.db=root/'db.sqlite3'; self.report=root/'in.json'
        repo=SQLitePlaceRepository(self.db)
        self.pid=str(uuid.uuid4())
        repo.save_place(CanonicalPlace(identity=PlaceIdentity(self.pid),canonical_name='Test',location=GeoPoint(13,100),province='กรุงเทพมหานคร',categories=('eat',),lifecycle=PlaceLifecycle.ACTIVE,created_at=NOW,updated_at=NOW))
        repo.close()
    def tearDown(self): self.t.cleanup()
    def write(self, claims): self.report.write_text(json.dumps({"claims":claims}),encoding='utf-8')
    def test_single_source_is_supported_and_dry_run_does_not_write(self):
        self.write([claim(self.pid,'phone','021234567','A','1')])
        r=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,observed_at=NOW)
        self.assertEqual(r['persistable_status_counts'],{'supported':1}); self.assertEqual(r['inserted_evidence_count'],0)
        con=sqlite3.connect(self.db); self.assertEqual(con.execute('select count(*) from place_evidence').fetchone()[0],0); con.close()
    def test_two_independent_sources_verify_same_value(self):
        self.write([claim(self.pid,'phone','021234567','A','1'),claim(self.pid,'phone','021234567','B','2')])
        r=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,observed_at=NOW)
        self.assertEqual(r['persistable_status_counts'],{'verified':2})
    def test_conflicting_values_are_not_persistable(self):
        self.write([claim(self.pid,'phone','021234567','A','1'),claim(self.pid,'phone','029999999','B','2')])
        r=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,observed_at=NOW)
        self.assertEqual(r['persistable_evidence_count'],0); self.assertEqual(r['blocked_counts'],{'verification_conflicting':2})
    def test_commit_writes_evidence_only(self):
        self.write([claim(self.pid,'website','https://official.example','A','1')])
        con=sqlite3.connect(self.db); before=con.execute('select * from places').fetchall(); con.close()
        r=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,commit=True,observed_at=NOW)
        self.assertEqual(r['inserted_evidence_count'],1); self.assertTrue(r['safety']['canonical_unchanged']); self.assertTrue(r['safety']['non_evidence_tables_unchanged'])
        con=sqlite3.connect(self.db); self.assertEqual(con.execute('select * from places').fetchall(),before); self.assertEqual(con.execute('select status from place_evidence').fetchone()[0],'supported'); con.close()
    def test_commit_is_idempotent(self):
        self.write([claim(self.pid,'phone','021234567','A','1')])
        a=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,commit=True,observed_at=NOW)
        b=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,commit=True,observed_at=NOW)
        self.assertEqual(a['inserted_evidence_count'],1); self.assertEqual(b['inserted_evidence_count'],0); self.assertEqual(b['already_present_count'],1)
    def test_unknown_place_blocked(self):
        self.write([claim(str(uuid.uuid4()),'phone','021234567','A','1')])
        r=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,observed_at=NOW)
        self.assertEqual(r['blocked_counts'],{'unknown_place':1}); self.assertEqual(r['persistable_evidence_count'],0)
    def test_unapproved_field_blocked(self):
        self.write([claim(self.pid,'description','x','A','1')])
        r=verify_and_persist_web_evidence(database_path=self.db,acquisition_report_path=self.report,observed_at=NOW)
        self.assertEqual(r['blocked_counts'],{'field_not_allowed':1})

if __name__=='__main__': unittest.main()

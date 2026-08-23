import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.pending_coordinate_queue import queue_pending_coordinates

class T(unittest.TestCase):
    def fixture(self):
        td = tempfile.TemporaryDirectory(); root = Path(td.name); db = root/'x.sqlite3'
        c = sqlite3.connect(db)
        c.execute("create table places(place_id text primary key)")
        c.execute("create table precanonical_candidates(candidate_id text primary key,candidate_key text,proposed_name text,province text,status text)")
        c.execute("create table precanonical_evidence(evidence_id text primary key)")
        c.execute("""create table precanonical_pending_review(queue_id text primary key,candidate_id text,reason text,current_state text,next_action text,status text,source_policy_version text,payload_json text,created_at text,updated_at text)""")
        c.execute("insert into precanonical_candidates values('c1','k1','ร้านอาหารเจ AMITA VEGAN','ปราจีนบุรี','verified_identity_address_location')")
        c.execute("insert into precanonical_pending_review values('old','c1','unresolved_lifecycle_conflict','STILL_UNRESOLVED','confirm','pending_manual_confirmation','p','{}','t','t')")
        c.commit(); c.close()
        rp = root/'r.json'
        rp.write_text(json.dumps({"candidate_name":"ร้านอาหารเจ AMITA VEGAN","province":"ปราจีนบุรี","confirmation_outcome":"STILL_UNRESOLVED","next_step":"supply_valid_direct_coordinate_confirmation","policy_version":"4.13"}), encoding='utf-8')
        return td, db, rp
    def test_commit_adds_coordinate_pending_type(self):
        td,db,rp=self.fixture(); self.addCleanup(td.cleanup)
        r=queue_pending_coordinates(database_path=db,direct_coordinate_report_path=rp,commit=True)
        self.assertEqual(r['inserted_queue_count'],1)
        self.assertEqual(r['queue_type_counts']['pending_coordinate_confirmation'],1)
        self.assertEqual(r['queue_type_counts']['pending_manual_confirmation'],1)
    def test_replay_idempotent(self):
        td,db,rp=self.fixture(); self.addCleanup(td.cleanup)
        queue_pending_coordinates(database_path=db,direct_coordinate_report_path=rp,commit=True)
        r=queue_pending_coordinates(database_path=db,direct_coordinate_report_path=rp,commit=True)
        self.assertEqual(r['inserted_queue_count'],0); self.assertEqual(r['already_present_queue_count'],1)
    def test_resolved_coordinate_is_not_queued(self):
        td,db,rp=self.fixture(); self.addCleanup(td.cleanup)
        x=json.loads(rp.read_text()); x['confirmation_outcome']='DIRECT_COORDINATES_CONFIRMED'; rp.write_text(json.dumps(x))
        r=queue_pending_coordinates(database_path=db,direct_coordinate_report_path=rp,commit=True)
        self.assertEqual(r['pending_candidate_count'],0)
    def test_non_queue_tables_unchanged(self):
        td,db,rp=self.fixture(); self.addCleanup(td.cleanup)
        r=queue_pending_coordinates(database_path=db,direct_coordinate_report_path=rp,commit=True)
        self.assertTrue(r['safety']['non_queue_tables_unchanged'])
    def test_pending_never_blocks_discovery(self):
        td,db,rp=self.fixture(); self.addCleanup(td.cleanup)
        r=queue_pending_coordinates(database_path=db,direct_coordinate_report_path=rp,commit=True)
        self.assertTrue(r['discovery_continues']); self.assertFalse(r['safety']['pending_candidate_blocks_discovery'])

if __name__=='__main__': unittest.main()
